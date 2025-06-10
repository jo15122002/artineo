#!/bin/bash
# filepath: c:\Users\lapin\Documents\Gobelins\Mon_Dossier_De_Travail\Projet_fin_d_annee\dev\utils\clean_build.bash

# Couleurs pour l'affichage
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo "========================================"
echo "Script de nettoyage des fichiers build"
echo "========================================"
echo "Répertoire courant: $(pwd)"

# Se placer dans le dossier parent (dev)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/.."
echo "Nouveau répertoire: $(pwd)"
echo

echo "Vérification de la structure des dossiers..."
if [ -d "./serveur/front" ]; then
    echo -e "${GREEN}[OK]${NC} Dossier serveur/front trouvé"
else
    echo -e "${RED}[ERREUR]${NC} Dossier serveur/front introuvable"
fi

if [ -d "./serveur/back" ]; then
    echo -e "${GREEN}[OK]${NC} Dossier serveur/back trouvé"
else
    echo -e "${RED}[ERREUR]${NC} Dossier serveur/back introuvable"
fi
echo

echo "Suppression des fichiers temporaires de Nuxt..."
if [ -d "./serveur/front/node_modules" ]; then
    echo "Suppression de ./serveur/front/node_modules..."
    if rm -rf "./serveur/front/node_modules"; then
        echo -e "${GREEN}[OK]${NC} node_modules supprimé"
    else
        echo -e "${RED}[ERREUR]${NC} Échec suppression node_modules"
    fi
else
    echo -e "${YELLOW}[INFO]${NC} ./serveur/front/node_modules n'existe pas"
fi

if [ -d "./serveur/front/.nuxt" ]; then
    echo "Suppression de ./serveur/front/.nuxt..."
    if rm -rf "./serveur/front/.nuxt"; then
        echo -e "${GREEN}[OK]${NC} .nuxt supprimé"
    else
        echo -e "${RED}[ERREUR]${NC} Échec suppression .nuxt"
    fi
else
    echo -e "${YELLOW}[INFO]${NC} ./serveur/front/.nuxt n'existe pas"
fi

if [ -d "./serveur/front/.output" ]; then
    echo "Suppression de ./serveur/front/.output..."
    if rm -rf "./serveur/front/.output"; then
        echo -e "${GREEN}[OK]${NC} .output supprimé"
    else
        echo -e "${RED}[ERREUR]${NC} Échec suppression .output"
    fi
else
    echo -e "${YELLOW}[INFO]${NC} ./serveur/front/.output n'existe pas"
fi

if [ -f "./serveur/front/package-lock.json" ]; then
    echo "Suppression de ./serveur/front/package-lock.json..."
    if rm -f "./serveur/front/package-lock.json"; then
        echo -e "${GREEN}[OK]${NC} package-lock.json supprimé"
    else
        echo -e "${RED}[ERREUR]${NC} Échec suppression package-lock.json"
    fi
else
    echo -e "${YELLOW}[INFO]${NC} ./serveur/front/package-lock.json n'existe pas"
fi

echo
echo "Suppression de l'environnement virtuel Python..."
if [ -d "./serveur/back/env" ]; then
    echo "Suppression de ./serveur/back/env..."
    if rm -rf "./serveur/back/env"; then
        echo -e "${GREEN}[OK]${NC} env supprimé"
    else
        echo -e "${RED}[ERREUR]${NC} Échec suppression env"
    fi
else
    echo -e "${YELLOW}[INFO]${NC} ./serveur/back/env n'existe pas"
fi

if [ -d "./serveur/back/__pycache__" ]; then
    echo "Suppression de ./serveur/back/__pycache__..."
    if rm -rf "./serveur/back/__pycache__"; then
        echo -e "${GREEN}[OK]${NC} __pycache__ supprimé"
    else
        echo -e "${RED}[ERREUR]${NC} Échec suppression __pycache__"
    fi
else
    echo -e "${YELLOW}[INFO]${NC} ./serveur/back/__pycache__ n'existe pas"
fi

# Recherche récursive des dossiers __pycache__
echo
echo "Recherche récursive des dossiers __pycache__..."
find "./serveur/back" -type d -name "__pycache__" 2>/dev/null | while read -r dir; do
    if [ -d "$dir" ]; then
        echo "Suppression de $dir..."
        rm -rf "$dir"
    fi
done

echo
echo "========================================"
echo -e "${GREEN}Nettoyage terminé !${NC}"
echo "========================================"

# Attendre une entrée utilisateur (équivalent de pause)
read -p "Appuyez sur Entrée pour continuer..."