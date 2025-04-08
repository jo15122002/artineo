import time

import picamera

# Create a camera object
camera = picamera.PiCamera()

# Set camera resolution (optional)
camera.resolution = (2592, 1944)  # Maximum resolution for the OV5647

# Set camera rotation (optional)
camera.rotation = 180  # Rotate the image 180 degrees if needed

# Preview the camera (optional)
camera.start_preview()
time.sleep(2)  # Give the camera a moment to warm up

# Capture an image
image_path = '/home/pi/image.jpg'
camera.capture(image_path)

# Stop the preview
camera.stop_preview()

# Close the camera
camera.close()

print(f"Image captured and saved to {image_path}")