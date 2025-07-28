# models/schema.py
import sqlite3
import os
from werkzeug.security import generate_password_hash

DB_NAME = "parkezily.db"

def init_db():
    if os.path.exists(DB_NAME):
        return

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # user table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        role TEXT NOT NULL CHECK(role IN ('admin', 'user'))
    );
    """)

    # lot table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS parking_lot (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        location_name TEXT NOT NULL,
        address TEXT NOT NULL,
        price_per_hour REAL NOT NULL,
        pin_code TEXT NOT NULL,
        max_spots INTEGER NOT NULL,
        status TEXT NOT NULL DEFAULT 'active'
    );
    """)

    # spot table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS parking_spot (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        lot_id INTEGER NOT NULL,
        status TEXT NOT NULL CHECK(status IN ('A', 'O')),
        FOREIGN KEY (lot_id) REFERENCES parking_lot(id) ON DELETE CASCADE
    );
    """)

    # reservation table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS reservation (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        spot_id INTEGER,
        start_time DATETIME NOT NULL,
        end_time DATETIME,
        total_cost REAL,
        FOREIGN KEY (user_id) REFERENCES users(id),
        FOREIGN KEY (spot_id) REFERENCES parking_spot(id) ON DELETE SET NULL
    );
    """)

    # insert admin
    hashed_pass = generate_password_hash('admin123', method='pbkdf2:sha256')
    cursor.execute(
        "INSERT INTO users (name, email, password, role) VALUES (?, ?, ?, ?)",
        ('Admin', 'admin@parkezily.com', hashed_pass, 'admin')
    )

    conn.commit()
    conn.close()
    print(f"Database '{DB_NAME}' initialized.")