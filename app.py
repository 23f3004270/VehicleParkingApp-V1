from flask import Flask, session, redirect, url_for, render_template
from models.schema import init_db
from controllers.auth import auth_controller
import os

application = Flask(__name__)
application.config['SECRET_KEY'] = os.urandom(24)
application.register_blueprint(auth_controller, url_prefix='/')

@application.route('/')
def home():
    if 'user_id' in session:
        if session.get('user_role') == 'admin':
            return redirect(url_for('admin_panel'))
        else:
            return redirect(url_for('user_panel'))
    # If no one is logged in, redirect to the login page
    return redirect(url_for('auth.login_user'))

@application.route('/admin/panel')
def admin_panel():
    if session.get('user_role') != 'admin':
        return redirect(url_for('auth.login_user'))
    user_name = session.get('user_name', 'Admin')
    # This will be replaced by a real template later
    return f"<h1>Admin Dashboard</h1><p>Welcome, {user_name}!</p><a href='/logout'>Logout</a>"

@application.route('/dashboard')
def user_panel():
    if 'user_id' not in session:
        return redirect(url_for('auth.login_user'))
    user_name = session.get('user_name', 'User')
    # This will be replaced by a real template later
    return f"<h1>User Dashboard</h1><p>Welcome, {user_name}!</p><a href='/logout'>Logout</a>"

if __name__ == '__main__':
    init_db()
    application.run(debug=True)