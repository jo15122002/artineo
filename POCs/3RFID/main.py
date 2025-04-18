#!/usr/bin/env python3

import RPi.GPIO as GPIO
from mfrc522 import MFRC522
import time
import threading
import signal
import sys

# --- Configuration ---
# Define GPIO pins for RST (Reset) and CS (Chip Select/SDA) for each reader
# Format: (RST_PIN, CS_PIN, READER_NAME)
READER_PINS = [
    (17, 8,  "Reader 1 (CE0)"), # Using CE0 (GPIO 8) for CS
    (27, 7,  "Reader 2 (CE1)"), # Using CE1 (GPIO 7) for CS
    (22, 25, "Reader 3 (GPIO25)") # Using GPIO 25 for CS
]

# --- Global Variables ---
readers = []
running = True # Flag to control the threads

# --- RFID Reading Function ---
def read_rfid(reader_instance, reader_name):
    """
    Function executed by each thread to continuously read RFID tags.
    """
    print(f"Thread started for {reader_name}")
    last_tag_time = 0
    last_tag_id = None
    debounce_time = 1.0 # Seconds to wait before reporting the same tag again

    while running:
        try:
            # Scan for tags
            status, TagType = reader_instance.MFRC522_Request(reader_instance.PICC_REQIDL)

            # If a tag is found
            if status == reader_instance.MI_OK:
                # Get the UID of the tag
                status, uid = reader_instance.MFRC522_Anticoll()

                if status == reader_instance.MI_OK:
                    tag_id = "-".join([str(x) for x in uid])
                    current_time = time.time()

                    # Debounce: Only print if it's a new tag or enough time has passed
                    if tag_id != last_tag_id or (current_time - last_tag_time) > debounce_time:
                        print(f"{reader_name} detected Tag ID: {tag_id}")
                        last_tag_id = tag_id
                        last_tag_time = current_time
                    # else:
                        # Optional: print("Debounced duplicate tag:", tag_id)
                        # pass

        except Exception as e:
            # Handle potential communication errors (less frequent with MFRC522)
            print(f"Error reading from {reader_name}: {e}")
            time.sleep(0.5) # Wait a bit before retrying after an error

        # Small delay to prevent high CPU usage
        time.sleep(0.1)

    print(f"Thread stopped for {reader_name}")

# --- Signal Handler for Graceful Exit ---
def signal_handler(sig, frame):
    global running
    print("\nCtrl+C detected. Stopping readers...")
    running = False # Signal threads to stop
    # Wait a moment for threads to potentially finish their current loop cycle
    time.sleep(0.5)
    GPIO.cleanup()
    print("GPIO cleaned up. Exiting.")
    sys.exit(0)

# --- Main Program ---
if __name__ == "__main__":
    # Setup signal handler for Ctrl+C
    signal.signal(signal.SIGINT, signal_handler)

    print("Starting RFID reader system...")
    print("Press Ctrl+C to exit.")

    # Set GPIO mode
    # Using BCM mode is generally recommended over BOARD mode
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False) # Disable GPIO warnings

    # Initialize reader objects
    print("Initializing readers...")
    for rst_pin, cs_pin, name in READER_PINS:
        try:
            # The MFRC522 library constructor might vary slightly.
            # Common parameters are (bus=0, device= (relevant for CE0/CE1), spidev_speed, pin_rst, pin_ce)
            # Check the specific library's documentation if this doesn't work.
            # We explicitly provide pin_ce (chip enable/select) and pin_rst (reset).
            # bus=0 and device=0 are often defaults but we rely on pin_ce here.
            reader = MFRC522(pin_rst=rst_pin, pin_ce=cs_pin)
            readers.append((reader, name))
            print(f" - {name} initialized (RST: GPIO{rst_pin}, CS: GPIO{cs_pin})")
        except Exception as e:
            print(f"Failed to initialize {name} on RST: {rst_pin}, CS: {cs_pin}. Error: {e}")
            # Optional: exit if a reader fails to initialize
            # GPIO.cleanup()
            # sys.exit(1)

    if not readers:
        print("No readers were initialized successfully. Exiting.")
        GPIO.cleanup()
        sys.exit(1)

    # Create and start threads for each reader
    threads = []
    print("Starting reader threads...")
    for reader_instance, reader_name in readers:
        thread = threading.Thread(target=read_rfid, args=(reader_instance, reader_name), daemon=True)
        thread.start()
        threads.append(thread)

    # Keep the main thread alive while other threads run
    # The signal handler will eventually set running to False
    while running:
        time.sleep(1)

    # This part is usually reached only if running is set to False externally,
    # but the signal handler is the primary exit mechanism.
    print("Main loop finished (should normally be interrupted by Ctrl+C).")
    # GPIO cleanup is handled by the signal handler