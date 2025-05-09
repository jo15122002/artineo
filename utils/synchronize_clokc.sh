#!/bin/bash

echo "🌐 Récupération de l'heure via HTTPS (Cloudflare)..."
http_date=$(curl -sI https://cloudflare.com | grep '^Date:' | cut -d' ' -f2-)

if [ -z "$http_date" ]; then
  echo "❌ Impossible de récupérer l'heure via HTTPS."
  exit 1
fi

echo "🕒 Heure récupérée : $http_date"

# Convertir en format utilisable par la commande date
date_cmd=$(date -d "$http_date" "+%Y-%m-%d %H:%M:%S")

echo "⏱️ Mise à jour de l'heure système : $date_cmd"
sudo date -s "$date_cmd"

echo "✅ Heure mise à jour manuellement."
timedatectl status