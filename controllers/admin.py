from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
import sqlite3
from functools import wraps
from datetime import datetime
from .utils import format_duration, format_ist

DB_FILE = 'parkezily.db'
adm_bp = Blueprint('admin', __name__, template_folder='templates')

def get_db():
    # db connect
    db = sqlite3.connect(DB_FILE)
    db.row_factory = sqlite3.Row
    return db

def login_req(f):
    # auth decorator
    @wraps(f)
    def wrapper(*args, **kwargs):
        if 'user_role' not in session or session['user_role'] != 'admin':
            flash('Admin access is required.', 'danger')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return wrapper

@adm_bp.route('/admin/dashboard')
@login_req
def dashboard():
    # main view
    db = get_db()
    lots = db.execute("SELECT * FROM parking_lot WHERE status = 'active'").fetchall()
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
    # soft delete
    db = get_db()
    active_res = db.execute(
        'SELECT r.id, r.start_time, ps.id as spot_id FROM reservation r JOIN parking_spot ps ON r.spot_id = ps.id WHERE ps.lot_id = ? AND r.end_time IS NULL',
        (lot_id,)
    ).fetchall()
    lot_price = db.execute('SELECT price_per_hour FROM parking_lot WHERE id = ?', (lot_id,)).fetchone()['price_per_hour']
    now = datetime.utcnow()
    for res in active_res:
        start_time = datetime.strptime(res['start_time'], '%Y-%m-%d %H:%M:%S.%f')
        cost = ((now - start_time).total_seconds() / 3600) * lot_price
        db.execute('UPDATE reservation SET end_time = ?, total_cost = ? WHERE id = ?', (now, cost, res['id']))
        db.execute("UPDATE parking_spot SET status = 'A' WHERE id = ?", (res['spot_id'],))
    db.execute("UPDATE parking_lot SET status = 'deleted' WHERE id = ?", (lot_id,))
    db.commit()
    db.close()
    if active_res:
        flash(f'Lot deleted. {len(active_res)} active session(s) were forcibly ended.', 'warning')
    else:
        flash('Parking lot deleted successfully.', 'info')
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

@adm_bp.route('/admin/records')
@login_req
def records():
    # view all records
    db = get_db()
    raw_recs = db.execute(
        '''
        SELECT u.name, p.location_name, p.status as lot_status, r.start_time, r.end_time, r.total_cost
        FROM reservation r JOIN users u ON r.user_id = u.id
        LEFT JOIN parking_spot ps ON r.spot_id = ps.id
        LEFT JOIN parking_lot p ON ps.lot_id = p.id
        ORDER BY r.start_time DESC
        '''
    ).fetchall()
    proc_recs = []
    for rec in raw_recs:
        rec_dict = dict(rec)
        rec_dict['duration'] = format_duration(rec['start_time'], rec['end_time'])
        rec_dict['start_ist'] = format_ist(rec['start_time'])
        rec_dict['end_ist'] = format_ist(rec['end_time'])
        proc_recs.append(rec_dict)
    db.close()
    return render_template('admin/records.html', records=proc_recs)

@adm_bp.route('/admin/search', methods=['GET', 'POST'])
@login_req
def search():
    # find user/spot
    results = None
    query = ""
    if request.method == 'POST':
        query = request.form['query']
        db = get_db()
        if query.isdigit():
            spot_id = int(query)
            spot_info = db.execute(
                'SELECT ps.id, ps.status, pl.location_name FROM parking_spot ps JOIN parking_lot pl ON ps.lot_id = pl.id WHERE ps.id = ?', (spot_id,)
            ).fetchone()
            results = {'spots': [dict(spot_info)] if spot_info else []}
        else:
            search_term = f"%{query}%"
            users = db.execute(
                "SELECT id, name, email FROM users WHERE (name LIKE ? OR email LIKE ?) AND role = 'user'", (search_term, search_term)
            ).fetchall()
            user_results = []
            for usr in users:
                active_res = db.execute(
                    'SELECT p.location_name, ps.id as spot_num FROM reservation r JOIN parking_spot ps ON r.spot_id = ps.id JOIN parking_lot p ON ps.lot_id = p.id WHERE r.user_id = ? AND r.end_time IS NULL', (usr['id'],)
                ).fetchone()
                usr_data = dict(usr)
                usr_data['parking'] = dict(active_res) if active_res else None
                user_results.append(usr_data)
            results = {'users': user_results}
        db.close()
        if not results.get('users') and not results.get('spots'):
            flash('No matches found for your query.', 'info')
    return render_template('admin/search.html', results=results, query=query)

@adm_bp.route('/admin/charts/data')
@login_req
def chart_data():
    db = get_db()
    
    # pichart
    occupied_count = db.execute("SELECT COUNT(id) as count FROM parking_spot WHERE status = 'O'").fetchone()['count']
    available_count = db.execute("SELECT COUNT(id) as count FROM parking_spot WHERE status = 'A'").fetchone()['count']
    
    # barchart
    lots = db.execute("SELECT id, location_name FROM parking_lot WHERE status = 'active'").fetchall()
    lot_labels = [lot['location_name'] for lot in lots]
    lot_availability = []
    for lot in lots:
        avail = db.execute("SELECT COUNT(id) as count FROM parking_spot WHERE lot_id = ? AND status = 'A'", (lot['id'],)).fetchone()['count']
        lot_availability.append(avail)

    db.close()
    
    return jsonify({
        'pie': {
            'occupied': occupied_count,
            'available': available_count
        },
        'bar': {
            'labels': lot_labels,
            'availability': lot_availability
        }
    })