#!/usr/bin/env bash
set -e

# Vérifie qu'on est en root (ou avec sudo)
if [[ $EUID -ne 0 ]]; then
  echo "❗️ Merci de lancer ce script avec sudo : sudo $0"
  exit 1
fi

HOST="artineo"

echo "⚙️  Configuration du nom de l’hôte en '${HOST}'…"

# Définit les trois noms principaux
scutil --set ComputerName     "${HOST}"
scutil --set HostName         "${HOST}"
scutil --set LocalHostName    "${HOST}"

# Recharge mDNSResponder pour prendre en compte le changement
killall -HUP mDNSResponder

echo "✅ Le Mac est désormais nommé '${HOST}'."
echo "   Vous pouvez y accéder via: http://${HOST}.local"
