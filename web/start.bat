@echo off
REM -------------------------------------------------------------------
REM start.bat — Lance le build Nuxt puis ouvre Chrome en mode kiosque
REM Placez ce fichier à la racine de votre projet (même dossier que package.json)
REM -------------------------------------------------------------------

REM 1. Se placer dans le dossier du script
cd /d "%~dp0"

REM 2. Installer les dépendances si besoin
echo 📦 Installation des dépendances...
npm install

REM 3. Compiler l'application Nuxt
echo 🔨 Build de l'application Nuxt...
npm run build

REM 4. Lancer le serveur Nuxt en mode preview (en arrière-plan)
echo 🚀 Démarrage du serveur Nuxt (preview)...
start "NuxtPreview" /MIN cmd /C "npx nuxi preview --hostname 0.0.0.0 --port 3000"

REM 5. Laisser le serveur monter
timeout /t 5 /nobreak >nul

REM 6. Ouvrir Chrome en mode kiosque sur l'application
echo 🌐 Lancement de Chrome en mode kiosque...
start "" "C:\Program Files\Google\Chrome\Application\chrome.exe" --noerrdialogs --disable-infobars --kiosk http://localhost:3000

REM 7. Surveiller la fermeture de Chrome pour arrêter Nuxt
:waitLoop
    timeout /t 5 /nobreak >nul
    tasklist /FI "IMAGENAME eq chrome.exe" | findstr /I "chrome.exe" >nul
    if ERRORLEVEL 1 goto stopNuxt
goto waitLoop

:stopNuxt
    echo 🛑 Chrome fermé, arrêt du serveur Nuxt...
    taskkill /F /IM node.exe >nul 2>&1
exit /B
