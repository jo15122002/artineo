sudo apt-get update && sudo apt-get upgrade -y
sudo apt-get install -y python3 python3-pip python3-opencv gstreamer1.0-tools \
    gstreamer1.0-plugins-base gstreamer1.0-plugins-good
pip3 install --upgrade pip
pip3 install opencv-python numpy --break-system-packages
libcamera-vid -t 5000 --nopreview --inline -o /dev/null
