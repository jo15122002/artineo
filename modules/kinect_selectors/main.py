from machine import Pin
import time

# Boutons en pull-up, reliés à la masse quand appuyés
button1 = Pin(25, Pin.IN, Pin.PULL_UP)
button2 = Pin(26, Pin.IN, Pin.PULL_UP)

def on_button_released(pin):
    # Vérifie bien qu'on est en état haut (relâché)
    if pin.value() == 1:
        if pin is button1:
            print("🔘 Bouton 1 relâché")
        elif pin is button2:
            print("🔘 Bouton 2 relâché")
    # anti-rebond
    time.sleep_ms(50)

# On passe sur IRQ_RISING pour capter le relâchement
button1.irq(trigger=Pin.IRQ_RISING, handler=on_button_released)
button2.irq(trigger=Pin.IRQ_RISING, handler=on_button_released)

# Boucle principale vide
while True:
    time.sleep(1)
