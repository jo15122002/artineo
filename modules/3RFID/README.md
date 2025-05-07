# Projet RFID Multi-Lecteurs avec ESP32 et MicroPython

Ce projet intègre trois lecteurs RFID MFRC522 connectés à un ESP32 fonctionnant sous MicroPython.  
Il permet de lire les UID de cartes RFID via trois modules distincts et de vérifier ces UID par rapport à différents sets de réponses (lieu, couleur, émotion) grâce à une logique d'essais multiples.  
L'interface utilisateur se fait via un bouton qui déclenche la lecture et des LED NeoPixel (une par lecteur) qui affichent le statut de la lecture (aucune carte, réponse correcte ou incorrecte) avec une intensité ajustable.

## Fonctionnalités

- **Multi-lecteurs RFID :**  
  Trois modules MFRC522 partagent le même bus SPI, chacun ayant ses propres broches CS et RST.

- **Lecture d'UID et vérification :**  
  À l'appui du bouton, le système lit les UID de chaque lecteur et compare ces UID aux valeurs correctes d'un set défini.

- **Jeux de réponses configurables :**  
  La fonction `get_answers(number)` permet de récupérer différents sets de réponses (sous forme de JSON en dur) pour vérifier les réponses lues.  
  La fonction `check_answers()` utilise ce set pour comparer et afficher les résultats.

- **Gestion des essais :**  
  L'utilisateur dispose de 3 essais par "tableau" (set de réponses). Une fois les 3 essais utilisés ou si les réponses sont correctes, le système passe au set suivant (via `get_answers(number+1)`).

- **Feedback visuel avec NeoPixel :**  
  Chaque lecteur est associé à une LED NeoPixel dont la couleur indique le résultat :  
  - Orange : Aucune carte détectée  
  - Vert : Réponse correcte  
  - Rouge : Réponse incorrecte  
  L'intensité des LED peut être ajustée via la variable globale `intensity`.

- **Assignation de cartes :**  
  Un mode d'assignation permet de lier des mots-clés à des UID de cartes RFID et de sauvegarder ces associations dans le fichier `assignments.json`.

- **Cooldown entre essais :**  
  Un délai de cooldown (configurable) est appliqué entre les appuis pour éviter des déclenchements trop rapprochés.

## Matériel requis

- **ESP32 Wroom-32** avec MicroPython installé.
- Trois modules **RFID MFRC522**.
- Trois LED **WS2812b (NeoPixel)**.
- Un bouton-poussoir.
- Câblage et alimentation adaptés.

### Exemple de connexions

- **Bus SPI (communs aux trois lecteurs) :**
  - SCK : GPIO12
  - MOSI : GPIO23
  - MISO : GPIO13
- **Lecteur 1 :**  
  - RST : GPIO4  
  - CS  : GPIO5
- **Lecteur 2 :**  
  - RST : GPIO16  
  - CS  : GPIO17
- **Lecteur 3 :**  
  - RST : GPIO25  
  - CS  : GPIO26
- **LED NeoPixel :**  
  - LED 1 : connecté à GPIO15  
  - LED 2 : connecté à GPIO18  
  - LED 3 : connecté à GPIO19
- **Bouton :**  
  - Connecté à GPIO14 en mode pull-up (le bouton relie la broche à 0 lorsqu'il est appuyé)

## Logiciel et installation

- **MicroPython** (version 1.19.1 ou supérieure recommandée)
- Bibliothèques utilisées :  
  - [mfrc522](https://github.com/cefn/micropython-mfrc522) (votre version modifiée avec documentation)
  - neopixel (inclus dans MicroPython)
  - ujson (inclus dans MicroPython)
- **Chargement des fichiers :**  
  Vous pouvez utiliser [mpfshell](https://github.com/wendlers/mpfshell) ou [WebREPL](https://micropython.org/webrepl/) pour transférer les fichiers suivants sur la mémoire flash de l'ESP32 :
  - `main.py` (le script principal ci-dessous)
  - `mfrc522.py` (la bibliothèque RFID, version modifiée avec docstrings)

## Utilisation

Au démarrage, le programme exécute la fonction `setup()` qui configure le SPI, les lecteurs RFID, les LED et le bouton.  
Le programme propose deux modes (lecture/vérification et assignation) – par défaut, le mode lecture est activé (mode "r").  
Chaque appui sur le bouton correspond à un essai pour lire les UID des trois lecteurs.  
L'utilisateur dispose de 3 essais par set de réponses. Si les 3 essais sont utilisés ou si toutes les réponses sont correctes, le programme passe au set suivant (via `get_answers(number+1)`).

Les LED des lecteurs s'actualisent dans la fonction `check_answers()` en fonction de la correspondance :
- Aucune carte détectée → LED orange
- UID correct → LED verte
- UID incorrect → LED rouge

Un cooldown (par exemple 3 secondes) est appliqué entre deux essais pour éviter les déclenchements trop rapprochés.

### Pour lancer le programme

- Connectez correctement votre matériel.
- Transférez les fichiers sur l'ESP32.
- Redémarrez l'ESP32 et lancez le script principal (ex. via le REPL : `import main`).

## Personnalisation

- **Intensité des LED :**  
  Modifiez la variable globale `intensity` (entre 0 et 1) pour régler la luminosité des LED.
  
- **Jeux de réponses :**  
  La fonction `get_answers(number)` contient un dictionnaire de sets de réponses. Vous pouvez ajouter ou modifier ces sets selon vos besoins.

- **Nombre d'essais et cooldown :**  
  Ajustez la constante `MAX_ATTEMPTS` (dans le mode lecture) et le temps de cooldown (ici défini par `COOLDOWN_SECONDS` dans la version précédente) pour personnaliser la logique d'essai.

## Structure des fichiers

- **main.py :**  
  Le script principal qui gère la lecture des RFID, la vérification des réponses, la gestion des essais et des sets, ainsi que l'assignation de cartes.

- **mfrc522.py :**  
  La bibliothèque pour contrôler le module MFRC522, avec documentation sur chaque fonction.

- **assignments.json :**  
  Fichier de sauvegarde des associations entre mots-clés et UID (créé et mis à jour par `assign_cards()`).

## Licence

Ce projet est distribué sous licence MIT.

## Remerciements

- Merci aux développeurs de la bibliothèque [micropython-mfrc522](https://github.com/cefn/micropython-mfrc522) pour leur travail de portage.
- Les exemples et conseils de câblage proviennent de diverses ressources sur l'utilisation des modules MFRC522 et NeoPixel en MicroPython.