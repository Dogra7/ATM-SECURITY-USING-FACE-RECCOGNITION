import os
import cv2
import numpy as np
import json
import psycopg2
from psycopg2 import Error
from flask import Flask, render_template, request, redirect, url_for, jsonify, session, Response
from flask_mail import Mail, Message
from datetime import datetime
import face_recognition
import random
from atm import app_atm # type: ignore


app = Flask(__name__)
app.secret_key = 'deep7'
app.config['UPLOAD_FOLDER'] = 'faces'
app.config['GRAY_FACE'] = 'face_data'
app.register_blueprint(app_atm)

# Initialize the global variable to store the latest RFID UID
latest_uid = None

FACE_DATA_DIR = 'face_data'

# Initialize arrays to store face encodings and names
known_face_encodings = []
known_face_names = []
recognized_face_name = "Unknown"  # Initialize the global variable

# Configure Flask-Mail
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USE_SSL'] = False
app.config['MAIL_USERNAME'] = 'deepmhatre007@gmail.com'
app.config['MAIL_PASSWORD'] = 'dkrnkwygcefhmaov'  
mail = Mail(app)


def detect_spoof(gray_frame):
    """
    Performs spoof detection using Local Binary Patterns (LBP) with scikit-image.
    """
    try:
        # 1. Calculate LBP (using scikit-image)
        radius = 1  # Adjust radius as needed
        n_points = 8 * radius  # Number of neighbors
        lbp = local_binary_pattern(gray_frame, n_points, radius, method="uniform")  # "uniform" is often a good choice

        # 2. Extract Histogram Features
        hist, _ = np.histogram(lbp.ravel(), bins=np.arange(0, n_points + 2), range=(0, n_points + 1)) # Bins according to the LBP type
        hist = hist.astype("float") / (hist.sum() + 1e-7)  # Normalize

        # 3. Classify (Needs training data and a classifier)
        threshold = 0.2 # Example threshold - NEEDS TRAINING
        spoof_score = np.sum(hist[5:]) # Example score (adjust indices)

        if spoof_score < threshold: # Example condition - NEEDS TRAINING
            return True # Real face
        else:
            return False # Spoof

    except Exception as e:
        print(f"Spoof detection error: {e}")
        return False

def load_known_faces():
    for filename in os.listdir(app.config['UPLOAD_FOLDER']):
        if filename.endswith(('.jpg', '.jpeg', '.png')):
            image = face_recognition.load_image_file(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            face_encodings = face_recognition.face_encodings(image)
            if len(face_encodings) > 0:
                known_face_encodings.append(face_encodings[0])
                known_face_names.append(os.path.splitext(filename)[0])

load_known_faces()

def extract_features(face_roi):
    # Replace this with actual feature extraction logic
    return np.random.rand(128)

def get_db_connection():
    try:
        connection = psycopg2.connect(
            user="postgres",
            password="deep1234",
            host="localhost",
            port="5432",
            database="ATM SECURITY"
        )
        return connection
    except (Exception, Error) as error:
        print("Error while connecting to PostgreSQL", error)

@app.route('/')
def index():
    return render_template('account.html')

@app.route('/add_face', methods=['POST'])
def add_face():
    file = request.files['image']
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
    file.save(file_path)
    name = os.path.splitext(file.filename)[0]
    image = cv2.imread(file_path)
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
    faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))
    if len(faces) != 1:
        return "Error: Please upload an image with exactly one face"
    x, y, w, h = faces[0]
    face_roi = gray[y:y+h, x:x+w]
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S%f')
    face_file_name = f'{name}_{timestamp}.jpg'
    face_file_path = os.path.join(app.config['UPLOAD_FOLDER'], face_file_name)
    cv2.imwrite(face_file_path, face_roi)
    face_features = extract_features(face_roi)
    face_data = {
        'name': name,
        'timestamp': timestamp,
        'file_path': face_file_name,
        'features': face_features.tolist()
    }
    if not os.path.exists(FACE_DATA_DIR):
        os.makedirs(FACE_DATA_DIR)
    face_data_file_path = os.path.join(FACE_DATA_DIR, f'{name}_{timestamp}.json')
    with open(face_data_file_path, 'w') as json_file:
        json.dump(face_data, json_file)
    load_known_faces()  # Reload faces after adding a new one
    return redirect(url_for('admin'))

@app.route('/video_feed')
def video_feed():
    def gen_frames():
        global recognized_face_name
        video_capture = cv2.VideoCapture(0)
        while True:
            ret, frame = video_capture.read()
            if not ret:
                break

            gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) # For LBP
            small_frame = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)
            rgb_small_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)

            face_locations = face_recognition.face_locations(rgb_small_frame)
            face_encodings = face_recognition.face_encodings(rgb_small_frame, face_locations)
            face_names = []

            for (top, right, bottom, left), face_encoding in zip(face_locations, face_encodings):
                # Spoof Detection before face recognition
                top *= 4  # Scale back to original frame size
                right *= 4
                bottom *= 4
                left *= 4
                face_roi_gray = gray_frame[top:bottom, left:right]  # ROI for spoof detection in original frame
                is_real = detect_spoof(face_roi_gray)

                if is_real:  # Only proceed with face recognition if real face
                    matches = face_recognition.compare_faces(known_face_encodings, face_encoding)
                    name = "Unknown"
                    face_distances = face_recognition.face_distance(known_face_encodings, face_encoding)
                    best_match_index = np.argmin(face_distances)
                    if matches[best_match_index]:
                        name = known_face_names[best_match_index]
                    face_names.append(name)
                    recognized_face_name = name
                else:
                    name = "Spoof Detected!"  # Or some other indication
                    face_names.append(name)
                    recognized_face_name = name # Update the global variable
                    
                # Drawing boxes and labels (modified to include spoof detection result)
                cv2.rectangle(frame, (left, top), (right, bottom), (0, 0, 255), 2)
                cv2.rectangle(frame, (left, bottom - 35), (right, bottom), (0, 0, 255), cv2.FILLED)
                font = cv2.FONT_HERSHEY_DUPLEX
                cv2.putText(frame, name, (left + 6, bottom - 6), font, 1.0, (255, 255, 255), 1)

            ret, buffer = cv2.imencode('.jpg', frame)
            frame_bytes = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

    return Response(gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route('/get_recognized_face_name')
def get_recognized_face_name():
    global recognized_face_name
    return jsonify({'recognized_face_name': recognized_face_name})


@app.route('/update_uid', methods=['POST'])
def update_uid():
    global latest_uid
    latest_uid = request.json.get('rfid_uid')  # UID sent as JSON
    print(f"Updated UID: {latest_uid}")
    return jsonify({'status': 'success'})

# Endpoint to get the latest UID and corresponding account name
@app.route('/get_latest_uid', methods=['GET'])
def get_latest_uid():
    global latest_uid
    if latest_uid:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('SELECT cus_name, cus_accountno FROM customer1 WHERE rfid_uid = %s', (latest_uid,))
        result = cur.fetchone()
        cur.close()
        conn.close()

        if result:
            session['account_name'] = result[0]  # Store account name in session
            session['account_number'] = result[1]  # Store account number in session
            session['rfid_uid'] = latest_uid    # Store UID in session
            response = jsonify({'rfid_uid': latest_uid, 'account_name': result[0], 'redirect': True})
            latest_uid = None  # Reset the latest UID            
            return response
        else:
            latest_uid = None  # Reset the latest UID                        
            return jsonify({'rfid_uid': latest_uid, 'account_name': None, 'redirect': False})
    else:
        return jsonify({'rfid_uid': None, 'account_name': None, 'redirect': False})

def generate_otp():
    return str(random.randint(100000, 999999))

@app.route('/get_email')
def get_email():
    account_number = session.get('account_number')  # Retrieve stored account number
    email = None
    if account_number:
        try:
            connection = get_db_connection()
            cursor = connection.cursor()
            query = "SELECT cus_email FROM customer1 WHERE cus_accountno = %s"
            cursor.execute(query, (account_number,))
            email_record = cursor.fetchone()
            cursor.close()
            connection.close()
            if email_record:
                email = email_record[0]  # Get the email from the fetched record
        except (Exception, Error) as error:
            print("Error fetching email from PostgreSQL", error)
    
    return jsonify({'email': email})


# Send OTP Email
def send_otp_email(recipient_email, otp):
    msg = Message('Your OTP Code for Secure ATM Access', 
                  sender=app.config['MAIL_USERNAME'], 
                  recipients=[recipient_email])
    
    msg.body = f"""
Dear Customer,

We have received a request to access your ATM account. For added security, please use the One-Time Password (OTP) provided below to complete the verification process.

Your OTP Code: {otp}

If you did not request this, please contact our support team immediately.

Thank you for choosing our secure ATM services.

Best regards,
Your Bank Support Team

"""
    mail.send(msg)
    return True

# Flask route to request OTP and send email
@app.route('/request_otp', methods=['POST'])
def request_otp():
    global otp_code, recipient_email
    recipient_email = request.json['email']
    otp_code = generate_otp()
    success = send_otp_email(recipient_email, otp_code)
    return jsonify({'success': success})

# Flask route to verify OTP
@app.route('/verify_otp', methods=['POST'])
def verify_otp():
    entered_otp = request.json['otp']
    if entered_otp == otp_code:
        account_number = session.get('account_number')  # Retrieve stored account number
        return jsonify({'success': True, 'redirect': url_for('home')})  # Redirect to home
    return jsonify({'success': False})

@app.route('/otp')
def otp():
    return render_template('otp.html')


@app.route('/home')
def home():
    account_number = session.get('account_number')  # Get the account number from session
    customer_info = None
    if account_number:  # If account number exists
        try:
            connection = get_db_connection()
            cursor = connection.cursor()
            query = "SELECT cus_name, cus_phoneno, cus_email, cus_accountno, cus_bankname FROM customer1 WHERE cus_accountno = %s"
            cursor.execute(query, (account_number,))
            customer_info = cursor.fetchone()  # Fetch the first matching record
            cursor.close()
            connection.close()
        except (Exception, Error) as error:
            print("Error fetching data from PostgreSQL", error)

    return render_template('home.html', customer=customer_info)


@app.route('/error')
def error():
    return render_template('error.html')





@app.route('/webcam')
def webcam():
    return render_template('webcam.html')


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)