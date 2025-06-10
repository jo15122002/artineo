// serveur/front/utils/ArtineoClient.ts
// -----------------------------------------------------------------------------
// Client Artineo côté front : HTTP (REST) + WebSocket résilient.
// Correction 2025-06 : ensureWs() ne crée plus plusieurs connexions concurrentes.
// -----------------------------------------------------------------------------

import { EventEmitter } from 'eventemitter3'

export type BufferPayload = { [key: string]: any }

export enum ArtineoAction {
  SET = 'set',
  GET = 'get',
}

export interface ArtineoConfigResponse {
  config?:          Record<string, any>
  configurations?:  Record<string, any>
}

export interface ArtineoClientOptions {
  httpRetries?:    number
  httpBackoff?:    number          // ms
  httpTimeout?:    number          // ms
  wsRetries?:      number
  wsBackoff?:      number          // ms
  wsPingInterval?: number          // ms
}

export class ArtineoClient extends EventEmitter {
  // WebSocket courant
  private ws?: WebSocket
  private stopping = false

  // ---- Recon­nexion / ping ---------------------------------------------------
  private reconnectAttempts = 0
  private backoff = 0
  private pingTimer?: number

  // ---- Nouvelle : promesse de connexion en cours ----------------------------
  private pendingConnectPromise?: Promise<WebSocket>

  constructor(
    public   moduleId: number,
    private  apiUrl:   string,
    private  wsUrl:    string,
    private  opts:     ArtineoClientOptions = {}
  ) {
    super()
    this.opts = {
      httpRetries:    3,
      httpBackoff:    500,
      httpTimeout:    5000,
      wsRetries:      5,
      wsBackoff:      1000,
      wsPingInterval: 20000,
      ...opts,
    }
  }

  // ────────────────────────────────────────────────────────────────────────────
  // HTTP (retry + back-off)
  // ────────────────────────────────────────────────────────────────────────────
  private async _fetch<T>(
    path: string,
    options: { method?: string; body?: any; params?: Record<string, any> } = {}
  ): Promise<T> {
    const { httpRetries, httpBackoff, httpTimeout } = this.opts
    const url = new URL(this.apiUrl + path)
    url.searchParams.set('module', this.moduleId.toString())
    Object.entries(options.params || {}).forEach(([k, v]) =>
      url.searchParams.set(k, v.toString())
    )

    let attempt = 0
    let delay   = httpBackoff!
    while (true) {
      attempt++
      const ctrl  = new AbortController()
      const timer = setTimeout(() => ctrl.abort(), httpTimeout)
      try {
        const res = await fetch(url.toString(), {
          method:  options.method || 'GET',
          headers: { 'Content-Type': 'application/json' },
          signal:  ctrl.signal,
          body:    options.body != null ? JSON.stringify(options.body) : undefined,
        })
        clearTimeout(timer)
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        return res.json()
      } catch (err) {
        clearTimeout(timer)
        if (attempt >= httpRetries!) throw err
        await new Promise(r => setTimeout(r, delay))
        delay *= 2
      }
    }
  }

  async fetchConfig(): Promise<any> {
    const js = await this._fetch<ArtineoConfigResponse>('/config')
    return js.config ?? js.configurations
  }

  async setConfig(patch: Record<string, any>): Promise<any> {
    const js = await this._fetch<ArtineoConfigResponse>('/config', {
      method: 'POST',
      body:   patch,
    })
    return js.config ?? js.configurations
  }

  // ────────────────────────────────────────────────────────────────────────────
  // WebSocket
  // ────────────────────────────────────────────────────────────────────────────
  private connectWebSocket(): void {
    // Si déjà ouverte ou en train d’ouvrir ⇒ ne rien faire
    if (
      this.ws &&
      (this.ws.readyState === WebSocket.OPEN ||
       this.ws.readyState === WebSocket.CONNECTING)
    ) {
      return
    }

    const { wsBackoff, wsRetries, wsPingInterval } = this.opts
    this.ws = new WebSocket(this.wsUrl + '/ws')

    this.ws.onopen = () => {
      this.reconnectAttempts = 0
      this.backoff = wsBackoff!
      this.emit('open')
      console.log(`[ArtineoClient] WebSocket opened for module ${this.moduleId}`)
      // Ping périodique
      this.pingTimer = window.setInterval(() => {
        try { this.ws!.send('ping') } catch {}
      }, wsPingInterval)
    }

    this.ws.onmessage = e => {
      if (e.data === 'ping') { this.ws!.send('pong'); return }
      let msg: any = e.data
      try { msg = JSON.parse(e.data) } catch {}
      this.emit('message', msg)
    }

    this.ws.onerror = err => {
      this.emit('error', err)
      this.ws!.close()
    }

    this.ws.onclose = () => {
      clearInterval(this.pingTimer)
      this.pendingConnectPromise = undefined          //  🔄 reset
      if (this.stopping) return
      if (this.reconnectAttempts >= wsRetries!) {
        this.emit('error', new Error('Max WS reconnect attempts reached'))
        return
      }
      this.reconnectAttempts++
      const jitter = 0.9 + 0.2 * Math.random()
      const wait   = this.backoff * jitter
      setTimeout(() => this.connectWebSocket(), wait)
      this.backoff *= 2
    }
  }

  // Garantit une WS ouverte ; NE relance plus plusieurs handshakes concurrents
  private ensureWs(): Promise<WebSocket> {
    // 1) Socket déjà ouverte
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      return Promise.resolve(this.ws)
    }

    // 2) Socket en cours d’ouverture ⇒ renvoyer la même promesse
    if (
      this.ws &&
      this.ws.readyState === WebSocket.CONNECTING &&
      this.pendingConnectPromise
    ) {
      return this.pendingConnectPromise
    }

    // 3) Aucune connexion en cours ⇒ on en crée UNE seule
    this.stopping = false
    this.connectWebSocket()

    this.pendingConnectPromise = new Promise<WebSocket>((resolve, reject) => {
      const clean = () => {
        this.off('open', onOpen)
        this.off('error', onErr)
        // pendingConnectPromise sera réinitialisée dans onclose
      }
      const onOpen = () => { clean(); resolve(this.ws!) }
      const onErr  = (e: any) => { clean(); reject(e) }

      this.once('open',  onOpen)
      this.once('error', onErr)
    })

    return this.pendingConnectPromise
  }

  // ------------------------------- helpers WS --------------------------------
  private async sendRaw(msg: object): Promise<any> {
    const ws = await this.ensureWs()
    ws.send(JSON.stringify({ module: this.moduleId, ...msg }))
    return new Promise(resolve => {
      const handler = (e: MessageEvent) => {
        ws.removeEventListener('message', handler)
        try { resolve(JSON.parse(e.data)) }
        catch { resolve(e.data) }
      }
      ws.addEventListener('message', handler)
    })
  }

  async getBuffer(): Promise<BufferPayload> {
    const res = await this.sendRaw({ action: ArtineoAction.GET })
    return res.buffer
  }

  async setBuffer(buf: any): Promise<any> {
    return this.sendRaw({ action: ArtineoAction.SET, data: buf })
  }

  onMessage(fn: (msg: any) => void): void {
    this.on('message', fn)
    // Assure la connexion
    this.ensureWs().catch(err => this.emit('error', err))
  }

  // -------------------------------------------------------------------------
  // Fermeture explicite
  // -------------------------------------------------------------------------
  close(): void {
    this.stopping = true
    clearInterval(this.pingTimer)
    this.pendingConnectPromise = undefined
    this.ws?.close()
    this.removeAllListeners()
    this.ws = undefined
  }
}
