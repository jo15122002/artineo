
# MFRC522 Multi-Reader (Custom Version)

Ce package permet de gérer plusieurs lecteurs RFID RC522 simultanément sur Raspberry Pi avec Python 3.11+.

## Installation

Installer les dépendances :
```
pip install RPi.GPIO spidev mfrc522
```

## Utilisation

```python
from mfrc522_multi.rfid_reader import RFIDReader
import time

readers = [
    RFIDReader(cs_pin=8, rst_pin=22, name="Lecteur 1"),
    RFIDReader(cs_pin=7, rst_pin=27, name="Lecteur 2"),
    RFIDReader(cs_pin=25, rst_pin=17, name="Lecteur 3"),
]

try:
    while True:
        for reader in readers:
            tag = reader.read_tag()
            if tag:
                print(f"{tag['name']} -> ID: {tag['id']} | Texte: {tag['text']}")
        time.sleep(0.5)
except KeyboardInterrupt:
    for reader in readers:
        reader.cleanup()
```

## Structure

- `mfrc522_multi/rfid_reader.py` : Classe principale pour gérer un lecteur RFID
- `README.md` : Documentation rapide

---

**Version préparée par ChatGPT - Projet PFE 2024-2025**
