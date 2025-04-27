// main.js

const moduleId = 3;
const serverUrl = '127.0.0.1:8000';
let assignments, wanted, answers, ws;
let _lastBackgroundSet = null;
let _lastBuffer = { current_set: 1, uid1: null, uid2: null, uid3: null, button_pressed: false };

// 1. Stocke les SVG bruts pour blob1/blob2/blob3
const svgCache = {};

/**
 * 1️⃣ Récupère config + précharge SVG + lance WebSocket
 */
async function fetchConfig() {
    // 1.1 Config
    const res = await fetch(`http://${serverUrl}/config?module=${moduleId}`);
    const json = await res.json();
    assignments = json.config.assignments;
    answers = json.config.answers;

    // Prépare lookup
    wanted = {
        lieux: Object.entries(assignments.lieux || {}),
        couleurs: Object.entries(assignments.couleurs || {}),
        emotions: Object.entries(assignments.emotions || {})
    };

    // 1.2 Précharge tout de suite les SVG en texte
    await preloadSvgs();

    // 1.3 WebSocket + première requête + background initial
    setupWebSocket();
    requestBuffer();
    changeBackground(1);

    // 1.4 Buffer toutes les secondes
    setInterval(requestBuffer, 1000);
}
window.addEventListener('load', fetchConfig);
window.addEventListener('beforeunload', () => { if (ws) ws.close(); });

/**
 * Précharge les SVG dans svgCache[id] = texte SVG
 */
async function preloadSvgs() {
    const ids = ['blob1', 'blob2', 'blob3'];
    await Promise.all(ids.map(id =>
        fetch(`./assets/${id}.svg`)
            .then(r => {
                if (!r.ok) throw new Error(`${id}.svg introuvable`);
                return r.text();
            })
            .then(text => {
                svgCache[id] = text;
            })
            .catch(err => console.error(err))
    ));
    console.log('SVG préchargés', svgCache);
}

/**
 * Initialise la WebSocket et gère incoming buffer
 */
function setupWebSocket() {
    ws = new WebSocket(`ws://${serverUrl}/ws`);
    ws.onopen = () => console.log('WS ouverte');
    ws.onmessage = e => {
        let msg;
        try { msg = JSON.parse(e.data); }
        catch { return; }
        if (msg.action === 'get_buffer') {
            updateBlobs(msg.buffer);
        }
    };
    ws.onclose = () => setTimeout(setupWebSocket, 3000);
}

/** Envoie la requête “get” au serveur */
function requestBuffer() {
    if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ module: moduleId, action: 'get' }));
    }
}

/**
 * 4️⃣ Met à jour le texte de chaque blob et déclenche coloration si button_pressed
 */
function updateBlobs(buf) {
    // Texte
    ['blob1', 'blob2', 'blob3'].forEach((id, i) => {
        const el = document.getElementById(id);
        const uid = buf[`uid${i + 1}`];
        const arr = i === 0 ? wanted.lieux
            : i === 1 ? wanted.couleurs
                : wanted.emotions;
        const word = uid ? (arr.find(([w, u]) => u === uid) || [])[0] : '';
        el.textContent = word || 'Aucun';
    });

    // Background si set change
    if (buf.current_set !== _lastBuffer.current_set) {
        changeBackground(buf.current_set);
    }

    // Si bouton appuyé, on colore
    if (buf.button_pressed) {
        highlightBlobs(buf);
    }

    _lastBuffer = buf;
}

/**
 * 5️⃣ Coloration des blobs en recolorant les SVG de fond
 */
function highlightBlobs(buf) {
    if (buf.button_pressed == true) {
        const setIdx = (buf.current_set || 1) - 1;

        ['blob1', 'blob2', 'blob3'].forEach((id, i) => {
            const el = document.getElementById(id);
            const uid = buf[`uid${i + 1}`];
            const key = i === 0 ? 'lieu'
                : i === 1 ? 'couleur'
                    : 'emotion';

            // même logique que pour les LEDs
            const col = !uid
                ? '#FFA500'  // pas de carte
                : uid.toLowerCase() === answers[setIdx][key].toLowerCase()
                    ? '#00FF00' // correct
                    : '#FF0000';// incorrect

            // on applique juste la couleur de fond
            el.style.backgroundColor = col;
        });
    } else {
        // Si pas de bouton appuyé, on remet les SVG de fond
        ['blob1', 'blob2', 'blob3'].forEach((id, i) => {
            const el = document.getElementById(id);
            el.style.backgroundColor = 'white';
            el.innerHTML = svgCache[`blob${i + 1}`];
        });
    }
}


/**
 * 6️⃣ Change dynamiquement le PNG de fond
 */
function changeBackground(set) {
    if (set === _lastBackgroundSet) return;
    _lastBackgroundSet = set;

    fetch(`http://${serverUrl}/getAsset?module=${moduleId}&path=tableau${set}.png`)
        .then(res => {
            if (!res.ok) throw new Error("PNG introuvable");
            return res.blob();
        })
        .then(blob => {
            document.body.style.backgroundImage = `url(${URL.createObjectURL(blob)})`;
        })
        .catch(console.error);
}
