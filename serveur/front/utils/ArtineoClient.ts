// front/utils/ArtineoClient.ts
import { EventEmitter } from 'eventemitter3'

export type BufferPayload = {
  [key: string]: any
}

export enum ArtineoAction {
  SET = 'set',
  GET = 'get',
}

export interface ArtineoConfigResponse {
  config: Record<string, any>
  configurations?: Record<string, any>
}

export interface ArtineoClientOptions {
  httpRetries?: number
  httpBackoff?: number
  httpTimeout?: number
  wsRetries?: number
  wsBackoff?: number
  wsPingInterval?: number
}

export class ArtineoClient extends EventEmitter {
  private ws?: WebSocket
  private stopping = false
  private reconnectAttempts = 0
  private backoff = 0
  private pingTimer?: number

  constructor(
    public moduleId: number,
    private apiUrl: string,
    private wsUrl: string,
    private opts: ArtineoClientOptions = {}
  ) {
    super()
    this.opts = {
      httpRetries: 3,
      httpBackoff: 500,
      httpTimeout: 5000,
      wsRetries: 5,
      wsBackoff: 1000,
      wsPingInterval: 20000,
      ...opts
    }
  }

  // —— HTTP with retry, timeout, backoff ——
  private async _fetch<T>(
    path: string,
    options: { method?: string; body?: any; params?: Record<string, any> } = {}
  ): Promise<T> {
    const { httpRetries, httpBackoff, httpTimeout } = this.opts
    const url = new URL(this.apiUrl + path)
    url.searchParams.set('module', this.moduleId.toString())
    Object.entries(options.params || {}).forEach(([k, v]) => url.searchParams.set(k, v.toString()))

    let attempt = 0, delay = httpBackoff!
    while (true) {
      attempt++
      const ctrl = new AbortController()
      const timer = setTimeout(() => ctrl.abort(), httpTimeout)
      try {
        const res = await fetch(url.toString(), {
          method: options.method || 'GET',
          headers: { 'Content-Type': 'application/json' },
          signal: ctrl.signal,
          body: options.body != null ? JSON.stringify(options.body) : undefined
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
    const json = await this._fetch<ArtineoConfigResponse>('/config')
    return json.config ?? json.configurations
  }

  async setConfig(patch: Record<string, any>): Promise<any> {
    const json = await this._fetch<ArtineoConfigResponse>('/config', {
      method: 'POST',
      body: patch
    })
    return json.config ?? json.configurations
  }

  // —— WebSocket with auto-reconnect and ping ——
  private connectWebSocket() {
    if (this.stopping) return
    const { wsBackoff, wsRetries, wsPingInterval } = this.opts
    this.ws = new WebSocket(this.wsUrl + '/ws')

    this.ws.onopen = () => {
      this.reconnectAttempts = 0
      this.backoff = wsBackoff!
      console.log(`[ArtineoClient] WS connected to ${this.wsUrl}/ws`)  // ← log connection
      this.emit('open')
      this.pingTimer = window.setInterval(() => {
        try { this.ws!.send('ping') } catch {}
      }, wsPingInterval)
    }

    this.ws.onmessage = e => {
      console.log('[ArtineoClient] WS message received:', e.data)   // ← log raw message
      this.handleRawMessage(e.data)
    }

    this.ws.onerror = err => {
      this.emit('error', err)
      this.ws!.close()
    }

    this.ws.onclose = () => {
      clearInterval(this.pingTimer)
      if (this.stopping) return
      if (this.reconnectAttempts >= wsRetries!) {
        this.emit('error', new Error('Max WS reconnect attempts reached'))
        return
      }
      this.reconnectAttempts++
      const jitter = (Math.random() * 0.2 + 0.9)
      const to = this.backoff * jitter
      setTimeout(() => this.connectWebSocket(), to)
      this.backoff *= 2
    }
  }

  private ensureWs(): Promise<WebSocket> {
    return new Promise((resolve, reject) => {
      if (this.ws && this.ws.readyState === WebSocket.OPEN) {
        return resolve(this.ws)
      }
      this.stopping = false
      this.connectWebSocket()
      const onOpen = () => {
        this.off('error', onErr)
        resolve(this.ws!)
      }
      const onErr = (e: any) => {
        this.off('open', onOpen)
        reject(e)
      }
      this.once('open', onOpen)
      this.once('error', onErr)
    })
  }

  private async sendRaw(msg: object): Promise<any> {
    const ws = await this.ensureWs()
    ws.send(JSON.stringify({ module: this.moduleId, ...msg }))
    return new Promise(resolve => {
      const handler = (dataEvent: MessageEvent) => {
        ws.removeEventListener('message', handler)
        try { resolve(JSON.parse(dataEvent.data)) }
        catch { resolve(dataEvent.data) }
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

  onMessage(fn: (msg: any) => void) {
    this.on('message', fn)
    this.ensureWs().catch(err => this.emit('error', err))
  }

  private handleRawMessage(raw: string) {
    if (raw === 'ping') {
      this.ws!.send('pong')
      return
    }
    let msg: any = raw
    try { msg = JSON.parse(raw) } catch {}
    this.emit('message', msg)
  }

  close() {
    this.stopping = true
    clearInterval(this.pingTimer)
    this.ws?.close()
    this.removeAllListeners()
  }
}
