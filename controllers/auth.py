from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3

DATABASE_FILE = 'parkezily.db'

auth_controller = Blueprint('auth', __name__, template_folder='templates')

def get_database_connection():
    connection = sqlite3.connect(DATABASE_FILE)
    connection.row_factory = sqlite3.Row
    return connection

@auth_controller.route('/register', methods=['GET', 'POST'])
def register_user():
    if request.method == 'GET':
        return render_template('register.html')

    full_name = request.form['fullName']
    email_address = request.form['email']
    password_text = request.form['password']

    db_conn = get_database_connection()
    existing_user = db_conn.execute('SELECT * FROM users WHERE email = ?', (email_address,)).fetchone()

    if existing_user:
        flash('An account with this email already exists.', 'warning')
        db_conn.close()
        return redirect(url_for('auth.register_user'))

    hashed_password = generate_password_hash(password_text, method='pbkdf2:sha256')

    db_conn.execute('INSERT INTO users (name, email, password, role) VALUES (?, ?, ?, ?)',
                     (full_name, email_address, hashed_password, 'user'))
    db_conn.commit()
    db_conn.close()

    flash('You have successfully registered! Please log in.', 'success')
    return redirect(url_for('auth.login_user'))

@auth_controller.route('/login', methods=['GET', 'POST'])
def login_user():
    if request.method == 'GET':
        return render_template('login.html')

    email_address = request.form['email']
    password_text = request.form['password']

    db_conn = get_database_connection()
    user_account = db_conn.execute('SELECT * FROM users WHERE email = ?', (email_address,)).fetchone()
    db_conn.close()

    if not user_account or not check_password_hash(user_account['password'], password_text):
        flash('Invalid credentials. Please check your details and try again.', 'danger')
        return redirect(url_for('auth.login_user'))

    session['user_id'] = user_account['id']
    session['user_name'] = user_account['name']
    session['user_role'] = user_account['role']

    if user_account['role'] == 'admin':
        return redirect(url_for('admin_panel'))
    else:
        return redirect(url_for('user_panel'))

@auth_controller.route('/logout')
def logout_user():
    session.clear()
    flash('You have been successfully logged out.', 'info')
    return redirect(url_for('auth.login_user'))