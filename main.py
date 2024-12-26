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
from atm import app_atm

app = Flask(__name__)
app.secret_key = 'deep7'
app.config['UPLOAD_FOLDER'] = 'faces'
app.register_blueprint(app_atm)

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
app.config['MAIL_PASSWORD'] = 'dkrnkwygcefhmaov'  # or your app password if 2FA is enabled

mail = Mail(app)


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

@app.route('/')
def index():
    return render_template('webcam.html')

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
                recognized_face_name = name  # Update recognized_face_name
            for (top, right, bottom, left), name in zip(face_locations, face_names):
                top *= 4
                right *= 4
                bottom *= 4
                left *= 4
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

def generate_otp():
    return str(random.randint(100000, 999999))
# Send OTP Email
def send_otp_email(recipient_email, otp):
    msg = Message('Your OTP Code', sender=app.config['MAIL_USERNAME'], recipients=[recipient_email])
    msg.body = f'Your OTP code is {otp}.'
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
        return jsonify({'success': True, 'redirect': url_for('home')})
    return jsonify({'success': False})

@app.route('/otp')
def otp():
    return render_template('otp.html')

@app.route('/home')
def home():
    return render_template('home.html')

@app.route('/error')
def error():
    return render_template('error.html')

if __name__ == '__main__':
    app.run(debug=True)