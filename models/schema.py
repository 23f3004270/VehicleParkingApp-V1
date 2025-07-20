import sqlite3
import os

DB_NAME = "parkingo.db"

def init_db():
    if os.path.exists(DB_NAME):
        return
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        role TEXT NOT NULL CHECK(role IN ('admin', 'user'))
    );
    ''')
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS parking_lot (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        location_name TEXT NOT NULL,
        address TEXT NOT NULL,
        price_per_hour REAL NOT NULL,
        pin_code TEXT NOT NULL,
        max_spots INTEGER NOT NULL
    );
    ''')
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS parking_spot (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        lot_id INTEGER NOT NULL,
        status TEXT NOT NULL CHECK(status IN ('A', 'O')), -- A=Available, O=Occupied
        FOREIGN KEY (lot_id) REFERENCES parking_lot(id) ON DELETE CASCADE
    );
    ''')
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS reservation (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        spot_id INTEGER NOT NULL,
        start_time DATETIME NOT NULL,
        end_time DATETIME,
        total_cost REAL,
        FOREIGN KEY (user_id) REFERENCES users(id),
        FOREIGN KEY (spot_id) REFERENCES parking_spot(id)
    );
    ''')

    cursor.execute("INSERT INTO users (name, email, password, role) VALUES (?, ?, ?, ?)", ('Admin', 'admin@parkingo.com', 'admin123', 'admin'))
    conn.commit()
    conn.close()
