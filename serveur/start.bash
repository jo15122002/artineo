# Setup du nom d'hôte
sudo scutil --set LocalHostName "artineo"

sudo launchctl list | grep mDNSResponder

python3 -m venv env
source env/bin/activate   # Sur macOS/Linux

pip install fastapi uvicorn

uvicorn main:app --reload --host 0.0.0.0 --port 8000