const moduleId = 3;
const serverUrl = '127.0.0.1:8000';
let assignments, wanted, ws;
let _lastBackgroundSet = null;

// 1. Récupère la config (assignments)
async function fetchConfig() {
    const res = await fetch(`http://${serverUrl}/config?module=${moduleId}`);
    const json = await res.json();
    assignments = json.config.assignments;
    // construit wanted pour parcourir facilement
    wanted = {
        lieux: Object.entries(assignments.lieux || {}),
        couleurs: Object.entries(assignments.couleurs || {}),
        emotions: Object.entries(assignments.emotions || {})
    };
    setupWebSocket();
    requestBuffer();
    changeBackground(1);
    setInterval(requestBuffer, 1000);
}

// 2. Initialise la WS
function setupWebSocket() {
    ws = new WebSocket(`ws://${serverUrl}/ws`);
    ws.onopen = () => console.log('WS ouverte');
    ws.onmessage = e => {
        let msg;
        try { msg = JSON.parse(e.data); }
        catch (_) { return; }
        if (msg.action === 'get_buffer') {
            updateBlobs(msg.buffer);
        }
    };
    ws.onclose = () => setTimeout(setupWebSocket, 3000);
}

// 3. Demande le buffer
function requestBuffer() {
    if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ module: moduleId, action: 'get' }));
    }
}

// 4. Met à jour chaque blob en fonction de uid1/2/3
function updateBlobs(buf) {
    ['blob1', 'blob2', 'blob3'].forEach((id, i) => {
        const el = document.getElementById(id);
        const uid = buf[`uid${i + 1}`];
        const arr = i === 0 ? wanted.lieux
            : i === 1 ? wanted.couleurs
                : wanted.emotions;
        const word = uid ? (arr.find(([w, u]) => u === uid) || [])[0] : '';
        el.textContent = word || 'Aucun';
    });
}

function changeBackground(set) {
    if (set === _lastBackgroundSet) return;  // cache simple
    _lastBackgroundSet = set;

    fetch(`http://${serverUrl}/getAsset?module=${moduleId}&path=tableau${set}.png`)
        .then(res => {
            if (!res.ok) throw new Error("Fichier non trouvé");
            return res.blob();
        })
        .then(blob => {
            document.body.style.backgroundImage = `url(${URL.createObjectURL(blob)})`;
        })
        .catch(console.error);
}

window.addEventListener('load', fetchConfig);
window.addEventListener('beforeunload', () => {
    if (ws) ws.close();
});