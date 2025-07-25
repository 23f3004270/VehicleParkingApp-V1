from flask import Flask, session, redirect, url_for
from models.schema import init_db
from controllers.auth import auth_bp
from controllers.admin import adm_bp
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24)

app.register_blueprint(auth_bp)
app.register_blueprint(adm_bp)

@app.route('/')
def home():
    #fixed
    if 'uid' in session:
        if session.get('user_role') == 'admin':
            return redirect(url_for('admin.dashboard'))
        else:
            return redirect(url_for('user_dash'))
    return redirect(url_for('auth.login')) # Updated 

@app.route('/dashboard')
def user_dash():
    if 'uid' not in session:
        return redirect(url_for('auth.login')) # Updated url_for
    name = session.get('name', 'User')
    return f"<h1>User Dashboard</h1><p>Welcome, {name}!</p><a href='/logout'>Logout</a>"

if __name__ == '__main__':
    init_db()
    app.run(debug=True)