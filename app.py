from flask import Flask
from models.schema import init_db

app = Flask(__name__)
init_db()

@app.route('/')
def index():
    return 'DB initialized'

if __name__ == '__main__':
    app.run(debug=True)
