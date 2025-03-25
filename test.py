from picamera2 import Picamera2
import cv2
import time

picam2 = Picamera2()
picam2.preview_configuration.main.size = (800, 480)
picam2.preview_configuration.main.format = "RGB888"
picam2.configure("preview")
picam2.start()

while True:
    frame = picam2.capture_array()
    cv2.imshow("PiCam2 Feed", frame)

    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

picam2.stop()
cv2.destroyAllWindows()
