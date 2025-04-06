sudo apt-get update
sudo apt-get install gstreamer1.0-plugins-base gstreamer1.0-plugins-good gstreamer1.0-plugins-bad gstreamer1.0-plugins-ugly
pip3 install opencv-python numpy --break-system-packages
libcamera-hello
gst-launch-1.0 libcamerasrc ! video/x-raw,width=640,height=480,framerate=30/1 ! videoconvert ! autovideosink
python3 main.py