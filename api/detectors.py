import cv2
import dlib

# Load once when module is imported
FACE_DETECTOR = dlib.get_frontal_face_detector()

EYE_CASCADE = cv2.CascadeClassifier(
    cv2.data.haarcascades + "haarcascade_eye.xml"
)

HAAR_FACE_CASCADE = cv2.CascadeClassifier(
    cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
)