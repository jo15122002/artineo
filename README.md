# Artineo – Projet 2024–25

Un projet de fin d'année de master Gobelins

---

## Table des matières

- [Introduction](#introduction)  
- [Fonctionnalités](#fonctionnalités)  
- [Structure du dépôt](#structure-du-dépôt)  
- [Architecture](#architecture)  
- [Flux de données](#flux-de-données)  
- [Installation](#installation)  
- [Configuration](#configuration)  
- [Modules](#modules)  
  - [3RFID](#3rfid)  
  - [IR](#ir)  
  - [Kinect](#kinect)  
- [Usage](#usage)  
- [Licence](#licence)  

---

## Introduction

**Artineo** est un projet de fin d’études 2024–25 qui centralise plusieurs modules matériels autour d’un **backend** FastAPI/WebSocket et d’un **front-end** Nuxt.js.  
Chaque module embarqué (MicroPython ou Python) pousse ses données en temps réel vers le serveur, qui les redistribue à une application web interactive.

---

## Fonctionnalités

- **Communication fiable** via HTTP (fetch config) + WebSocket (push/pull de données)
- **Modules indépendants** pour RFID (3 lecteurs PN532), détection IR (OpenCV), pipeline Kinect (profiling, détection strokes & objets)
- **Front-end** Nuxt.js pour afficher/visualiser chaque module en son propre “layout”
- **Mise à l’échelle** facile : ajouter un nouveau module = ajouter un dossier `modules/<id>`

---

## Structure du dépôt

```

.
├── modules/
│   ├── 3RFID/           # MicroPython (esp32)
│   ├── IR/              # Python + OpenCV
│   └── kinect/          # Python + PyKinect2 + Pydantic
├── serveur/
│   ├── back/            # FastAPI + WebSocket
│   └── front/           # Nuxt.js + TypeScript
├── utils/               # scripts/utilitaires partagés
└── README.md

````

---

## Architecture

```mermaid
flowchart TB
  subgraph Matériel
    M1["Module 3RFID<br>(MicroPython)"]
    M2["Module IR<br>(Python)"]
    M3["Module Kinect<br>(Python)"]
  end
  subgraph Serveur
    S1["FastAPI<br>REST & WebSocket"]
    S2["Buffer<br>in-memory"]
  end
  subgraph Frontend
    F1["Nuxt.js<br>Pages & Composables"]
  end

  M1 --> S1
  M2 --> S1
  M3 --> S1
  S1 --> S2
  S1 --> F1
  F1 --> S1
````

---

## Flux de données

```mermaid
sequenceDiagram
  participant Modul as Module embarqué
  participant Serv as Serveur FastAPI
  participant Front as Front-end Nuxt.js

  %% Récup config
  Front->>Serv: GET /config?module=X
  Serv-->>Front: { config }

  %% Module → Serveur (push)
  Modul->>Serv: WS SET { module:X, data:{…} }
  Serv-->>Serv: stocke buffer[X]

  %% Serveur → Front (broadcast)
  Serv-->>Front: WS {"action":"get_buffer","module":X,"buffer":…}
  Front->>Front: met à jour l’UI
```

---

## Installation

### Prérequis

* **Python 3.9+**
* **Micropython** (ESP32 pour 3RFID)
* **Node.js 16+** & **npm** ou **yarn**

### Backend

```bash
cd serveur/back
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend

```bash
cd serveur/front
npm install    # ou yarn install
npm run dev    # ou yarn dev
```

### Modules embarqués

* **3RFID** (sur ESP32 via Thonny ou outil MicroPython)
* **IR** et **Kinect** s’exécutent dans un environnement Python local (pip install -r requirements.txt)

---

## Configuration

* Fichiers `.env.example` dans chaque dossier (modules/… et serveur/…)
* Dossier `serveur/back/configs/moduleX.json` pour les configs JSON
* Par défaut :

  * Host = `artineo.local`
  * Port = `8000`

---

## Modules

### 3RFID

* **Langage** : MicroPython
* **Brochage** : 3 × PN532 via SPI
* **Entrypoint** : `modules/3RFID/main.py`
* **Fonction** :

  * Lecture cyclique des tags RFID
  * Envoi d’un buffer `{ uid1, uid2, uid3, current_set }` par WS
  * Ping périodique pour maintenir la connexion

### IR

* **Langage** : Python
* **Entrypoint** : `modules/IR/main.py`
* **Fonction** :

  * Lecture d’un flux bgr24 sur stdin
  * Détection du cercle le plus brillant (Hough + mask)
  * Envoi `{ x, y, diameter }` par WS / HTTP fallback

### Kinect

* **Langage** : Python
* **Entrypoint** : `modules/kinect/main.py`
* **Pipeline** :

  1. Profil de fond (moyenne de N frames)
  2. Mapping profondeur → image 8-bits
  3. Extraction contours (morpho + seuil)
  4. Détection strokes ou objets selon outil actif
  5. Envoi des diffs (newStrokes, removeStrokes, newObjects, removeObjects)

---

## Usage

1. **Lancer le backend** (FastAPI + WebSocket)
2. **Démarrer chaque module** (3RFID sur ESP32, IR & Kinect localement)
3. **Démarrer le front** (`npm run dev`)
4. **Naviguer** vers :

   * `/modules/module1` → IR
   * `/modules/module3` → 3RFID
   * `/modules/module4` → Kinect
   * `/dashboard` pour un aperçu santé/modules

---