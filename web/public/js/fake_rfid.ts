// fake_rfid.ts
import { RFIDMessage } from './types'

// Assure-toi que `ws` est initialisé quelque part avant cet intervalle.
declare const ws: WebSocket

// Envoie un message au serveur toutes les 5 secondes
setInterval(() => {
  const msg: RFIDMessage = {
    module: 3,
    action: 'set',
    data: {
      uid1: '880424973f',
      uid2: '8804d091cd',
      uid3: '8804fa8cfa',
      current_set: 1,
      button_pressed: true
    }
  }

  ws.send(JSON.stringify(msg))
  console.log('Message sent to server')
}, 5000)
