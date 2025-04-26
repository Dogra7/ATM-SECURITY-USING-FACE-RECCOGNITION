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
from random import randint
from twilio.rest import Client
from datetime import datetime, timedelta


app = Flask(__name__)
app.secret_key = 'deep7'
app.config['UPLOAD_FOLDER'] = 'faces'
app.config['GRAY_FACE'] = 'face_data'
app.register_blueprint(app_atm)

# Initialize the global variable to store the latest RFID UID
latest_uid = None

otp_code = None
otp_generated_time = None 

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


# Twilio credentials
TWILIO_ACCOUNT_SID = 'AC43a485ebbc68f1351e195f5961d77678'
TWILIO_AUTH_TOKEN = 'f07662bc6dd419ab25c3108ccba282a6'
TWILIO_PHONE_NUMBER = '+19898004774'  # Your Twilio phone number

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
    face_file_path = os.path.join(app.config['GRAY_FACE'], face_file_name)
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
    return redirect(url_for('account'))

@app.route('/video_feed')
def video_feed():
    # Get the account holder's name from the session in the route
    account_name = session.get('account_name', None)

    def gen_frames(account_name):  # Pass account_name as an argument
        global recognized_face_name
        ip_camera_url = 'http://192.168.219.78:8080/video'  # Replace with your IP camera URL
        video_capture = cv2.VideoCapture(ip_camera_url)
        frame_skip = 2  # Process every third frame
        frame_count = 0 

        while True:
            ret, frame = video_capture.read()
            if not ret:
                break

            # Skip frames to reduce the processing load
            if frame_count % frame_skip == 0:
                small_frame = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)
                rgb_small_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)

                face_locations = face_recognition.face_locations(rgb_small_frame)
                face_encodings = face_recognition.face_encodings(rgb_small_frame, face_locations)

                face_names = []
                for face_encoding in face_encodings:
                    matches = face_recognition.compare_faces(known_face_encodings, face_encoding)
                    name = "Unknown"
                    face_distances = face_recognition.face_distance(known_face_encodings, face_encoding)
                    best_match_index = np.argmin(face_distances)
                    if matches[best_match_index]:
                        name = known_face_names[best_match_index]
                    face_names.append(name)
                    recognized_face_name = name  # Update the global recognized_face_name

                # Draw rectangles around faces
                for (top, right, bottom, left), name in zip(face_locations, face_names):
                    top *= 4
                    right *= 4
                    bottom *= 4
                    left *= 4
                    cv2.rectangle(frame, (left, top), (right, bottom), (0, 0, 255), 2)
                    cv2.rectangle(frame, (left, bottom - 35), (right, bottom), (0, 0, 255), cv2.FILLED)
                    font = cv2.FONT_HERSHEY_DUPLEX
                    cv2.putText(frame, name, (left + 6, bottom - 6), font, 1.0, (255, 255, 255), 1)
                       
                       
                if recognized_face_name == account_name:
                    print("Face matched with account:", account_name)  # Debugging log
                else:
                    print("Face not matched. Current recognized:", recognized_face_name)

            # Increment frame counter
            frame_count += 1

            ret, buffer = cv2.imencode('.jpg', frame)
            frame_bytes = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

    return Response(gen_frames(account_name), mimetype='multipart/x-mixed-replace; boundary=frame')



@app.route('/get_recognized_face_name')
def get_recognized_face_name():
    global recognized_face_name
    return jsonify({'recognized_face_name': recognized_face_name})

# @app.route('/account', methods=['GET', 'POST'])
# def account():
#     if request.method == 'POST':
#         account_number = request.form['account_number']
        
#         # Validate account number against the database
#         try:
#             connection = get_db_connection()
#             cursor = connection.cursor()
#             query = "SELECT cus_name FROM customer1 WHERE cus_accountno = %s"
#             cursor.execute(query, (account_number,))
#             customer = cursor.fetchone()  # Fetch the customer name associated with the account number
#             cursor.close()
#             connection.close()
            
#             if customer:
#                 session['account_name'] = customer[0]  # Store the customer name in the session
#                 session['account_number'] = account_number  # Store the account number in the session
#                 return redirect(url_for('webcam'))  # Redirect to face recognition page
#             else:
#                 return render_template('account.html', error="Invalid account number. Try again.")
#         except (Exception, Error) as error:
#             print("Error fetching data from PostgreSQL", error)
#             return render_template('account.html', error="Error occurred. Please try again.")
    
#     return render_template('account.html')


# Endpoint to update the latest UID (triggered by ESP32 or RFID scanner)
@app.route('/update_uid', methods=['POST'])
def update_uid():
    global fingerprint_uid
    global latest_uid
    fingerprint_uid = request.json.get('fingerprint_uid')  # UID sent as JSON
    print(f"Updated FUID: {fingerprint_uid}")
    latest_uid = request.json.get('rfid_uid')  # UID sent as JSON
    print(f"Updated UID: {latest_uid}")
    return jsonify({'status': 'success'})

# Endpoint to get the latest UID and corresponding account name
@app.route('/get_latest_fuid', methods=['GET'])
def get_latest_fuid():
    global fingerprint_uid
    if fingerprint_uid:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('SELECT cus_name FROM customer1 WHERE finger_uid = %s', (fingerprint_uid,))
        result = cur.fetchone()
        cur.close()
        conn.close()

        if result:
            account_name = result[0]
            session['account_name'] = account_name  # Store account name in session
            session['fingerprint_uid'] = fingerprint_uid        # Store UID in session
            fingerprint_uid = None  # Clear the UID after processing
            return jsonify({'fingerprint_uid': session['fingerprint_uid'], 'account_name': account_name, 'redirect': True})
        else:
            # latest_uid = None  # Clear the UID even if no match is found
            return jsonify({'fingerprint_uid': None, 'account_name': None, 'redirect': False})
    else:
        return jsonify({'fingerprint_uid': None, 'account_name': None, 'redirect': False})
    

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


# def generate_otp():
#     return str(random.randint(100000, 999999))

# @app.route('/get_email')
# def get_email():
#     account_number = session.get('account_number')  # Retrieve stored account number
#     email = None
#     if account_number:
#         try:
#             connection = get_db_connection()
#             cursor = connection.cursor()
#             query = "SELECT cus_email FROM customer1 WHERE cus_accountno = %s"
#             cursor.execute(query, (account_number,))
#             email_record = cursor.fetchone()
#             cursor.close()
#             connection.close()
#             if email_record:
#                 email = email_record[0]  # Get the email from the fetched record
#         except (Exception, Error) as error:
#             print("Error fetching email from PostgreSQL", error)
    
#     return jsonify({'email': email})


# # Send OTP Email
# def send_otp_email(recipient_email, otp):
#     msg = Message('Your OTP Code for Secure ATM Access', 
#                   sender=app.config['MAIL_USERNAME'], 
#                   recipients=[recipient_email])
    
#     msg.body = f"""
# Dear Customer,

# We have received a request to access your ATM account. For added security, please use the One-Time Password (OTP) provided below to complete the verification process.

# Your OTP Code: {otp}

# If you did not request this, please contact our support team immediately.

# Thank you for choosing our secure ATM services.

# Best regards,
# Your Bank Support Team

# """
#     mail.send(msg)
#     return True

# # Flask route to request OTP and send email
# @app.route('/request_otp', methods=['POST'])
# def request_otp():
#     global otp_code, recipient_email
#     recipient_email = request.json['email']
#     otp_code = generate_otp()
#     success = send_otp_email(recipient_email, otp_code)
#     return jsonify({'success': success})

# # Flask route to verify OTP
# @app.route('/verify_otp', methods=['POST'])
# def verify_otp():
#     entered_otp = request.json['otp']
#     if entered_otp == otp_code:
#         account_number = session.get('account_number')  # Retrieve stored account number
#         return jsonify({'success': True, 'redirect': url_for('home')})  # Redirect to home
#     return jsonify({'success': False})

# @app.route('/otp')
# def otp():
#     return render_template('otp.html')

# Fetch registered phone number from the database
@app.route('/get_phone')
def get_phone():
    account_number = session.get('account_number')
    phone_number = None
    if account_number:
        try:
            connection = get_db_connection()
            cursor = connection.cursor()
            query = "SELECT cus_phoneno FROM customer1 WHERE cus_accountno = %s"
            cursor.execute(query, (account_number,))
            phone_record = cursor.fetchone()
            cursor.close()
            connection.close()
            if phone_record:
                phone_number = phone_record[0]
        except Exception as error:
            print("Error fetching phone number from PostgreSQL", error)
    return jsonify({'phone': phone_number})

# Function to send OTP via Twilio
def send_otp_sms(recipient_phone, otp):
    try:
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        message = client.messages.create(
            body=f"Dear Customer, we have received a request to access your ATM account. For added security, please use the One-Time Password (OTP) provided below to complete the verification process. {otp}",
            from_=TWILIO_PHONE_NUMBER,
            to=recipient_phone
        )
        return True
    except Exception as e:
        print("Error sending OTP via SMS:", e)
        return False

# Flask route to request OTP and send SMS
@app.route('/request_otp', methods=['POST'])
def request_otp():
    global otp_code, recipient_phone, otp_timestamp
    recipient_phone = request.json['phone']
    otp_code = randint(100000, 999999)
    otp_timestamp = datetime.now()  # Record OTP creation time
    success = send_otp_sms(recipient_phone, otp_code)
    return jsonify({'success': success})

@app.route('/verify_otp', methods=['POST'])
def verify_otp():
    global otp_code, otp_timestamp

    entered_otp = request.json['otp']

    # Check if OTP exists and is not expired (e.g., 2 minutes)
    if not otp_code or not otp_timestamp:
        return jsonify({'success': False, 'error': 'OTP not requested'})

    if datetime.now() - otp_timestamp > timedelta(minutes=2):
        otp_code = None  # Clear expired OTP
        return jsonify({'success': False, 'error': 'OTP expired'})

    if entered_otp == str(otp_code):
        otp_code = None  # Clear OTP after successful verification
        return jsonify({'success': True, 'redirect': url_for('home')})

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

@app.route('/fingerprint')
def fingerprint():
    return render_template('fingerprint.html')

@app.route('/auth')
def auth():
    return render_template('auth.html')


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)