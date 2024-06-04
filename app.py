from flask import Flask, render_template, request, redirect, url_for, flash, session,send_file
from datetime import datetime
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import qrcode
import io
import base64
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import pygame
import time
import os

app = Flask(__name__)
app.secret_key = "bap_sem2_final_project"
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page', 'danger')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function
def get_db_connection():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn
with sqlite3.connect('database.db') as conn:
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Stock (
            id INTEGER PRIMARY KEY,
            batch_no TEXT,
            name TEXT,
            manuf TEXT,
            date_man TEXT,
            date_exp TEXT,
            quantity INTEGER,
            sell INTEGER,
            balance INTEGER,
            cost_unit REAL
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Dispose (
            id INTEGER PRIMARY KEY,
            batch_no TEXT,
            name TEXT,
            manuf TEXT,
            date_man TEXT,
            date_exp TEXT,
            quantity INTEGER
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Appointments (
            Token_no INTEGER PRIMARY KEY AUTOINCREMENT,
            Name TEXT NOT NULL,
            Gender TEXT NOT NULL,
            Age INTEGER NOT NULL,
            Weight INTEGER NOT NULL,
            Doctor_appointed TEXT NOT NULL,
            Contact_details INTEGER NOT NULL,
            Problem_Description TEXT NOT NULL,
            Date TEXT NOT NULL
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            typeof TEXT NOT NULL,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    ''')
    conn.commit()


@app.route('/')
def index():
    return render_template('index.html')

@app.route('/patient_login')
def patient_login():
    session['active'] = True
    session['typeof'] = 'patient'
    session['username'] = 'patient'
    return render_template('patient_home.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        role = request.form['roleSelect']
        username = request.form['username']
        password = request.form['password']
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM Users WHERE username = ?', (username,))
        user = cursor.fetchone()
        conn.close()
        
        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['active'] = True
            session['username'] = username
            session['typeof'] = user['typeof']
            if role == 'pharmacist' and user['typeof'] == 'pharmacist':
                flash('Login successful!', 'success')
                return redirect(url_for('pharmacy_home'))
            elif role == 'doctor' and user['typeof'] == 'doctor':
                flash('Login successful!', 'success')
                return redirect(url_for('doctor_static'))
            else:
                flash('Invalid role for credentials!', 'danger')
        else:
            flash('Invalid username or password!', 'danger')
        
        return redirect(url_for('login'))  # Always redirect after POST
    return render_template('login.html')
@app.route('/doctor_static')
@login_required
def doctor_static():
    username = session.get('username')
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM Users WHERE username = ?", (username,))
    doctor_details = cur.fetchone() 
    return render_template('doctor_static.html',doctor_name=doctor_details['name'])
@app.route('/doctor_home')
@login_required
def doctor_home():
    username = session.get('username')
    if not username:
        flash('Username not provided,\nlogging out!!!', 'danger')
        return redirect(url_for('logout'))
    
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM Users WHERE username = ?", (username,))
    doctor_details = cur.fetchone()
    
    cur.execute("SELECT * FROM Appointments WHERE doctor_appointed = ?", (doctor_details['name'],))
    appointments = cur.fetchall()
    conn.close()
    
    return render_template('doctor_home.html', doctor_details=doctor_details, appointments=appointments, doctor_name=doctor_details['name'])

@app.route('/pharmacy_home')
@login_required
def pharmacy_home():
    return render_template('pharmacy_home.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('username', None)
    session.pop('typeof', None)
    session.pop('active', None)
    flash('You have been logged out!', 'success')
    return redirect(url_for('index'))

@app.route('/register', methods=['POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        role = request.form['typeof']
        username = request.form['username']
        password = request.form['password']
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
        try:
            with sqlite3.connect('database.db') as conn:
                cursor = conn.cursor()
                cursor.execute('INSERT INTO Users (name, typeof, username, password) VALUES (?, ?, ?, ?)',
                               (name, role, username, hashed_password))
                conn.commit()
            flash('User registered successfully!', 'success')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('Username already exists!', 'danger')
    return render_template('register.html')

# Define route for about page
@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/doctors')
def doctors():
    return render_template('doctors.html')

# Define route for contact us page
EMAIL_USER = 'sendingemail@gmail.com'
EMAIL_PASSWORD = 'XXXX XXXX XXXX XXXX'#app password
RECIPIENT_EMAIL = 'receiveremail@gmail.com'

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        # Get form data
        name = request.form['name']
        email = request.form['email']
        subject = request.form['subject']
        message = request.form['message']
        
        # Create the email content
        msg = MIMEMultipart()
        msg['From'] = EMAIL_USER
        msg['To'] = RECIPIENT_EMAIL
        msg['Subject'] = subject
        
        body = f"Name: {name}\nEmail: {email}\n\nMessage:\n{message}"
        msg.attach(MIMEText(body, 'plain'))
        
        try:
            # Set up the SMTP server
            server = smtplib.SMTP('smtp.gmail.com', 587)
            server.starttls()
            server.login(EMAIL_USER, EMAIL_PASSWORD)
            text = msg.as_string()
            server.sendmail(EMAIL_USER, RECIPIENT_EMAIL, text)
            server.quit()
            return f'Thank you, {name}, for your message! We will get back to you soon.'
        except Exception as e:
            return str(e)
    
    return render_template('contact.html')
def play_sound():
    try:
        pygame.mixer.pre_init(frequency=44100, size=-16, channels=2, buffer=512)
        pygame.init()
        pygame.mixer.init()

        # Convert the URL to a local path
        success_path = os.path.join(app.root_path, 'static', 'success.mp3')
        note_path = os.path.join(app.root_path, 'static', 'note.mp3')

        success_sound = pygame.mixer.Sound(success_path)
        success_sound.play()
        time.sleep(2.5)
        note_sound = pygame.mixer.Sound(note_path)
        note_sound.play()
    except Exception as e:
        flash('Appointment Created successfully!', 'success')
    
BUILTIN_FONTS = ['Helvetica', 'Times-Roman', 'Courier']
IMAGE_PATH = 'static/logopdf.png'
@app.route('/create_appointment', methods=['GET', 'POST'])
def create_appointment():
    if request.method == 'POST':
        name = request.form['name']
        gender = request.form['gender']
        age = request.form['age']
        weight = request.form['weight']
        phone = request.form['phone']
        disease = request.form['disease']
        problem_description = request.form['description']

        # Doctor assignment logic   
        doctor = 'Unknown'
        degree = 'Unknown'
        if disease == 'normal_fever':
            disease = 'Normal Fever'
            doctor = 'Rishek'
            degree = 'MBBS'
        elif disease == 'skin_issue':
            disease = 'Skin Issues'
            doctor = 'Surya'
            degree = 'MD (Dermatology)'
        elif disease == 'emergency':
            disease = 'Emergency'
            doctor = 'Darshath'
            degree = 'MD (Emergency Medicine)'
        elif disease == 'eye_related':
            disease = 'Eye Problem'
            doctor = 'Amoolya'
            degree = 'MS (Ophthalmology)'
        elif disease == 'cancer':
            disease = 'Cancer'
            doctor = 'Tejas'
            degree = 'MD (Oncology)'
        else:
            doctor = 'Sanvi'
            degree = 'MBBS'

        # Server-side validation for word count
        word_count = len(problem_description.strip().split())
        if word_count > 50:
            flash(f'Problem Description should not exceed 50 words. Currently, it has {word_count} words.', 'danger')
            return redirect(url_for('create_appointment'))

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO Appointments (Name, Gender, Age, Weight, Contact_details, Doctor_appointed, Problem_Description, Date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (name, gender, age, weight, phone, doctor, problem_description, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
        token_no = cursor.lastrowid
        conn.commit()
        conn.close()

        # Generate PDF
        buffer = BytesIO()
        p = canvas.Canvas(buffer, pagesize=letter)
        
        # Draw the image
        p.drawImage(IMAGE_PATH, 45, 680, width=100, height=100)  # Adjust the coordinates and size as needed
        p.setFont("Helvetica-Bold", 35)
        p.drawString(190, 750, "Hospital  Care  Cloud ")
        p.setFont("Times-Roman", 17)
        p.drawString(150, 715,"Phone:+91 1234567890 / +91 9876543210 ")
        p.drawString(150, 690,"Email:carecloud@hospital.com / hospitalcarecloud@gmail.com ")
        p.line(45, 670, 545, 670)  # (x1, y1, x2, y2)
        # Set font styles
        p.setFont("Helvetica-Bold", 18)
        p.drawString(60, 640, f"Appointment Details")
        y=635
        p.setFont("Times-Roman", 14)
        p.drawString(60, y-25, "Token Number:")
        p.drawString(200, y-25,f"{token_no}")
        p.drawString(60, y-50, "Name:")
        p.drawString(200, y-50,f"{name}")
        p.drawString(60, y-75, "Gender:")
        p.drawString(200, y-75, f"{gender}")
        p.drawString(60, y-100, "Age:")
        p.drawString(200, y-100, f"{age}")
        p.drawString(60, y-125, "Weight:")
        p.drawString(200, y-125, f"{weight}")
        p.drawString(60, y-150, "Phone:")
        p.drawString(200, y-150, f"{phone}")
        p.drawString(60, y-175, "Disease:")
        p.drawString(200, y-175, f"{disease}")
        p.drawString(60, y-200, "Doctor:")
        p.drawString(200, y-200, f"Dr.{doctor}")
        p.setFont("Times-Roman", 12)
        p.drawString(280, y-200, f"{degree}")

        p.setFont("Helvetica", 14)
        p.drawString(60, y-225, "Problem Description:")
        p.drawString(200, y-225,f"{problem_description}")

        p.setFont("Times-Roman", 14)
        p.drawString(60, y-265, "Date and time:")
        p.drawString(200, y-265,f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        p.setFont("Courier-Bold", 16)
        p.drawString(60, y-310, f"Note : Carry the Receipt while you visit the Doctor.")
        p.line(60,50,175,50)  # (x1, y1, x2, y2)
        p.setFont("Helvetica-Bold", 14)
        p.drawString(60, 35, "Doctor Signature")
        p.showPage()
        p.save()

        buffer.seek(0)
        if buffer.getbuffer().nbytes > 0:
            play_sound()
            return send_file(buffer, as_attachment=True, download_name='appointment_details.pdf', mimetype='application/pdf')
        return render_template('create_appointment.html')

    return render_template('create_appointment.html')

@app.route('/delete_appointment/<int:token_no>', methods=['POST'])
def delete_appointment(token_no):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM Appointments WHERE Token_no=?", (token_no,))
    conn.commit()
    conn.close()
    flash('Appointment deleted successfully!', 'success')
    return redirect(url_for('doctor_home', username=session['username']))
################################################# pharmacy store management ################################################################
@app.route('/add_medicine', methods=['GET', 'POST'])
@login_required
def add_medicine():
    if request.method == 'POST':
        batch_no = request.form['batch_no']
        name = request.form['name']

        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM Stock WHERE name=? AND batch_no=?", (name, batch_no))
        existing_record = cur.fetchone()

        if existing_record:
            quantity = int(request.form['quantity'])
            new_quantity = existing_record['quantity'] + quantity
            new_balance = existing_record['balance'] + quantity

            cur.execute("""
                UPDATE Stock
                SET quantity=?, balance=?
                WHERE name=? AND batch_no=?
            """, (new_quantity, new_balance, name, batch_no))
        else:
            manuf = request.form['manuf']
            date_man = request.form['date_man']
            date_exp = request.form['date_exp']
            quantity = int(request.form['quantity'])
            cost_unit = float(request.form['cost_unit'])

            cur.execute("""
                INSERT INTO Stock (batch_no, name, manuf, date_man, date_exp, quantity, sell, balance, cost_unit)
                VALUES (?, ?, ?, ?, ?, ?, 0, ?, ?)
            """, (batch_no, name, manuf, date_man, date_exp, quantity, quantity, cost_unit))

        conn.commit()
        conn.close()

        flash('Medicine added successfully!', 'success')
        return redirect(url_for('add_medicine'))

    return render_template('add_medicine.html')
@app.route('/search/name', methods=('GET', 'POST'))
@login_required
def search_by_name():
    if request.method == 'POST':
        name = request.form['name']
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM Stock WHERE name=?", (name,))
        record = cur.fetchall()
        conn.close()
        return render_template('search_name.html', records=record)
    return render_template('search_name.html', records=None)
@app.route('/search/manufacturer', methods=('GET', 'POST'))
@login_required
def search_by_manufacturer():
    if request.method == 'POST':
        manufacturer = request.form['manufacturer']
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT name FROM Stock WHERE manuf=?", (manufacturer,))
        records = cur.fetchall()
        sorted_records = sorted(records, key=lambda x: x['name'])  # Sorting by 'name' field
        conn.close()
        return render_template('search_manufacturer.html', records=sorted_records)
    return render_template('search_manufacturer.html', records=None)
@app.route('/update/cost', methods=('GET', 'POST'))
@login_required
def update_cost():
    if request.method == 'POST':
        name = request.form['name']
        cost_unit = request.form['cost_unit']
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM Stock WHERE name=?", (name,))
        present=cur.fetchone()
        if present:
            cur.execute("UPDATE Stock SET cost_unit=? WHERE name=?", (cost_unit, name))
            flash(f'Cost updated for {name} to {cost_unit} Rs','success')
        else:
            flash(f'Medicine {name} Not Found in stock','danger')
        conn.commit()
        conn.close()
        return redirect(url_for('pharmacy_home'))
    return render_template('update_cost.html')
@app.route('/sell', methods=['GET', 'POST'])
def sell_medicine():
    qr_code = None
    cart = session.get('cart', [])
    return render_template('sell_medicine.html', qr_code=qr_code, cart=cart)
@app.route('/add_to_cart', methods=['POST'])
def add_to_cart():
    name = request.form['name']
    quantity = int(request.form['quantity'])

    # Check if the medicine is available in stock
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM Stock WHERE name=?", (name,))
    medicine = cur.fetchone()
    
    if medicine:
        available_quantity = medicine['balance']
        if available_quantity < quantity:
            flash(f'Not enough stock available for {name}. Available quantity: {available_quantity}')
        else:
            cart = session.get('cart', [])
            cart.append({'name': name, 'quantity': quantity})
            session['cart'] = cart
            flash(f'Added {quantity} units of {name} to the cart.')

            # Update the balance and sold quantities in the Stock table
            new_balance = available_quantity - quantity
            cur.execute("UPDATE Stock SET sell=sell+?, balance=? WHERE name=?", (quantity, new_balance, name))
            conn.commit()

    else:
        flash(f'Medicine {name} not found in stock.')

    conn.close()
    return redirect(url_for('sell_medicine'))
@app.route('/generate_bill', methods=['POST'])
def generate_bill():
    cart = session.get('cart', [])
    if not cart:
        flash('Cart is empty')
        return redirect(url_for('sell_medicine'))

    total_amount = 0.0
    for item in cart:
        name = item['name']
        quantity = item['quantity']
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT cost_unit FROM Stock WHERE name=?", (name,))
        medicine = cur.fetchone()
        if medicine:
            cost_unit = medicine['cost_unit']
            item_total = cost_unit * quantity
            total_amount += item_total
            item['item_total'] = item_total  # Store item total in cart item

        conn.close()

    # Replace with your UPI ID and amount calculation logic
    upi_id = "yourupiid@oksbi"
    amount = str(total_amount)
    payment_info = f"upi://pay?pa={upi_id}&pn=YourName&am={amount}&cu=INR&tn=Payment%20for%20goods"

    # Generate QR code
    img = qrcode.make(payment_info)
    buf = io.BytesIO()
    img.save(buf)
    buf.seek(0)
    
    qr_code = f"data:image/png;base64,{base64.b64encode(buf.getvalue()).decode('utf-8')}"
    session['cart'] = []  # Clear the cart after generating the bill

    return render_template('sell_medicine.html', qr_code=qr_code, cart=cart, total_amount=total_amount)
@app.route('/cancel_bill', methods=['POST'])
def cancel_bill():
    cart = session.get('cart', [])
    session['cart'] = []  # Clear the cart

    # Restore the stock balance and sold quantities for each item in the cart
    conn = get_db_connection()
    cur = conn.cursor()
    for item in cart:
        name = item['name']
        quantity = item['quantity']
        cur.execute("SELECT sell, balance FROM Stock WHERE name=?", (name,))
        medicine = cur.fetchone()
        if medicine:
            current_sold = medicine['sell']
            current_balance = medicine['balance']
            current_sold -= quantity
            current_balance += quantity
            cur.execute("UPDATE Stock SET sell=?, balance=? WHERE name=?", (current_sold, current_balance, name))
            conn.commit()
    conn.close()

    flash('Cancelled the entire bill.')
    return redirect(url_for('sell_medicine'))
@app.route('/cancel_item/<name>', methods=['POST'])
def cancel_item(name):
    cart = session.get('cart', [])
    for item in cart:
        if item['name'] == name:
            cart.remove(item)
            break
    session['cart'] = cart

    # Restore the stock balance and sold quantities for the canceled item
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT sell, balance FROM Stock WHERE name=?", (name,))
    medicine = cur.fetchone()
    if medicine:
        current_sold = medicine['sell']
        current_balance = medicine['balance']
        current_sold -= item['quantity']
        current_balance += item['quantity']
        cur.execute("UPDATE Stock SET sell=?, balance=? WHERE name=?", (current_sold, current_balance, name))
        conn.commit()
    conn.close()

    flash(f'Cancelled {name} from the cart.')
    return redirect(url_for('sell_medicine'))
    cart = session.get('cart', [])
    for item in cart:
        if item['name'] == name:
            cart.remove(item)
            break
    session['cart'] = cart

    # Restore the stock balance and sold quantities
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT sell, balance FROM Stock WHERE name=?", (name,))
    medicine = cur.fetchone()
    if medicine:
        current_sold = medicine['sell']
        current_balance = medicine['balance']
        for item in cart:
            if item['name'] == name:
                quantity = item['quantity']
                current_sold -= quantity
                current_balance += quantity
                break
        cur.execute("UPDATE Stock SET sell=?, balance=? WHERE name=?", (current_sold, current_balance, name))
        conn.commit()
    conn.close()

    flash(f'Cancelled {name} from the cart.')
    return redirect(url_for('sell_medicine'))
@app.route('/delete_medicine/<int:batch_no>', methods=('POST',))
def delete_medicine(batch_no):
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("DELETE FROM Stock WHERE batch_no = ?", (batch_no,))
    conn.commit()
    
    conn.close()
    
    return redirect(url_for('show_stock'))
@app.route('/stock', methods=('GET', 'POST'))
@login_required
def show_stock():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM Stock")
    records = cur.fetchall()
    conn.close()
    return render_template('show_stock.html', records=records)
@app.route('/dispose_records')
@login_required
def show_dispose():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM Dispose")
    records = cur.fetchall()
    conn.close()
    return render_template('show_dispose.html', records=records)
