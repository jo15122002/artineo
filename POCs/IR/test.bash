libcamera-vid -t 0 --width 640 --height 480 --inline --codec yuv420 --output - | \
ffmpeg -loglevel error \
-f rawvideo -pix_fmt yuv420p -s 640x480 -i - \
-f rawvideo -pix_fmt bgr24 - | \
python3 cam_debug.py