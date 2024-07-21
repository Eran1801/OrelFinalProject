from flask import Flask, request, render_template, redirect, url_for, g, session, jsonify, flash
import sqlite3
import datetime
import random
from datetime import datetime
import sys
import re
import os

from utils import check_valid_password, send_email, update_table_name

sys.stdout = open('stdout.log', 'w')

DATABASE = os.path.join('Tables', 'Emergenshe.db')

app = Flask(__name__)
app.config['DATABASE'] = DATABASE
app.config['SECRET_KEY'] = 'super_secret_key'
app.config['DEBUG'] = True


def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(app.config['DATABASE'])
    return db


@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()


@app.route('/')
def first_page():
    print(f"Returning to first page, clearing session for user: {session.get('email')}")
    session.clear()  # Clear all session data when returning to first page
    print("Session cleared")
    return render_template('first_page.html')


@app.route('/logout')
def logout():
    print(f"Logging out user: {session.get('email')}")
    session.clear()  # Clear all session data
    print("Session cleared")
    return redirect(url_for('user_login'))


@app.route('/get_user_type')
def get_user_type():
    email = session.get('email').lower()
    if email:
        con = get_db()
        cursor = con.cursor()
        cursor.execute("SELECT UserType FROM login_type WHERE Email=?", (email,))
        user_type = cursor.fetchone()
        if user_type:
            return jsonify({'user_type': user_type[0]})
    return jsonify({'error': 'User type not found'}), 404


@app.route('/user_sign_up', methods=['GET', 'POST'])
def user_sign_up():
    if request.method == 'POST':
        try:
            first_name = request.form.get('first_name')
            last_name = request.form.get('last_name')
            phone_number = request.form.get('phone_number')
            email = request.form.get('email').lower()
            password = request.form.get('password')
            confirm_password = request.form.get('confirm_password')

            if password != confirm_password:
                return "Passwords do not match.", 400

            if check_valid_password(password):
                return "Password must be at least 6 characters long and contain at least one uppercase letter, one lowercase letter, and one number.", 400

            con = get_db()
            cursor = con.cursor()

            cursor.execute("SELECT COUNT(*) FROM Users WHERE phone_number = ?", (phone_number,))
            phone_exists = cursor.fetchone()[0] > 0

            cursor.execute("SELECT COUNT(*) FROM login_type WHERE Email = ?", (email,))
            email_exists = cursor.fetchone()[0] > 0

            if email_exists or phone_exists:
                error_message = "החשבון קיים, אנא התחבר/י"
                cursor.close()
                con.close()
                return render_template('user_sign_up.html', error_message=error_message)

            new_id = random.randint(900000, 1100000)

            cursor.execute("SELECT COUNT(*) FROM login_type WHERE ID = ?", (new_id,))
            id_exists = cursor.fetchone()[0] > 0

            while id_exists:
                new_id = random.randint(900000, 1100000)
                cursor.execute("SELECT COUNT(*) FROM login_type WHERE ID = ?", (new_id,))
                id_exists = cursor.fetchone()[0] > 0

            sql_user = "INSERT INTO Users (ID, first_name, last_name, phone_number, email, password) VALUES (?, ?, ?, ?, ?, ?)"
            cursor.execute(sql_user, (new_id, first_name, last_name, phone_number, email, password))

            sql_login_type = "INSERT INTO login_type (ID, Email, UserType) VALUES (?, ?, ?)"
            cursor.execute(sql_login_type, (new_id, email, 'User'))

            con.commit()

            session['email'] = email
            session['user_id'] = new_id
            session['user_type'] = 'User'

            cursor.close()
            con.close()

            return redirect(url_for('main_user_page'))

        except Exception as e:
            print("An error occurred:", e)
            return f"An error occurred while processing your request. Please try again later. error : {e} database - {DATABASE}", 500

    return render_template('user_sign_up.html')


@app.route('/set_availability', methods=['POST'])
def set_availability():
    try:
        data = request.json
        available = data.get('available')
        volunteer_id = data.get('volunteer_id')
        session[f"volunteer_{volunteer_id}_is_timing"] = available
        return jsonify({'message': 'Availability status updated successfully.'})
    except Exception as e:
        print(f"Error in set_availability: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/start_call', methods=['POST'])
def start_call():
    try:
        email = request.json.get('email').lower()
        print(f"Starting call for email: {email}")
        db = get_db()
        cursor = db.cursor()

        cursor.execute("SELECT ID, first_name FROM Users WHERE email = ?", (email,))
        user = cursor.fetchone()
        if not user:
            print("User not found")
            return jsonify({'success': False, 'error': 'User not found'})

        user_id, user_first_name = user

        cursor.execute("SELECT ID, first_name FROM Volunteers_list")
        volunteers = cursor.fetchall()

        if not volunteers:
            print("No available volunteers")
            return jsonify({'success': False, 'error': 'No available volunteers'})

        volunteer = next((v for v in volunteers if session.get(f"volunteer_{v[0]}_is_timing")), None)
        if not volunteer:
            print("No available volunteers with the timer running")
            return jsonify({'success': False, 'error': 'No available volunteers with the timer running'})

        volunteer_id, volunteer_name = volunteer

        session[f"volunteer_{volunteer_id}_current_call"] = user_id
        session[f"user_{user_id}_volunteer"] = volunteer_id
        session['current_user'] = {'id': user_id, 'name': user_first_name}
        session['current_volunteer'] = {'id': volunteer_id, 'name': volunteer_name}
        session['call_active'] = True  # נוסיף את הנתון הזה למעקב אחר השיחה הפעילה
        session['user_first_name'] = user_first_name  # Ensure user_first_name is stored in session

        start_time = datetime.now()
        cursor.execute(
            "INSERT INTO Calls (UserID, VolunteerID, Start_Time, Call_Status) VALUES (?, ?, ?, ?)",
            (user_id, volunteer_id, start_time, 'waiting')
        )
        db.commit()

        print(f"Call started: User ID: {user_id}, Volunteer ID: {volunteer_id}")
        print(f"Session data after starting call: {session}")
        return jsonify({'success': True, 'volunteer_name': volunteer_name})

    except Exception as e:
        print(f"Error in start_call: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/hangup_call/<int:call_id>', methods=['POST'])
def hangup_call(call_id):
    email = request.json.get('email').lower()
    db = get_db()
    cursor = db.cursor()

    cursor.execute("UPDATE Calls SET Call_Status = 'ended' WHERE ID = ?", (call_id,))
    db.commit()

    cursor.execute("SELECT UserID, VolunteerID FROM Calls WHERE ID = ?", (call_id,))
    call = cursor.fetchone()
    if call:
        user_id, volunteer_id = call
        if email == session['email']:
            session.pop('current_call', None)
            session.pop('current_user', None)
            session.pop('current_volunteer', None)
            session.pop('call_id', None)

    return jsonify({'success': True})


@app.route('/call_rate_user/<int:call_id>', methods=['GET', 'POST'])
def call_rate_user(call_id):
    if request.method == 'POST':
        rating = request.form['rating']

        db = get_db()
        cursor = db.cursor()
        cursor.execute("INSERT INTO calls (ID, User_Call_Rating) VALUES (?, ?)",
                       (call_id, rating))
        db.commit()

        return redirect(url_for('main_user_page'))

    return render_template('call_rate_user.html', call_id=call_id)


@app.route('/call_rate_volunteer/<int:call_id>', methods=['GET', 'POST'])
def call_rate_volunteer(call_id):
    if request.method == ('POST'):
        rating = request.form['rating']
        emergency = request.form['emergency']
        notes = request.form['notes']
        db = get_db()
        cursor = db.cursor()
        cursor.execute("INSERT INTO calls (ID, Volunteer_Call_Rating, Call_Type, Notes) VALUES (?, ?, ?, ?)",
                       (call_id, rating, emergency, notes))
        db.commit()

        return redirect(url_for('main_volunteer_page'))

    return render_template('call_rate_volunteer.html', call_id=call_id)


@app.route('/get_call_status', methods=['POST'])
def get_call_status():
    email = request.json.get('email').lower()
    print(f"Checking call status for email: {email}")  # הוספת לוג
    db = get_db()
    cursor = db.cursor()

    # Check if the email belongs to a user
    cursor.execute("SELECT ID FROM Users WHERE email = ?", (email,))
    user = cursor.fetchone()
    if user:
        user_id = user[0]
        cursor.execute("""
            SELECT Calls.ID, Calls.Call_Status, Volunteers_list.first_name as volunteer_name
            FROM Calls
            JOIN Volunteers_list ON Calls.VolunteerID = Volunteers_list.ID
            WHERE Calls.UserID = ? AND Calls.Call_Status = 'waiting'
            ORDER BY Calls.Start_Time DESC LIMIT 1
        """, (user_id,))
        call = cursor.fetchone()
        if call:
            call_id, call_status, other_party_name = call
            print(f"User call status: {call_status}, Volunteer: {other_party_name}")  # הוספת לוג
            return jsonify({'success': True, 'status': call_status, 'call_id': call_id, 'other_party_name': other_party_name})

    # Check if the email belongs to a volunteer
    cursor.execute("SELECT ID FROM Volunteers_list WHERE email = ?", (email,))
    volunteer = cursor.fetchone()
    if volunteer:
        volunteer_id = volunteer[0]
        cursor.execute("""
            SELECT Calls.ID, Calls.Call_Status, Users.first_name as user_name
            FROM Calls
            JOIN Users ON Calls.UserID = Users.ID
            WHERE Calls.VolunteerID = ? AND Calls.Call_Status = 'waiting'
            ORDER BY Calls.Start_Time DESC LIMIT 1
        """, (volunteer_id,))
        call = cursor.fetchone()
        if call:
            call_id, call_status, other_party_name = call
            print(f"Volunteer call status: {call_status}, User: {other_party_name}")  # הוספת לוג
            return jsonify({'success': True, 'status': call_status, 'call_id': call_id, 'other_party_name': other_party_name})

    print("No ongoing call found")  # הוספת לוג
    return jsonify({'success': False, 'error': 'No ongoing call found'})



@app.route('/answer_call', methods=['POST'])
def answer_call():
    volunteer_id = session.get('user_id')
    db = get_db()
    cursor = db.cursor()
    cursor.execute("""
    UPDATE Calls
    SET Call_Status = 'ongoing'
    WHERE VolunteerID = ? AND Call_Status = 'waiting'
    """, (volunteer_id,))
    db.commit()
    return jsonify({'success': True})


@app.route('/check_call_status', methods=['POST'])
def check_call_status():
    email = request.json.get('email').lower()
    db = get_db()
    cursor = db.cursor()

    cursor.execute("""
        SELECT c.Call_Status, u.first_name
        FROM Calls c
        JOIN Users u ON c.UserID = u.ID
        WHERE (c.UserID = (SELECT ID FROM Users WHERE email = ?)
        OR c.VolunteerID = (SELECT ID FROM Volunteers_list WHERE email = ?))
        AND c.Call_Status = 'ongoing'
    """, (email, email))

    call = cursor.fetchone()

    if call:
        return jsonify({'status': 'ongoing', 'user_first_name': call[1]})
    else:
        return jsonify({'status': 'ended'})


def get_assigned_user_name(volunteer_id):
    user_id = session.get(f"volunteer_{volunteer_id}_current_call")
    if user_id:
        db = get_db()
        cursor = db.cursor()
        cursor.execute("SELECT first_name FROM Users WHERE ID = ?", (user_id,))
        user = cursor.fetchone()
        if user:
            return user[0]
    return None


@app.route('/accept_call', methods=['POST'])
def accept_call():
    try:
        email = request.json.get('email').lower()
        print(f"Accepting call for email: {email}")  # לוג התחלה
        print(f"Session data on accept_call: {session}")  # לוג נתוני סשן

        db = get_db()
        cursor = db.cursor()

        volunteer_id = session.get('volunteer_id')
        volunteer_name = session.get('first_name')

        if not volunteer_id:
            print("Volunteer not found in session")
            return jsonify({'success': False, 'error': 'Volunteer not found in session'})

        print(f"Volunteer ID: {volunteer_id}, Volunteer Name: {volunteer_name}")  # לוג פרטי מתנדב

        cursor.execute("""
            SELECT ID
            FROM Calls
            WHERE VolunteerID = ? AND Call_Status = 'waiting'
            ORDER BY Start_Time DESC LIMIT 1
        """, (volunteer_id,))
        call = cursor.fetchone()
        if not call:
            print("No waiting call found")
            return jsonify({'success': False, 'error': 'No waiting call found'})

        call_id = call[0]
        cursor.execute("UPDATE Calls SET Call_Status = 'accepted' WHERE ID = ?", (call_id,))
        db.commit()

        session['call_id'] = call_id

        print(f"Call accepted with Call ID: {call_id}")  # לוג קבלת שיחה

        return jsonify({'success': True, 'call_id': call_id})
    except Exception as e:
        print(f"Error accepting call: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500




@app.route('/reject_call', methods=['POST'])
def reject_call():
    volunteer_id = session.get('current_volunteer', {}).get('id')
    if volunteer_id:
        session.pop(f"volunteer_{volunteer_id}_current_call", None)
        session.pop('current_user', None)
        session.pop('current_volunteer', None)
        session.pop('call_id', None)
        return jsonify({'success': True})
    return jsonify({'success': False, 'error': 'No call to reject'})


@app.route('/end_call', methods=['POST'])
def end_call():
    user_id = session.get('current_user', {}).get('id')
    volunteer_id = session.get('current_volunteer', {}).get('id')
    if user_id and volunteer_id:
        session.pop(f"volunteer_{volunteer_id}_current_call", None)
        session.pop('current_user', None)
        session.pop('current_volunteer', None)
        return jsonify({'success': True})
    return jsonify({'success': False, 'error': 'No call to end'})


@app.route('/update_volunteer_status', methods=['POST'])
def update_volunteer_status():
    try:
        is_timing = request.json.get('is_timing')
        volunteer_id = session.get('user_id')
        session[f"volunteer_{volunteer_id}_is_timing"] = is_timing
        return jsonify({'success': True})
    except Exception as e:
        print(f"Error in update_volunteer_status: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/check_for_incoming_call', methods=['POST'])
def check_for_incoming_call():
    try:
        volunteer_id = request.json.get('volunteer_id')
        if not volunteer_id:
            return jsonify({'incoming_call': False})
        
        db = get_db()
        cursor = db.cursor()
        
        # Check if the volunteer is available (is timing)
        if not session.get(f"volunteer_{volunteer_id}_is_timing"):
            return jsonify({'incoming_call': False})
        
        cursor.execute("""
            SELECT c.ID, u.first_name
            FROM Calls c
            JOIN Users u ON c.UserID = u.ID
            WHERE c.Call_Status = 'waiting' AND u.ID = ?
            ORDER BY c.Start_Time ASC
            LIMIT 1
        """, (session.get('current_user')['id'],))
        waiting_call = cursor.fetchone()

        if waiting_call:
            call_id, user_first_name = waiting_call
            return jsonify({'incoming_call': True, 'call_id': call_id, 'user_first_name': user_first_name})
        else:
            return jsonify({'incoming_call': False})
    except Exception as e:
        print(f"Error in check_for_incoming_call: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/trigger_volunteer_incoming_call', methods=['POST'])
def trigger_volunteer_incoming_call():
    try:
        call_id = request.json.get('call_id')
        volunteer_id = session.get('current_volunteer')['id']

        if not call_id or not volunteer_id:
            return jsonify({'success': False, 'error': 'Missing call ID or volunteer ID'})

        session[f"volunteer_{volunteer_id}_incoming_call"] = call_id

        return jsonify({'success': True})
    except Exception as e:
        print(f"Error in trigger_volunteer_incoming_call: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/call_ongoing_user')
def call_ongoing_user():
    email = session.get('email').lower()
    user_id = session.get('user_id')
    
    if not email or not user_id:
        return redirect(url_for('user_login'))
    
    con = get_db()
    cursor = con.cursor()
    
    cursor.execute("""
        SELECT c.ID, v.first_name
        FROM Calls c
        JOIN Volunteers_list v ON c.VolunteerID = v.ID
        WHERE c.UserID = ? AND c.Call_Status = 'waiting'
        ORDER BY c.Start_Time DESC
        LIMIT 1
    """, (user_id,))
    call = cursor.fetchone()
    
    if not call:
        return redirect(url_for('main_user_page'))
    
    call_id, volunteer_first_name = call

    # Update the call status to notify that the user is waiting for a volunteer
    cursor.execute("UPDATE Calls SET Call_Status = 'waiting' WHERE ID = ?", (call_id,))
    con.commit()

    session['call_id'] = call_id

    # Debug print for session data
    print("Session data:", session)

    # Ensure user_first_name is in session
    user_first_name = session.get('user_first_name')
    if not user_first_name:
        # Fetch user first name from database if not in session
        cursor.execute("SELECT first_name FROM Users WHERE ID = ?", (user_id,))
        user_first_name = cursor.fetchone()
        if user_first_name:
            user_first_name = user_first_name[0]
            session['user_first_name'] = user_first_name
        else:
            return redirect(url_for('user_login'))
    
    return render_template('call_ongoing_user.html', user_first_name=user_first_name, volunteer_first_name=volunteer_first_name)


@app.route('/leave_call_ongoing_user')
def leave_call_ongoing_user():
    user_id = session.get('user_id')
    session.pop(f"user_{user_id}_on_call_page", None)  # Remove the flag when user leaves the page
    return redirect(url_for('main_user_page'))


def get_assigned_volunteer_name(user_id):
    db = get_db()
    cursor = db.cursor()
    volunteer_id = cursor.execute("SELECT VolunteerID FROM Calls WHERE UserID = ? AND Call_Status = 'ongoing'",
                                  (user_id,)).fetchone()
    if volunteer_id:
        volunteer = cursor.execute("SELECT first_name FROM Volunteers_list WHERE ID = ?", (volunteer_id[0],)).fetchone()
        if volunteer:
            return volunteer[0]
    return None


@app.route('/call_ongoing_volunteer')
def call_ongoing_volunteer():
    volunteer_first_name = session.get('first_name')
    volunteer_id = session.get('user_id')
    user_first_name = get_assigned_user_name(volunteer_id)
    return render_template('call_ongoing_volunteer.html', user_first_name=user_first_name,
                           volunteer_first_name=volunteer_first_name)


@app.route('/volunteer_sign_up', methods=['GET', 'POST'])
def volunteer_sign_up():
    if request.method == 'POST':
        try:
            first_name = request.form.get('first_name')
            last_name = request.form.get('last_name')
            phone_number = request.form.get('phone_number')
            email = request.form.get('email').lower()
            password = request.form.get('password')
            confirm_password = request.form.get('confirm_password')

            if password != confirm_password:
                return "Passwords do not match.", 400
            if len(password) < 6 or not any(c.isupper() for c in password) or not any(
                    c.islower() for c in password) or not any(c.isdigit() for c in password):
                return "Password must be at least 6 characters long and contain at least one uppercase letter, one lowercase letter, and one number.", 400

            conn = get_db()
            cursor = conn.cursor()

            cursor.execute("SELECT COUNT(*) FROM login_type WHERE Email = ?", (email,))
            email_exists = cursor.fetchone()[0] > 0

            cursor.execute("SELECT COUNT(*) FROM Volunteers_list WHERE phone_number = ?", (phone_number,))
            phone_exists = cursor.fetchone()[0] > 0

            if email_exists or phone_exists:
                error_message = "החשבון קיים, אנא התחבר/י"
                cursor.close()
                conn.close()
                return render_template('volunteer_sign_up.html', error_message=error_message)

            volunteer_id = random.randint(70000, 900000)

            cursor.execute("SELECT COUNT(*) FROM login_type WHERE ID = ?", (volunteer_id,))
            id_exists = cursor.fetchone()[0] > 0

            while id_exists:
                volunteer_id = random.randint(70000, 900000)
                cursor.execute("SELECT COUNT(*) FROM login_type WHERE ID = ?", (volunteer_id,))
                id_exists = cursor.fetchone()[0] > 0

            registration_date = datetime.now().strftime("%Y-%m-%d")
            test_status = "UNCHECKED"

            sql_Volunteers_list = "INSERT INTO Volunteers_list (ID, first_name, last_name, phone_number, email, password, registration_date, test_status) VALUES (?, ?, ?, ?, ?, ?, ?, ?)"
            cursor.execute(sql_Volunteers_list, (
                volunteer_id, first_name, last_name, phone_number, email, password, registration_date, test_status))
            conn.commit()

            sql_login_type = "INSERT INTO login_type (ID, Email, UserType) VALUES (?, ?, ?)"
            cursor.execute(sql_login_type, (volunteer_id, email, 'Volunteer'))
            conn.commit()

            session['email'] = email
            session['user_id'] = volunteer_id
            session['user_type'] = 'Volunteer'

            cursor.close()

            return redirect(url_for('main_volunteer_page'))

        except Exception as e:
            return f"An error occurred: {str(e)}"

    else:
        return render_template('volunteer_sign_up.html')


@app.route('/user_login', methods=['GET', 'POST'])
def user_login():
    if request.method == 'POST':
        email = request.form.get('email').lower()
        password = request.form.get('password')
        
        con = get_db()
        cursor = con.cursor()
        
        print(f"Trying to login user with email: {email}")
        
        user_data = cursor.execute("SELECT Email, UserType FROM login_type WHERE Email=?", (email,)).fetchone()
        if user_data:
            user_type = user_data[1]
            print(f"User type found: {user_type}")
            
            if user_type == 'User':
                user_info = cursor.execute(
                    "SELECT password, ID, first_name, written_code, spoken_code FROM Users WHERE email=?",
                    (email,)).fetchone()
                if user_info and user_info[0] == password:
                    session['email'] = email
                    session['user_id'] = user_info[1]
                    session['first_name'] = user_info[2]
                    print(f"User {email} logged in successfully with user_id {session['user_id']}")
                    return redirect(url_for('main_user_page'))

            elif user_type == 'Volunteer':
                volunteer_info = cursor.execute("SELECT password, ID, first_name FROM Volunteers_list WHERE email=?", (email,)).fetchone()
                if volunteer_info and volunteer_info[0] == password:
                    session['email'] = email
                    session['user_id'] = volunteer_info[1]
                    session['first_name'] = volunteer_info[2]
                    print(f"Volunteer {email} logged in successfully with user_id {session['user_id']}")
                    return redirect(url_for('main_volunteer_page'))

            elif user_type == 'Contact':
                contact_info = cursor.execute(
                    "SELECT ID, UserID, First_Name, Last_Name, Phone_Number, Email, password FROM contact_list WHERE Email=?",
                    (email,)).fetchone()
                if contact_info and contact_info[6] == password:
                    session['email'] = email
                    session['user_id'] = contact_info[0]
                    session['first_name'] = contact_info[2]
                    print(f"Contact {email} logged in successfully with user_id {session['user_id']}")
                    return redirect(url_for('main_contact'))

            elif user_type == 'Association Manager':
                manager_info = cursor.execute("SELECT password, ID, first_name FROM Manager WHERE email=?", (email,)).fetchone()
                if manager_info and manager_info[0] == password:
                    session['email'] = email
                    session['user_id'] = manager_info[1]
                    session['first_name'] = manager_info[2]
                    print(f"Association Manager {email} logged in successfully with user_id {session['user_id']}")
                    return redirect(url_for('main_association'))

        print(f"Login failed for user with email: {email}")
        return render_template('login_failed.html')

    return render_template('user_login.html')


@app.route('/protected_route')
def protected_route():
    if 'email' in session:
        print(f"Session data: {session}")
        return "Welcome to the protected route!"
    else:
        return redirect(url_for('user_login'))


@app.route('/create_contact', methods=['GET', 'POST'])
def create_contact():
    if 'email' not in session:
        return redirect(url_for('user_login'))

    user_email = session['email'].lower()

    con = get_db()
    cursor = con.cursor()
    cursor.execute("SELECT ID, First_Name FROM Users WHERE Email = ?", (user_email,))
    user_data = cursor.fetchone()
    user_id = user_data[0]
    user_first_name = user_data[1]

    if request.method == 'POST':
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        phone_number = request.form.get('phone_number')
        email = request.form.get('email').lower()

        try:
            cursor.execute("SELECT ID FROM contact_list WHERE Email=? AND is_active != 'deleted'", (email,))
            existing_contact = cursor.fetchone()

            if existing_contact:
                error_message = "המייל שהוזן כבר קיים וקשור לאיש קשר קיים"
                cursor.close()
                con.close()
                return render_template('create_contact.html', user_first_name=user_first_name,
                                       error_message=error_message)

            cursor.execute("SELECT ID FROM contact_list WHERE UserID=? AND is_active IN ('active', 'inactive')",
                           (user_id,))
            existing_contact = cursor.fetchone()

            if existing_contact:
                error_message = "לא ניתן להוסיף יותר מאיש קשר אחד"
                cursor.close()
                con.close()
                return render_template('create_contact.html', user_first_name=user_first_name,
                                       error_message=error_message)

            contact_id = random.randint(20000, 40000)
            password = None
            is_active = "inactive"

            sql_insert_contact = """
                INSERT INTO contact_list (ID, UserID, First_Name, Last_Name, Phone_Number, Email, password, is_active)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """
            cursor.execute(sql_insert_contact,
                           (contact_id, user_id, first_name, last_name, phone_number, email, password, is_active))
            con.commit()

            sql_insert_login = """
                INSERT INTO login_type (ID, Email, UserType) VALUES (?, ?, ?)
            """
            cursor.execute(sql_insert_login, (contact_id, email, 'Contact'))
            con.commit()

            email_message = f'Hello {first_name} {last_name} {user_first_name} want to add you as her contact. Please register in this link to the service : http://127.0.0.1:5000/contact_sign_up'
            email_subject = "EmergeShe"
            send_email(email_subject, email_message, email)

            cursor.close()

            flash("איש הקשר נוסף בהצלחה", "success")
            return redirect(url_for('users_contact'))

        except Exception as e:
            print("An error occurred while creating contact:", e)
            flash("אירעה שגיאה בעת יצירת איש הקשר. נסה שוב מאוחר יותר.", "error")
            return redirect(url_for('create_contact'))

    return render_template('create_contact.html', user_first_name=user_first_name)


@app.route('/check_duplicate_email', methods=['POST'])
def check_duplicate_email():
    email = request.json.get('email').lower()

    con = get_db()
    cursor = con.cursor()
    cursor.execute("SELECT is_active FROM contact_list WHERE Email = ?", (email,))
    result = cursor.fetchone()
    cursor.close()

    if result:
        status = result[0]
        if status in ['active', 'inactive']:
            return jsonify({'exists': True, 'status': status})

    return jsonify({'exists': False})


@app.route('/contact_sign_up', methods=['GET', 'POST'])
def contact_sign_up():
    if request.method == 'POST':
        try:
            First_Name = request.form.get('First_Name')
            Last_Name = request.form.get('Last_Name')
            Phone_Number = request.form.get('Phone_Number')
            Email = request.form.get('Email')

            Password = request.form.get('Password')
            confirm_password = request.form.get('Confirm_Password')

            print(f"Form data received: First_Name={First_Name}, Last_Name={Last_Name}, "
                  f"Phone_Number={Phone_Number}, Email={Email}, Password={Password}, Confirm_Password={confirm_password}")

            if Password != confirm_password:
                flash("Passwords do not match.", "error")
                return redirect(url_for('contact_sign_up'))
            if len(Password) < 6 or not any(c.isupper() for c in Password) or not any(
                    c.islower() for c in Password) or not any(c.isdigit() for c in Password):
                flash(
                    "Password must be at least 6 characters long and contain at least one uppercase letter, one lowercase letter, and one number.",
                    "error")
                return redirect(url_for('contact_sign_up'))

            if '@' not in Email:
                flash("כתובת המייל חייבת לכלול '@'", "error")
                return redirect(url_for('contact_sign_up'))

            con = get_db()
            cursor = con.cursor()

            cursor.execute("SELECT ID, UserID FROM contact_list WHERE Email=?", (Email.lower(),))
            existing_contact = cursor.fetchone()

            if existing_contact:
                existing_id, existing_user_id = existing_contact

                cursor.execute(
                    "UPDATE contact_list SET First_Name=?, Last_Name=?, Phone_Number=?, Password=?, is_active=? WHERE Email=?",
                    (First_Name, Last_Name, Phone_Number, Password, 'active', Email))
                con.commit()
                print(
                    f"Updated contact: ID={existing_id}, UserID={existing_user_id}, First_Name={First_Name}, Last_Name={Last_Name}, "
                    f"Phone_Number={Phone_Number}, Email={Email}, Password={Password}")

                cursor.close()
                return redirect(url_for('user_login'))

            else:
                cursor.close()
                con.close()

                flash("The email does not exist in the contact list. Please check and try again.", "error")

                return render_template('contact_sign_up.html',
                                       error_message="The email does not exist in the contact list. Please check and try again.")

        except Exception as e:
            print("An error occurred while updating/inserting contact:", e)
            flash("An error occurred while updating/inserting the contact. Please try again later.", "error")
            return redirect(url_for('contact_sign_up'))

    return render_template('contact_sign_up.html')


@app.route('/show_contact_profile/<int:contact_id>')
def show_contact_profile(contact_id):
    try:
        con = get_db()
        cursor = con.cursor()
        contact = cursor.execute("SELECT * FROM contact_list WHERE ID=?", (contact_id,)).fetchone()
        cursor.close()
        if contact:
            return render_template('contact_profile.html', contact=contact)
        else:
            flash("Contact not found.", "error")
            return redirect(url_for('contact_sign_up'))
    except Exception as e:
        print("An error occurred while fetching contact profile:", e)
        flash("An error occurred while fetching contact profile. Please try again later.", "error")
        return redirect(url_for('contact_sign_up'))


@app.route('/main_contact')
def main_contact():
    if 'email' in session:
        email = session['email'].lower()
        print("Email from session:", email)

        con = get_db()
        cursor = con.cursor()
        cursor.execute("SELECT First_Name FROM contact_list WHERE email=?", (email,))
        contact_data = cursor.fetchone()

        if contact_data:
            contact_first_name = contact_data[0]
            return render_template('main_contact.html', contact_info={'first_name': contact_first_name})
        else:
            flash("The email does not exist in the contact list. Please check and try again.", "error")
            return redirect(url_for('user_login'))
    else:
        return redirect(url_for('user_login'))


@app.route('/contact_user_list')
def contact_user_list():
    return render_template('contact_user_list.html')


@app.route('/terms_of_use')
def terms_of_use():
    return render_template('terms_of_use.html')


@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    con = get_db()
    cursor = con.cursor()

    if request.method == 'POST':
        email = request.form.get('email').lower()

        cursor.execute("SELECT UserType FROM login_type WHERE Email = ?", (email,))
        user_data = cursor.fetchone()

        cursor.close()
        con.close()

        if user_data:
            source_table = update_table_name(user_data[0])
            reset_link = url_for('change_password_forgot_password', email=email, source_table=source_table,
                                 _external=True)
            email_subject = 'Update Password'
            email_message = f'To update your password, please click the following link: {reset_link}'
            send_email(email_subject, email_message, email)

            success_message = f'A reset password email has been sent. Found in {source_table} table.'
            return render_template('forgot_password.html', success_message=success_message)
        else:
            error_message = "Email not found"
            return render_template('forgot_password.html', error_message=error_message)

    return render_template('forgot_password.html')


@app.route('/change_password_forgot_password', methods=['GET', 'POST'])
def change_password_forgot_password():
    email = request.args.get('email').lower()
    source_table = request.args.get('source_table')

    if request.method == 'POST':
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')

        if new_password != confirm_password:
            error_message = "Password not match"
            return render_template('change_password_forgot_password.html', error_message=error_message)

        response = check_valid_password(new_password)
        if response is not None:
            return render_template('change_password_forgot_password.html', error_message=response)

        con = get_db()
        cursor = con.cursor()
        query = f"UPDATE {source_table} SET Password = ? WHERE Email = ?"
        cursor.execute(query, (new_password, email))

        con.commit()
        cursor.close()
        con.close()

        success_message = "Password updated successfully."
        return render_template('first_page.html', success_message=success_message)

    return render_template('change_password_forgot_password.html', email=email, source_table=source_table)


@app.route('/volunteer_hours', methods=['GET', 'POST'])
def volunteer_hours():
    return render_template('volunteer_hours.html')


@app.route('/volunteer_trust_quiz', methods=['GET', 'POST'])
def volunteer_trust_quiz():
    if request.method == 'POST':
        try:
            form_data = request.form.to_dict()
            volunteer_id = session.get('user_id')

            if volunteer_id:
                con = get_db()
                cursor = con.cursor()

                email = session['email'].lower()
                cursor.execute("SELECT first_name FROM Volunteers_list WHERE email=?", (email,))
                volunteer_data = cursor.fetchone()

                if volunteer_data:
                    volunteer_first_name = volunteer_data[0]

                    query = """
                    INSERT INTO TrustquizResults (
                        volunteer_id, volunteered_before, previous_organization, age, occupation,
                        emotional_resilience, coping_strategy, availability, confidentiality_ability,
                        relevant_skills, skills_details, past_pressures, pressure_details, substance_abuse,
                        police_record, police_record_details, emergency_disclosure, app_understanding,
                        app_importance, why_volunteer
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """

                    values = (
                        volunteer_id,
                        form_data.get('volunteered_before', ''),
                        form_data.get('previous_organization', ''),
                        form_data.get('age', ''),
                        form_data.get('occupation', ''),
                        form_data.get('emotional_resilience', ''),
                        form_data.get('coping_strategy', ''),
                        form_data.get('availability', ''),
                        form_data.get('confidentiality_ability', ''),
                        form_data.get('relevant_skills', ''),
                        form_data.get('skills_details', ''),
                        form_data.get('past_pressures', ''),
                        form_data.get('pressure_details', ''),
                        form_data.get('substance_abuse', ''),
                        form_data.get('police_record', ''),
                        form_data.get('police_record_details', ''),
                        form_data.get('emergency_disclosure', ''),
                        form_data.get('app_understanding', ''),
                        form_data.get('app_importance', ''),
                        form_data.get('why_volunteer', '')
                    )

                    cursor.execute(query, values)
                    con.commit()

                    cursor.close()
                    return redirect(url_for('main_volunteer_page'))

                else:
                    return "Volunteer details not found. Please complete registration first."

            else:
                return jsonify({'success': False, 'error': 'Volunteer ID not found in session.'})

        except Exception as e:
            print(f"Error: {e}")
            return jsonify({'success': False, 'error': str(e)})

        finally:
            con.close()

    else:
        try:
            con = get_db()
            cursor = con.cursor()

            email = session['email'].lower()
            cursor.execute("SELECT first_name FROM Volunteers_list WHERE email=?", (email,))
            volunteer_data = cursor.fetchone()

            if volunteer_data:
                volunteer_first_name = volunteer_data[0]
                return render_template('volunteer_trust_quiz.html', volunteer_first_name=volunteer_first_name)

            else:
                return "Volunteer details not found. Please complete registration first."

        except Exception as e:
            print(f"Error: {e}")
            return jsonify({'success': False, 'error': str(e)})

        finally:
            con.close()


@app.route('/call_rate_contact')
def call_rate_contact():
    return render_template('call_rate_contact.html')


@app.route('/main_user_page')
def main_user_page():
    if 'email' in session:
        email = session['email'].lower()
        con = get_db()
        cursor = con.cursor()
        user_data = cursor.execute("SELECT first_name, written_code, spoken_code, ID FROM Users WHERE email=?",
                                   (email,)).fetchone()
        if user_data:
            user_first_name = user_data[0]
            user_written_code = user_data[1]
            user_spoken_code = user_data[2]
            session['user_id'] = user_data[3]
            return render_template('main_user_page.html', user_first_name=user_first_name,
                                   user_written_code=user_written_code, user_spoken_code=user_spoken_code)
        else:
            return "User details not found. Please complete registration first."
    else:
        return redirect(url_for('user_login'))


@app.route('/code_update', methods=['GET', 'POST'])
def code_update():
    if request.method == 'POST':
        written_code = request.form['written_code']
        audio_blob = request.form['audio_blob']
        email = session.get('email').lower()

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("UPDATE Users SET written_code = ?, spoken_code = ? WHERE email = ?",
                       (written_code, audio_blob, email))
        conn.commit()
        conn.close()

        flash('מילת הקוד עודכנה בהצלחה')
        return redirect(url_for('main_user_page'))

    return render_template('code_update.html')


@app.route('/contact_update')
def contact_update():
    return render_template('contact_update.html')



@app.route('/volunteers_hours_summary_report')
def volunteers_hours_summary_report():
    sql_query = '''
        SELECT
            v.first_name,
            v.last_name,
            SUM(
                CAST(SUBSTR(vl.logout_time, 12, 2) AS INTEGER) * 3600 +
                CAST(SUBSTR(vl.logout_time, 15, 2) AS INTEGER) * 60 +
                CAST(SUBSTR(vl.logout_time, 18, 2) AS INTEGER) -
                CAST(SUBSTR(vl.login_time, 12, 2) AS INTEGER) * 3600 -
                CAST(SUBSTR(vl.login_time, 15, 2) AS INTEGER) * 60 -
                CAST(SUBSTR(vl.login_time, 18, 2) AS INTEGER)
            ) AS total_seconds
        FROM
            Volunteers_list v
        LEFT JOIN VolunteersLogs vl ON v.ID = vl.volunteer_id
        WHERE
            vl.logout_time IS NOT NULL
        GROUP BY
            v.first_name,
            v.last_name
    '''
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute(sql_query)
    rows = cursor.fetchall()

    formatted_rows = []
    for row in rows:
        first_name = row[0]
        last_name = row[1]
        total_seconds = row[2] or 0
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        formatted_time = f"{hours:02}:{minutes:02}:{seconds:02}"
        formatted_rows.append((first_name, last_name, formatted_time))
        print(f"Debug: {first_name} {last_name} {formatted_time} ({total_seconds} seconds)")

    print(formatted_rows)
    conn.close()
    return render_template('volunteers_hours_summary_report.html', rows=formatted_rows)


def get_test_status(email):
    con = get_db()
    cursor = con.cursor()
    cursor.execute("SELECT test_status FROM Volunteers_list WHERE email=?", (email,))
    status = cursor.fetchone()
    con.close()
    return status[0] if status else None


@app.route('/check_volunteer_status', methods=['GET'])
def check_volunteer_status():
    if 'email' in session:
        email = session['email'].lower()
        test_status = get_test_status(email)
        if test_status:
            return jsonify({'status': test_status}), 200
        else:
            return jsonify({'error': 'Status not found'}), 404
    else:
        return jsonify({'error': 'Unauthorized'}), 401


@app.route('/volunteer_hours_report')
def volunteer_hours_report():
    logged_in_email = session.get('email').lower()
    if logged_in_email:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT
                v.first_name,
                v.last_name,
                vl.login_time,
                vl.logout_time
            FROM
                Volunteers_list v
            JOIN
                VolunteersLogs vl ON v.ID = vl.volunteer_id
            WHERE
                v.email = ?
        """, (logged_in_email,))
        rows = cursor.fetchall()
        conn.close()
        return render_template('volunteer_hours_report.html', rows=rows, first_name=session.get('first_name'))
    else:
        return "Email not found in session"


@app.route('/start_volunteering', methods=['POST'])
def start_volunteering():
    email = request.json.get('email').lower()
    conn = get_db()
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT ID FROM Volunteers_list WHERE email=?", (email,))
        volunteer = cursor.fetchone()
        if not volunteer:
            return jsonify({'error': 'Volunteer not found'}), 404

        volunteer_id = volunteer[0]
        login_time = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

        cursor.execute("INSERT INTO VolunteersLogs (volunteer_id, login_time) VALUES (?, ?)",
                       (volunteer_id, login_time))
        conn.commit()

        session[f"volunteer_{volunteer_id}_is_timing"] = True
        session["is_timing"] = True

        return jsonify({'message': 'Volunteering started successfully.'}), 200

    except Exception as e:
        return jsonify({'error': f'Failed to start volunteering: {str(e)}'}), 500

    finally:
        conn.close()


@app.route('/stop_volunteering', methods=['POST'])
def stop_volunteering():
    email = request.json.get('email').lower()
    conn = get_db()
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT ID FROM Volunteers_list WHERE email=?", (email,))
        volunteer = cursor.fetchone()
        if not volunteer:
            return jsonify({'error': 'Volunteer not found'}), 404

        volunteer_id = volunteer[0]

        cursor.execute(
            "SELECT id FROM VolunteersLogs WHERE volunteer_id = ? AND logout_time IS NULL ORDER BY id DESC LIMIT 1",
            (volunteer_id,))
        latest_session_id = cursor.fetchone()
        if not latest_session_id:
            return jsonify({'error': 'No active session found to stop.'}), 404

        logout_time = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        cursor.execute("UPDATE VolunteersLogs SET logout_time = ? WHERE id = ?",
                       (logout_time, latest_session_id[0]))
        conn.commit()

        session.pop(f"volunteer_{volunteer_id}_is_timing", None)
        session["is_timing"] = False

        return jsonify({'message': 'Volunteering stopped successfully.'}), 200

    except Exception as e:
        return jsonify({'error': f'Failed to stop volunteering: {str(e)}'}), 500

    finally:
        conn.close()


@app.route('/main_volunteer_page')
def main_volunteer_page():
    if 'email' in session:
        con = get_db()
        cursor = con.cursor()
        email = session['email'].lower()
        cursor.execute("SELECT ID, first_name, email FROM Volunteers_list WHERE email=?", (email,))
        volunteer_data = cursor.fetchone()
        if volunteer_data:
            volunteer_id, volunteer_first_name, email = volunteer_data
            session['first_name'] = volunteer_first_name  # שמירת השם הפרטי בסשן
            session['email'] = email  # שמירת האימייל בסשן
            session['volunteer_id'] = volunteer_id  # שמירת ה-ID של המתנדב בסשן
            test_status = get_test_status(email)
            return render_template('main_volunteer_page.html', volunteer_first_name=volunteer_first_name,
                                   test_status=test_status)
        else:
            return "Volunteer details not found."
    else:
        return redirect(url_for('user_login'))



@app.route('/main_association')
def main_association():
    return render_template('main_association.html')


@app.route('/users_report')
def users_report():
    sql_query = '''
SELECT
    u.first_name AS user_first_name,
    u.last_name AS user_last_name,
    u.email AS user_email,
    u.phone_number AS phone_number,
    a.App_rate AS App_rate
FROM
    App_rating a
JOIN
    users u ON a.user_id = u.ID
    '''

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(sql_query)
    rows = cursor.fetchall()
    print(rows)

    return render_template('users_report.html', rows=rows)


@app.route('/users_list')
def users_list():
    sql_query = '''
        SELECT
            ID,
            first_name,
            last_name,
            phone_number,
            email,
            Rating,
            password
        FROM
            Users
    '''
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(sql_query)
    rows = cursor.fetchall()
    return render_template('users_list.html', rows=rows)


@app.route('/new_volunteers')
def new_volunteers():
    sql_query1 = '''
            SELECT  ID, first_name, last_name
            FROM Volunteers_list
            WHERE test_status = 'UNCHECKED';
        '''

    conn = get_db()
    cursor1 = conn.cursor()
    cursor1.execute(sql_query1)
    rows1 = cursor1.fetchall()
    print(rows1)
    return render_template('new_volunteers.html', rows=rows1)


@app.route('/user_type_list')
def user_type_list():
    sql_query = '''
        SELECT ID,Email, UserType
        FROM login_type
    '''
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(sql_query)
    rows = cursor.fetchall()

    return render_template('user_type_list.html', rows=rows)


@app.route('/volunteers_list')
def volunteers_list():
    sql_query = '''
        SELECT
        ID,
            first_name,
            last_name,
            phone_number,
            email,
            password,
            registration_date,
            test_status
        FROM
            Volunteers_list
    '''
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(sql_query)
    rows = cursor.fetchall()

    return render_template('volunteers_list.html', rows=rows)


@app.route('/trust_quiz_report', methods=['GET', 'POST'])
def trust_quiz_report():
    if request.method == 'POST':
        data = request.get_json()
        volunteer_id = data.get('volunteer_id')
        new_status = data.get('new_status')

        print("Received data for updating status:")
        print("Volunteer ID:", volunteer_id)
        print("New Status:", new_status)

        conn = get_db()
        cursor = conn.cursor()

        sql_update_status = "UPDATE Volunteers_list SET test_status = ? WHERE Volunteers_list.ID = ?"
        cursor.execute(sql_update_status, (new_status, volunteer_id))
        conn.commit()

        return jsonify({"message": "Status updated successfully"}), 200

    else:
        volunteer_id = request.args.get('ID')

        sql_query = '''
                SELECT *
                FROM TrustquizResults
                WHERE volunteer_id = ?;
            '''
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(sql_query, (volunteer_id,))
        volunteer_details = cursor.fetchone()

        if volunteer_details:
            print("Volunteer Details:", volunteer_details)

        return render_template('trust_quiz_report.html', volunteer_details=volunteer_details)


@app.route('/contact_list')
def contact_list():
    sql_query = '''
        SELECT
            ID,
            UserID,
            First_Name,
            Last_Name,
            Phone_Number,
            Email,
            password,
            is_active
        FROM
            contact_list
    '''
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(sql_query)
    rows = cursor.fetchall()

    return render_template('contact_list.html', rows=rows)


@app.route('/trustquizres')
def trustquizres():
    sql_query = '''
        SELECT
                volunteer_id,
                volunteered_before,
                previous_organization,
                age

        FROM
            TrustquizResults
    '''
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(sql_query)
    rows = cursor.fetchall()

    return render_template('trustquizres.html', rows=rows)


@app.route('/rating')
def rating():
    sql_query = '''
        SELECT
            ID,
            user_id,
            user_type,
            email,
            phone_number,
            first_name,
            last_name,
            App_rate
        FROM
            App_rating
    '''
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(sql_query)
    rows = cursor.fetchall()

    return render_template('rating.html', rows=rows)


@app.route('/user_rating', methods=['POST', 'GET'])
def user_rating():
    try:
        if request.method == 'GET':
            return render_template('user_rating.html')

        rating = request.form.get('rating')
        userType = request.form.get('user_type')
        email = session.get('email').lower()
        userFirstName = request.form.get('user_first_name')
        userFeedback = request.form.get('user_feedback')

        print("Rating:", rating)
        print("User Type:", userType)
        print("Email:", email)
        print("User First Name:", userFirstName)
        print("Feedback:", userFeedback)

        con = get_db()
        cursor = con.cursor()

        user_data = cursor.execute("SELECT UserType, ID FROM login_type WHERE Email=?", (email,)).fetchone()
        print("User Data:", user_data)
        if not user_data:
            return "User not found", 404

        stored_user_type, user_id = user_data

        if stored_user_type == 'User':
            user_info = cursor.execute("SELECT ID, phone_number, first_name, last_name FROM Users WHERE email=?",
                                       (email,)).fetchone()
        elif stored_user_type == 'Contact':
            user_info = cursor.execute("SELECT ID, phone_number, first_name, last_name FROM contact_list WHERE email=?",
                                       (email,)).fetchone()
        elif stored_user_type == 'Volunteer':
            user_info = cursor.execute(
                "SELECT ID, phone_number, first_name, last_name FROM Volunteers_list WHERE email=?",
                (email,)).fetchone()
        else:
            user_info = None

        print("User Info:", user_info)

        if not user_info:
            return "User information not found", 404

        user_id, phone_number, first_name, last_name = user_info

        cursor.execute(
            "INSERT INTO App_rating (user_id, user_type, email, phone_number, first_name, last_name, App_rate, feedback) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (user_id, stored_user_type, email, phone_number, first_name, last_name, rating, userFeedback))

        con.commit()
        con.close()

        return redirect(url_for('main_volunteer_page'))

    except Exception as e:
        print("Error:", e)
        return "An error occurred while processing your request. Please try again later.", 500


@app.route('/users_contact')
def users_contact():
    if 'email' in session:
        email = session['email'].lower()
        conn = get_db()
        cursor = conn.cursor()

        cursor.execute("SELECT ID FROM Users WHERE email=?", (email,))
        user_data = cursor.fetchone()
        if user_data:
            user_id = str(user_data[0])
            session['user_id'] = user_id

            query = "SELECT * FROM contact_list WHERE UserID=? AND is_active!='deleted'"
            cursor.execute(query, (user_id,))
            contacts = cursor.fetchall()

            cursor.close()

            print(f"Contacts fetched for {email}: {contacts}")
            return render_template('users_contact.html', contacts=contacts)
        else:
            return "User details not found. Please complete registration first."
    else:
        return redirect(url_for('user_login'))


@app.route('/delete_contact', methods=['POST'])
def delete_contact():
    if 'email' in session:
        email = session['email'].lower()
        conn = get_db()
        cursor = conn.cursor()

        cursor.execute("SELECT ID FROM Users WHERE email=?", (email,))
        user_data = cursor.fetchone()
        if user_data:
            user_id = str(user_data[0])
            session['user_id'] = user_id

            contact_id = request.json.get('contact_id')

            query = "UPDATE contact_list SET is_active='deleted' WHERE ID=? AND UserID=?"
            cursor.execute(query, (contact_id, user_id))
            conn.commit()

            cursor.close()
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'error': 'User details not found. Please complete registration first.'}), 400
    else:
        return jsonify({'success': False, 'error': 'Not logged in'}), 401


@app.route('/contact_user_update', methods=['POST'])
def contact_user_update():
    if 'email' in session:
        email = session['email'].lower()
        conn = get_db()
        cursor = conn.cursor()

        cursor.execute("SELECT ID FROM Users WHERE email=?", (email,))
        user_data = cursor.fetchone()
        if user_data:
            user_id = str(user_data[0])
            session['user_id'] = user_id

            contact_id = request.json.get('contact_id')
            new_email = request.json.get('email').lower()
            new_first_name = request.json.get('first_name')
            new_last_name = request.json.get('last_name')
            new_phone_number = request.json.get('phone_number')

            query = "UPDATE contact_list SET First_Name=?, Last_Name=?, Phone_Number=?, Email=? WHERE ID=? AND UserID=?"
            cursor.execute(query, (new_first_name, new_last_name, new_phone_number, new_email, contact_id, user_id))
            conn.commit()

            cursor.close()
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'error': 'User details not found. Please complete registration first.'}), 400
    else:
        return jsonify({'success': False, 'error': 'Not logged in'}), 401


@app.route('/contact_sign_up_update', methods=['GET', 'POST'])
def contact_sign_up_update():
    if request.method == 'POST':
        try:
            contact_id = request.form.get('contact_id')
            First_Name = request.form.get('First_Name')
            Last_Name = request.form.get('Last_Name')
            Phone_Number = request.form.get('Phone_Number')
            Email = request.form.get('email').lower()
            Password = request.form.get('Password')
            confirm_password = request.form.get('Confirm_Password')

            print(f"Form data received: First_Name={First_Name}, Last_Name={Last_Name}, "
                  f"Phone_Number={Phone_Number}, Email={Email}, Password={Password}, Confirm_Password={confirm_password}")

            if Password != confirm_password:
                flash("Passwords do not match.", "error")
                return redirect(url_for('contact_sign_up_update'))
            if len(Password) < 6 or not any(c.isupper() for c in Password) or not any(
                    c.islower() for c in Password) or not any(c.isdigit() for c in Password):
                flash(
                    "Password must be at least 6 characters long and contain at least one uppercase letter, one lowercase letter, and one number.",
                    "error")
                return redirect(url_for('contact_sign_up_update'))

            con = get_db()
            cursor = con.cursor()

            cursor.execute(
                "UPDATE contact_list SET First_Name=?, Last_Name=?, Phone_Number=?, Email=?, Password=?, is_active=? WHERE ID=?",
                (First_Name, Last_Name, Phone_Number, Email, Password, 'active', contact_id))
            con.commit()

            cursor.close()
            return redirect(url_for('user_login'))

        except Exception as e:
            print("An error occurred while updating contact:", e)
            flash("An error occurred while updating the contact. Please try again later.", "error")
            return redirect(url_for('contact_sign_up_update'))

    return render_template('contact_sign_up_update.html')


@app.route('/users_rate_call', methods=['POST', 'GET'])
def users_rate_call():
    try:
        if request.method == 'GET':
            return render_template('users_rate_call.html')

        rating = request.form.get('rating')
        email = session.get('email').lower()
        userFirstName = request.form.get('user_first_name')
        userFeedback = request.form.get('user_feedback')
        appFeedback = request.form.get('app_feedback')

        print("Rating:", rating)
        print("Email:", email)
        print("User First Name:", userFirstName)
        print("User Feedback:", userFeedback)
        print("App Feedback:", appFeedback)

        con = get_db()
        cursor = con.cursor()

        user_data = cursor.execute("SELECT UserType, ID FROM login_type WHERE Email=?", (email,)).fetchone()
        print("User Data:", user_data)
        if not user_data:
            return "User not found", 404

        stored_user_type, user_id = user_data

        if stored_user_type == 'User':
            user_info = cursor.execute("SELECT ID, phone_number, first_name, last_name FROM Users WHERE email=?",
                                       (email,)).fetchone()
        elif stored_user_type == 'Contact':
            user_info = cursor.execute("SELECT ID, phone_number, first_name, last_name FROM contact_list WHERE email=?",
                                       (email,)).fetchone()
        elif stored_user_type == 'Volunteer':
            user_info = cursor.execute(
                "SELECT ID, phone_number, first_name, last_name FROM Volunteers_list WHERE email=?",
                (email,)).fetchone()
        else:
            user_info = None

        print("User Info:", user_info)

        if not user_info:
            return "User information not found", 404

        user_id, phone_number, first_name, last_name = user_info

        cursor.execute(
            "INSERT INTO App_rating (user_id, user_type, email, phone_number, first_name, last_name, App_rate, feedback, app_feedback) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (user_id, stored_user_type, email, phone_number, first_name, last_name, rating, userFeedback, appFeedback))

        con.commit()
        con.close()

        return redirect(url_for('main_user_page'))

    except Exception as e:
        print("Error:", e)
        return "An error occurred while processing your request. Please try again later.", 500


@app.route('/volunteer_rate_call', methods=['POST', 'GET'])
def volunteer_rate_call():
    try:
        if request.method == 'GET':
            return render_template('volunteer_rate_call.html')

        rating = request.form.get('rating')
        email = session.get('email').lower()
        volunteerFirstName = request.form.get('volunteer_first_name')
        userFirstName = request.form.get('user_first_name')
        userFeedback = request.form.get('user_feedback')
        appFeedback = request.form.get('app_feedback')

        print("Rating:", rating)
        print("Email:", email)
        print("Volunteer First Name:", volunteerFirstName)
        print("User First Name:", userFirstName)
        print("User Feedback:", userFeedback)
        print("App Feedback:", appFeedback)

        con = get_db()
        cursor = con.cursor()

        user_data = cursor.execute("SELECT UserType, ID FROM login_type WHERE Email=?", (email,)).fetchone()
        print("User Data:", user_data)
        if not user_data:
            return "User not found", 404

        stored_user_type, user_id = user_data

        if stored_user_type == 'User':
            user_info = cursor.execute("SELECT ID, phone_number, first_name, last_name FROM Users WHERE email=?",
                                       (email,)).fetchone()
        elif stored_user_type == 'Contact':
            user_info = cursor.execute("SELECT ID, phone_number, first_name, last_name FROM contact_list WHERE email=?",
                                       (email,)).fetchone()
        elif stored_user_type == 'Volunteer':
            user_info = cursor.execute(
                "SELECT ID, phone_number, first_name, last_name FROM Volunteers_list WHERE email=?",
                (email,)).fetchone()
        else:
            user_info = None

        print("User Info:", user_info)

        if not user_info:
            return "User information not found", 404

        user_id, phone_number, first_name, last_name = user_info

        cursor.execute(
            "INSERT INTO App_rating (user_id, user_type, email, phone_number, first_name, last_name, App_rate, feedback, app_feedback) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (user_id, stored_user_type, email, phone_number, first_name, last_name, rating, userFeedback, appFeedback))

        con.commit()
        con.close()

        return redirect(url_for('main_volunteer_page'))

    except Exception as e:
        print("Error:", e)
        return "An error occurred while processing your request. Please try again later.", 500


@app.route('/show_user_contact')
def show_user_contact():
    sql_query = '''
        SELECT
            u.first_name AS user_first_name,
            u.last_name AS user_last_name,
            c.First_Name AS contact_first_name,
            c.Last_Name AS contact_last_name,
            c.Phone_Number,
            c.Email
        FROM
            Users u
        JOIN
            contact_list c ON u.ID = c.UserID
        WHERE
            c.is_active != 'deleted'
    '''
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(sql_query)
    rows = cursor.fetchall()
    return render_template('show_user_contact.html', rows=rows)


@app.route('/user_main_login', methods=['POST', 'GET'])
def user_main_login():
    try:
        if request.method == 'GET':
            return render_template('user_main_login.html')

        email = request.form.get('email').lower()
        password = request.form.get('password')
        print("Received email:", email)
        print("Received password:", password)

        con = get_db()
        cursor = con.cursor()

        cursor.execute("SELECT UserType, ID FROM login_type WHERE Email=?", (email,))
        user_data = cursor.fetchone()
        print("User Data:", user_data)

        if not user_data:
            print("Email not found")
            return "Email not found", 404

        user_type, user_id = user_data
        print("User Type:", user_type)
        print("User ID:", user_id)

        if user_type == 'User':
            cursor.execute("SELECT password, first_name FROM Users WHERE email=?", (email,))
            user_info = cursor.fetchone()
        elif user_type == 'Contact':
            cursor.execute("SELECT password, First_Name FROM contact_list WHERE Email=?", (email,))
            user_info = cursor.fetchone()
        elif user_type == 'Volunteer':
            cursor.execute("SELECT password, first_name FROM Volunteers_list WHERE email=?", (email,))
            user_info = cursor.fetchone()
        else:
            user_info = None

        print("User Info:", user_info)

        if user_info and user_info[0] == password:
            session['email'] = email
            session['user_id'] = user_id
            session['first_name'] = user_info[1]

            if user_type == 'User':
                return redirect(url_for('main_user_page'))
            elif user_type == 'Contact':
                return redirect(url_for('main_contact'))
            elif user_type == 'Volunteer':
                return redirect(url_for('main_volunteer_page'))
            else:
                return "Invalid user type", 400
        else:
            print("Password mismatch")
            return "Password mismatch", 401

    except Exception as e:
        print("Error:", e)
        return "An error occurred while processing your request. Please try again later.", 500


@app.route('/call_receive', methods=['POST', 'GET'])
def call_receive():
    user_first_name = request.args.get('user_first_name')
    print(f"Session data on call_receive: {session}")
    return render_template('call_receive.html', user_first_name=user_first_name)



if __name__ == '__main__':
    app.run(debug=True, port=5000)
