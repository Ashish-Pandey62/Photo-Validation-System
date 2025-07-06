import dlib
import cv2

def valid_head_check(image):

    faces = detect_faces(image)

    # Print the number of detected faces
    num_faces = len(faces)
    #print("Number of faces detected:", num_faces)

    # Draw rectangles around the detected faces
    if not num_faces == 0:
        for rect in faces:
            x, y, w, h = rect.left(), rect.top(), rect.width(), rect.height()
            cv2.rectangle(image, (x, y), (x + w, y + h), (0, 255, 0), 2)
            proper_head_percentage = calculate_head_percentage(rect, image)

 

    # #pyt Display the image with detected faces
    # cv2.imshow("Detected Faces", image)
    # cv2.waitKey(0)
    # cv2.destroyAllWindows()
    
    if (num_faces == 1 and (10<proper_head_percentage<80)):
        print("head percent" ,proper_head_percentage)
        return True, proper_head_percentage
    elif(num_faces == 1 and (proper_head_percentage<10 or proper_head_percentage>80)):
        return False, proper_head_percentage
    elif(num_faces == 0):
        return False, 101
    else:
        return False, 102
    
def detect_eyes(image):
    # Load the pre-trained eye cascade classifier from OpenCV
    eye_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_eye.xml')
    
    # Convert the image to grayscale for eye detection
    gray_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    # Detect eyes using the eye cascade classifier
    eyes = eye_cascade.detectMultiScale(gray_image, scaleFactor=1.1, minNeighbors=5)
    #print("no of eyes", len(eyes))
    return len(eyes) == 0

def calculate_head_percentage(face, image):
    face_area = face.width() * face.height()
    image_area = image.shape[0] * image.shape[1]
    head_percentage = (face_area / image_area) * 100
    return head_percentage

def detect_faces(image):
    # Load the pre-trained face detection model from dlib
    face_detector = dlib.get_frontal_face_detector()
    
    # Convert the image to grayscale for face detection
    gray_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    # Detect faces in the grayscale image
    faces = face_detector(gray_image)
    return faces
