from flask import Blueprint, render_template, request, redirect, url_for, session, flash
import sqlite3
from functools import wraps
from datetime import datetime

DB_FILE = 'parkezily.db'

adm_bp = Blueprint('admin', __name__, template_folder='templates')

def get_db():
    # db connect
    db = sqlite3.connect(DB_FILE)
    db.row_factory = sqlite3.Row
    return db

def login_req(f):
    # decorator check
    @wraps(f)
    def wrapper(*args, **kwargs):
        if 'user_role' not in session or session['user_role'] != 'admin':
            flash('Admin access is required for this page.', 'danger')
            return redirect(url_for('auth.login')) # CHANGE THIS LINE
        return f(*args, **kwargs)
    return wrapper

@adm_bp.route('/admin/dashboard')
@login_req
def dashboard():
    # main view
    db = get_db()
    lots = db.execute('SELECT * FROM parking_lot').fetchall()
    users = db.execute("SELECT id, name, email FROM users WHERE role = 'user'").fetchall()
    db.close()
    return render_template('admin/dashboard.html', lots=lots, users=users)

@adm_bp.route('/admin/lot/create', methods=['GET', 'POST'])
@login_req
def create_lot():
    # new lot form
    if request.method == 'POST':
        name = request.form['name']
        addr = request.form['addr']
        pin = request.form['pin']
        cap = int(request.form['cap'])
        cost = float(request.form['cost'])

        db = get_db()
        cur = db.cursor()
        cur.execute(
            'INSERT INTO parking_lot (location_name, address, pin_code, max_spots, price_per_hour) VALUES (?, ?, ?, ?, ?)',
            (name, addr, pin, cap, cost)
        )
        lot_id = cur.lastrowid

        # auto-create spots
        for _ in range(cap):
            cur.execute('INSERT INTO parking_spot (lot_id, status) VALUES (?, ?)', (lot_id, 'A'))

        db.commit()
        db.close()
        flash(f'Lot "{name}" created with {cap} spots.', 'success')
        return redirect(url_for('admin.dashboard'))

    return render_template('admin/add_lot.html')

@adm_bp.route('/admin/lot/update/<int:lot_id>', methods=['GET', 'POST'])
@login_req
def update_lot(lot_id):
    # edit existing
    db = get_db()
    lot = db.execute('SELECT * FROM parking_lot WHERE id = ?', (lot_id,)).fetchone()

    if request.method == 'POST':
        name = request.form['name']
        addr = request.form['addr']
        pin = request.form['pin']
        cap = int(request.form['cap'])
        cost = float(request.form['cost'])

        db.execute(
            'UPDATE parking_lot SET location_name = ?, address = ?, pin_code = ?, max_spots = ?, price_per_hour = ? WHERE id = ?',
            (name, addr, pin, cap, cost, lot_id)
        )
        
        # simple spot update
        db.execute('DELETE FROM parking_spot WHERE lot_id = ?', (lot_id,))
        for _ in range(cap):
            db.execute('INSERT INTO parking_spot (lot_id, status) VALUES (?, ?)', (lot_id, 'A'))

        db.commit()
        db.close()
        flash(f'Lot "{name}" updated.', 'success')
        return redirect(url_for('admin.dashboard'))

    db.close()
    return render_template('admin/edit_lot.html', lot=lot)

@adm_bp.route('/admin/lot/remove/<int:lot_id>', methods=['POST'])
@login_req
def remove_lot(lot_id):
    # remove lot
    db = get_db()
    db.execute('DELETE FROM parking_lot WHERE id = ?', (lot_id,))
    db.commit()
    db.close()
    flash('Parking lot removed.', 'info')
    return redirect(url_for('admin.dashboard'))

@adm_bp.route('/admin/lot/inspect/<int:lot_id>')
@login_req
def inspect_lot(lot_id):
    # view spots
    db = get_db()
    lot = db.execute('SELECT * FROM parking_lot WHERE id = ?', (lot_id,)).fetchone()
    spots = db.execute('SELECT * FROM parking_spot WHERE lot_id = ?', (lot_id,)).fetchall()
    db.close()
    return render_template('admin/view_lot.html', lot=lot, spots=spots)

def format_duration(start, end):
    # duration helper
    if not end:
        return "Active"
    start_dt = datetime.strptime(start, '%Y-%m-%d %H:%M:%S.%f')
    end_dt = datetime.strptime(end, '%Y-%m-%d %H:%M:%S.%f')
    delta = end_dt - start_dt
    
    hrs, rem = divmod(delta.seconds, 3600)
    mins, _ = divmod(rem, 60)
    
    if hrs > 0:
        return f"{hrs}h {mins}m"
    return f"{mins}m"

@adm_bp.route('/admin/records')
@login_req
def records():
    # view all records
    db = get_db()
    raw_records = db.execute(
        '''
        SELECT u.name, p.location_name, r.start_time, r.end_time, r.total_cost
        FROM reservation r
        JOIN users u ON r.user_id = u.id
        JOIN parking_spot ps ON r.spot_id = ps.id
        JOIN parking_lot p ON ps.lot_id = p.id
        ORDER BY r.start_time DESC
        '''
    ).fetchall()

    processed_records = []
    for rec in raw_records:
        rec_dict = dict(rec)
        rec_dict['duration'] = format_duration(rec['start_time'], rec['end_time'])
        processed_records.append(rec_dict)

    db.close()
    return render_template('admin/records.html', records=processed_records)