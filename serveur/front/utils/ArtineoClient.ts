// front/utils/ArtineoClient.ts
export type BufferPayload = {
  current_set: number
  uid1: string | null
  uid2: string | null
  uid3: string | null
  button_pressed?: boolean
  [key: string]: any
}

export enum ArtineoAction {
  SET    = "set",
  GET    = "get",
}

export interface ArtineoConfigResponse {
  config: Record<string, any>
  configurations?: Record<string, any>
}

export class ArtineoClient {
  private ws?: WebSocket
  private handler?: (msg: any) => void

  constructor(
    public moduleId: number,
    private apiUrl: string,
    private wsUrl: string,
  ) {}

  /** Récupère la config via GET /config?module=… */
  async fetchConfig(): Promise<any> {
    const url = new URL(`${this.apiUrl}/config`)
    url.searchParams.set("module", this.moduleId.toString())
    const res = await fetch(url.toString())
    if (!res.ok) throw new Error(`Config fetch failed: ${res.status}`)
    const json = await res.json() as ArtineoConfigResponse
    return json.config ?? json.configurations
  }

  /** Poste une mise à jour partielle de config sur POST /config */
  async setConfig(patch: Record<string, any>): Promise<any> {
    const url = new URL(`${this.apiUrl}/config`)
    url.searchParams.set("module", this.moduleId.toString())
    const res = await fetch(url.toString(), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(patch),
    })
    if (!res.ok) throw new Error(`Config update failed: ${res.status}`)
    return (await res.json()).config
  }

  /** (Re)ouvre la connexion WS si besoin */
  private ensureWs(): Promise<WebSocket> {
  return new Promise((resolve, reject) => {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      return resolve(this.ws)
    }
    this.ws = new WebSocket(`${this.wsUrl}/ws`)
    this.ws.onopen = () => {
      console.log(`[ArtineoClient] WebSocket connected to ${this.wsUrl}`)  // ← nouveau log
      resolve(this.ws!)
    }
    this.ws.onerror = e => reject(e)
    this.ws.onmessage = e => this.handleRawMessage(e.data)
  })
}

  /** Envoie un message JSON et attend une réponse */
  private async sendRaw(msg: object): Promise<any> {
    const ws = await this.ensureWs()
    ws.send(JSON.stringify(msg))
    return new Promise(resolve => {
      const listener = (e: MessageEvent) => {
        ws.removeEventListener("message", listener)
        try { resolve(JSON.parse(e.data)) }
        catch { resolve(e.data) }
      }
      ws.addEventListener("message", listener)
    })
  }

  /** Récupère le buffer via WS */
  async getBuffer(): Promise<BufferPayload> {
    return this.sendRaw({ module: this.moduleId, action: ArtineoAction.GET })
  }

  /** Envoie un buffer via WS */
  async setBuffer(buf: any): Promise<any> {
    return this.sendRaw({ module: this.moduleId, action: ArtineoAction.SET, data: buf })
  }

  /** Enregistre un callback pour tous les messages non-ping */
  onMessage(fn: (msg: any) => void) {
    this.handler = fn
    // démarre l’écoute si ws déjà ouvert
    this.ensureWs().catch(() => {})
  }

  /** Interne : distribue le message brut */
  private handleRawMessage(raw: string) {
    if (raw === "ping") {
      this.ws!.send("pong")
      return
    }
    try {
      const msg = JSON.parse(raw)
      if (msg.action === "get_buffer" || msg.action === "set_buffer" || msg.action === "ack") {
        this.handler?.(msg)
        return
      }
    } catch {
      // non-JSON, ignore ou forward
    }
    this.handler?.(raw)
  }

  /** Ferme proprement la connexion WebSocket */
  close() {
    if (this.ws) {
      this.ws.close()
      this.ws = undefined
    }
  }
}
