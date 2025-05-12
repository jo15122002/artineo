#!/usr/bin/env bash
set -e

# 1) Vérifie la commande dns-sd
if ! command -v dns-sd &>/dev/null; then
  echo "❌ Bonjour (dns-sd) introuvable sur ce système !"
  echo "   macOS intègre Bonjour par défaut, il faut alors :"
  echo "     • Vérifier votre version de macOS"
  echo "     • Réinstaller macOS si nécessaire"
  exit 1
fi
echo "✅ dns-sd trouvé : $(which dns-sd)"

# 2) Vérifie que mDNSResponder tourne
if ! pgrep -x mDNSResponder &>/dev/null; then
  echo "❌ Le démon mDNSResponder n'est pas lancé. Tentative de relance…"
  # relance via launchctl
  sudo launchctl load -w /System/Library/LaunchDaemons/com.apple.mDNSResponder.plist
  sudo killall -HUP mDNSResponder || true
  sleep 1
  if pgrep -x mDNSResponder &>/dev/null; then
    echo "✅ mDNSResponder relancé avec succès."
  else
    echo "❌ Échec du redémarrage de mDNSResponder."
    exit 1
  fi
else
  echo "✅ mDNSResponder est déjà en cours d’exécution."
fi

# 3) Test de résolution localement
echo
echo "Test rapide de résolution mDNS :"
dns-sd -G v4 "$(scutil --get LocalHostName).local" 2>/dev/null

echo
echo "Vous pouvez maintenant essayer depuis un autre poste :"
echo "  ping $(scutil --get LocalHostName).local"
