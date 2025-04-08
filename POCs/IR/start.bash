sudo apt update && sudo apt upgrade -y

sudo apt-get install -y \
    python3 python3-pip python3-opencv \
    libcamera-apps \
    gstreamer1.0-tools \
    gstreamer1.0-plugins-base \
    gstreamer1.0-plugins-good

libcamera-hello -t 5000 --nopreview

v4l2-ctl --list-devices
