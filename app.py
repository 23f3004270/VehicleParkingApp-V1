from flask import Flask, session, redirect, url_for
from models.schema import init_db
from controllers.auth import auth_bp
from controllers.admin import adm_bp
from controllers.user import user_bp # import user
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24)

# register blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(adm_bp)
app.register_blueprint(user_bp) # register user

@app.route('/')
def home():
    if 'uid' in session:
        if session.get('user_role') == 'admin':
            return redirect(url_for('admin.dashboard'))
        else:
            return redirect(url_for('user.dashboard')) # updated redirect
    return redirect(url_for('auth.login'))

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
