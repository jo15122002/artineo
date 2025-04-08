sudo apt update && sudo apt upgrade -y

sudo apt-get install -y \
    python3 python3-pip python3-opencv \
    libcamera-apps \
    gstreamer1.0-tools \
    gstreamer1.0-plugins-base \
    gstreamer1.0-plugins-good

libcamera-hello -t 5000 --nopreview

v4l2-ctl --list-devices

sudo apt-get install v4l2loopback-dkms

sudo modprobe -r v4l2loopback
sudo modprobe v4l2loopback video_nr=2 card_label="CameraLoop" exclusive_caps=1 max_buffers=4

libcamera-vid -t 0 --nopreview --inline --codec yuv420 --width 1296 --height 972 --output /dev/video2

gst-launch-1.0 v4l2src device=/dev/video2 ! "video/x-raw,format=I420,width=1296,height=972,framerate=30/1" ! videoscale ! "video/x-raw,width=320,height=240" ! videoconvert ! autovideosink