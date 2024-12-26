from flask import Flask, render_template, request, redirect, url_for, jsonify
from flask_mail import Mail, Message
import random

app = Flask(__name__)

# Configure Flask-Mail
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USE_SSL'] = False
app.config['MAIL_USERNAME'] = 'deepmhatre007@gmail.com'
app.config['MAIL_PASSWORD'] = 'dkrnkwygcefhmaov'  # or your app password if 2FA is enabled

mail = Mail(app)

# Generate OTP
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

@app.route('/')
def index():
    return render_template('otp.html')

@app.route('/home')
def home():
    return render_template('home.html')

@app.route('/error')
def error():
    return render_template('otp_error.html')

if __name__ == '__main__':
    app.run(debug=True)