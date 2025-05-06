@echo off
setlocal

:: ----------------------------
:: reset_esp32.bat
:: Efface la flash de l’ESP32 et optionnellement flashe un firmware
:: Usage :
::   reset_esp32.bat [COM_PORT] [BAUD] [FIRMWARE_BIN]
:: Exemples :
::   reset_esp32.bat COM3 460800
::   reset_esp32.bat COM3 460800 firmware.bin
:: ----------------------------

:: 1) Valeurs par défaut
set "PORT=%~1"
if "%PORT%"=="" set "PORT=COM3"

set "BAUD=%~2"
if "%BAUD%"=="" set "BAUD=115200"

set "FW=%~3"

echo.
echo ==================================================
echo  ESP32 reset script
echo  Port    : %PORT%
echo  Baud    : %BAUD%
if "%FW%"=="" (
  echo  Firmware: (skipped)
) else (
  echo  Firmware: %FW%
)
echo ==================================================
echo.

:: 2) Vérifier qu’on peut appeler esptool via python
python -m esptool --help >nul 2>&1
if errorlevel 1 (
  echo ERREUR : Impossible de lancer esptool via "python -m esptool".
  echo Vérifiez que esptool est installé dans votre environnement Python.
  echo Installez-le avec : pip install esptool
  pause
  exit /b 1
)

:: 3) Effacer toute la flash
echo → Erase flash...
python -m esptool --chip esp32 --port %PORT% --baud %BAUD% erase_flash
if errorlevel 1 (
  echo ERREUR : Impossible d'effacer la flash.
  pause
  exit /b 1
)
echo ✓ Flash erased.

:: 4) (Optionnel) Flasher le firmware
if not "%FW%"=="" (
  if not exist "%FW%" (
    echo ERREUR : Fichier firmware "%FW%" non trouvé.
    pause
    exit /b 1
  )
  echo → Flashing firmware "%FW%"...
  python -m esptool --chip esp32 --port %PORT% --baud %BAUD% write_flash -z 0x1000 "%FW%"
  if errorlevel 1 (
    echo ERREUR : Impossible de flasher le firmware.
    pause
    exit /b 1
  )
  echo ✓ Firmware flashed.
)

echo.
echo ESP32 ready!
pause
endlocal