#!/bin/bash

# --- Configuration ---
PYTHON_SCRIPT_NAME="main.py" # The name of your python script

# --- Script Start ---
echo "-------------------------------------"
echo "Starting Multi-RFID Reader Setup & Launch"
echo "-------------------------------------"
echo

# --- 1. Check SPI ---
echo "[INFO] Checking for SPI device..."
# Note: This doesn't guarantee SPI is correctly configured, only that the device file exists
if [ ! -e /dev/spidev0.0 ] && [ ! -e /dev/spidev0.1 ]; then
  echo "[WARNING] SPI device /dev/spidev0.0 or /dev/spidev0.1 not found!"
  echo "          Please ensure SPI is enabled using 'sudo raspi-config' (Interface Options -> SPI)."
  # Decide if you want to exit or just warn. We'll just warn for now.
  # read -p "Continue anyway? (y/N): " choice
  # [[ "$choice" =~ ^[Yy]$ ]] || exit 1
else
  echo "[OK] SPI device found (/dev/spidev0.0 or /dev/spidev0.1)."
fi
echo

# --- 2. Check Python 3 & Pip 3 ---
echo "[INFO] Checking for Python 3 and Pip 3..."
if ! command -v python3 &> /dev/null; then
    echo "[ERROR] python3 command not found. Please install Python 3."
    exit 1
fi
PYTHON_VERSION=$(python3 --version)
echo "[OK] Found Python 3: $PYTHON_VERSION"

if ! command -v pip3 &> /dev/null; then
    echo "[WARNING] pip3 command not found."
    read -p "Attempt to install python3-pip? (Y/n): " install_pip
    if [[ "$install_pip" =~ ^[Yy]?$ ]]; then # Default to Yes
        echo "Updating package list and installing python3-pip..."
        sudo apt-get update && sudo apt-get install -y python3-pip
        if ! command -v pip3 &> /dev/null; then
             echo "[ERROR] Failed to install pip3. Please install it manually (sudo apt install python3-pip)."
             exit 1
        fi
        echo "[OK] pip3 installed successfully."
    else
        echo "[ERROR] pip3 is required to install dependencies. Exiting."
        exit 1
    fi
else
    echo "[OK] Found pip3."
fi
echo

# --- 3. Check Python Dependencies ---
echo "[INFO] Checking Python dependencies (RPi.GPIO, mfrc522)..."
PACKAGES=("RPi.GPIO" "mfrc522")
NEEDS_INSTALL=()

for pkg in "${PACKAGES[@]}"; do
    # Use pip3 show to check if package is installed
    pip3 show "$pkg" &> /dev/null
    if [ $? -ne 0 ]; then
        echo "       - Package '$pkg' NOT found."
        NEEDS_INSTALL+=("$pkg")
    else
        echo "       - Package '$pkg' found."
    fi
done

if [ ${#NEEDS_INSTALL[@]} -ne 0 ]; then
    echo "[INFO] Attempting to install missing packages: ${NEEDS_INSTALL[*]}"
    # Use sudo for pip install as GPIO access often requires root privileges anyway
    if sudo pip3 install "${NEEDS_INSTALL[@]}"; then
        echo "[OK] Missing packages installed successfully."
    else
        echo "[ERROR] Failed to install Python packages."
        echo "        Please try installing manually: sudo pip3 install ${NEEDS_INSTALL[*]}"
        exit 1
    fi
else
    echo "[OK] All required Python packages are installed."
fi
echo

# --- 4. Check if Python script exists ---
echo "[INFO] Checking for Python script '$PYTHON_SCRIPT_NAME'..."
if [ ! -f "$PYTHON_SCRIPT_NAME" ]; then
    echo "[ERROR] Python script '$PYTHON_SCRIPT_NAME' not found in this directory ($(pwd))."
    exit 1
fi
echo "[OK] Found Python script: $PYTHON_SCRIPT_NAME"
echo

# --- 5. Launch the Python Script ---
echo "[INFO] Launching the RFID reader script..."
echo "       (Requires sudo for GPIO/SPI access)"
echo "       Press Ctrl+C to stop the script."
echo "-------------------------------------"
sudo python3 "$PYTHON_SCRIPT_NAME"

# Optional: Add a message after the script finishes (if it exits normally, not via Ctrl+C)
echo "-------------------------------------"
echo "[INFO] Python script finished."
echo "-------------------------------------"

exit 0