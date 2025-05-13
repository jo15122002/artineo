// lib/artineoClient.js

import fetch from 'cross-fetch'
import { EventEmitter } from 'eventemitter3'
import WebSocket from 'isomorphic-ws'

export const ArtineoAction = {
    SET: 'set',
    GET: 'get',
}

export class ArtineoClient extends EventEmitter {
    /**
     * @param {object} options
     * @param {string|null} options.moduleId
     * @param {string} options.apiUrl     // ex. "http://mon-serveur:8000"
     * @param {string} options.wsUrl      // ex. "ws://mon-serveur:8000/ws"
     * @param {number} [options.httpRetries]
     * @param {number} [options.httpBackoff]    en ms
     * @param {number} [options.httpTimeout]    en ms
     * @param {number} [options.wsRetries]
     * @param {number} [options.wsBackoff]      en ms
     * @param {number} [options.wsPingInterval] en ms
     */
    constructor({
        moduleId = null,
        apiUrl,
        wsUrl,
        httpRetries = 3,
        httpBackoff = 500,
        httpTimeout = 5000,
        wsRetries = 5,
        wsBackoff = 1000,
        wsPingInterval = 20000,
    }) {
        super()
        this.moduleId = moduleId
        this.baseUrl = apiUrl
        this.wsUrl = wsUrl
        this.httpRetries = httpRetries
        this.httpBackoff = httpBackoff
        this.httpTimeout = httpTimeout
        this.wsRetries = wsRetries
        this.wsBackoff = wsBackoff
        this.wsPingInterval = wsPingInterval

        this.ws = null
        this._stop = false
    }

    // —— HTTP avec retry & timeout ——
    async _fetch(path, { method = 'GET', body = null, params = {} } = {}) {
        const url = new URL(this.baseUrl + path)
        if (this.moduleId != null) params.module = this.moduleId
        Object.entries(params).forEach(([k, v]) => url.searchParams.set(k, v))

        let attempt = 0, delay = this.httpBackoff
        while (attempt < this.httpRetries) {
            attempt++
            const ctrl = new AbortController()
            const timer = setTimeout(() => ctrl.abort(), this.httpTimeout)
            try {
                const res = await fetch(url.toString(), {
                    method,
                    signal: ctrl.signal,
                    headers: { 'Content-Type': 'application/json' },
                    body: body != null ? JSON.stringify(body) : null,
                })
                clearTimeout(timer)
                if (!res.ok) throw new Error(`HTTP ${res.status}`)
                return res.json()
            } catch (err) {
                clearTimeout(timer)
                if (attempt === this.httpRetries) throw err
                await new Promise(r => setTimeout(r, delay))
                delay *= 2
            }
        }
    }

    fetchConfig() {
        return this._fetch('/config', { method: 'GET' })
            .then(data => data.config || data.configurations)
    }

    setConfig(newConfig) {
        return this._fetch('/config', { method: 'POST', body: newConfig })
    }

    // —— WebSocket avec reconnexion & ping ——
    startWebSocket() {
        this._stop = false
        let attempt = 0, backoff = this.wsBackoff

        const connect = () => {
            if (this._stop) return
            const ws = new WebSocket(this.wsUrl)
            this.ws = ws

            ws.onopen = () => {
                attempt = 0
                backoff = this.wsBackoff
                this.emit('open')
                if (typeof ws.ping === 'function') {
                    this._pingId = setInterval(() => {
                        try { ws.ping() } catch (_) { }
                    }, this.wsPingInterval)
                }
            }

            ws.onmessage = ({ data }) => {
                let msg = data
                try { msg = JSON.parse(data) } catch { }
                this.emit('message', msg)
            }

            ws.onclose = () => {
                clearInterval(this._pingId)
                if (this._stop) return
                attempt++
                const to = backoff * (1 + 0.1 * (2 * Math.random() - 1))
                setTimeout(connect, to)
                backoff *= 2
                if (attempt >= this.wsRetries) {
                    this.emit('error', new Error('Impossible de reconnecter le WebSocket'))
                    this._stop = true
                }
            }

            ws.onerror = err => {
                this.emit('error', err)
                ws.close()
            }
        }

        connect()
    }

    stopWebSocket() {
        this._stop = true
        if (this.ws) this.ws.close()
        clearInterval(this._pingId)
    }

    async sendWs(action, data) {
        const msg = JSON.stringify({ module: this.moduleId, action, data })
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(msg)
            return
        }
        await new Promise(resolve => this.once('open', resolve))
        this.ws.send(msg)
    }

    getBuffer() {
        return this.sendWs(ArtineoAction.GET, null)
    }

    setBuffer(bufferData) {
        return this.sendWs(ArtineoAction.SET, bufferData)
    }
}
