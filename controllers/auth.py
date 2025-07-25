from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3

DATABASE_FILE = 'parkezily.db'

auth_bp = Blueprint('auth', __name__, template_folder='templates')

def get_db():
    db = sqlite3.connect(DATABASE_FILE)
    db.row_factory = sqlite3.Row
    return db

@auth_bp.route('/register', methods=['GET', 'POST'])
def register(): # Function renamed to 'register'
    if request.method == 'GET':
        return render_template('register.html')

    name = request.form['fullName']
    email = request.form['email']
    pwd = request.form['password']

    db = get_db()
    user = db.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()

    if user:
        flash('Email already registered.', 'warning')
        db.close()
        return redirect(url_for('auth.register')) # Updated url_for

    hash_pwd = generate_password_hash(pwd, method='pbkdf2:sha256')

    db.execute('INSERT INTO users (name, email, password, role) VALUES (?, ?, ?, ?)',
                     (name, email, hash_pwd, 'user'))
    db.commit()
    db.close()

    flash('Registration complete. Please log in.', 'success')
    return redirect(url_for('auth.login')) # Updated url_for

@auth_bp.route('/login', methods=['GET', 'POST'])
def login(): # Function renamed to 'login'
    if request.method == 'GET':
        return render_template('login.html')

    email = request.form['email']
    pwd = request.form['password']

    db = get_db()
    user = db.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
    db.close()

    if not user or not check_password_hash(user['password'], pwd):
        flash('Login failed. Check details.', 'danger')
        return redirect(url_for('auth.login')) # Updated url_for

    session['uid'] = user['id']
    session['name'] = user['name']
    session['user_role'] = user['role']

    if user['role'] == 'admin':
        return redirect(url_for('admin.dashboard'))
    else:
        return redirect(url_for('user.dashboard'))

@auth_bp.route('/logout')
def logout(): # Function renamed to 'logout'
    session.clear()
    flash('Successfully logged out.', 'info')
    return redirect(url_for('auth.login')) # Updated url_for