from flask import Blueprint, render_template, request, redirect, url_for, session, flash
import sqlite3
from functools import wraps
from datetime import datetime
from .utils import format_duration, format_ist

DB_FILE = 'parkezily.db'
user_bp = Blueprint('user', __name__, template_folder='templates')

def get_db():
    db = sqlite3.connect(DB_FILE)
    db.row_factory = sqlite3.Row
    return db

def user_login_req(f):
    # auth decorator
    @wraps(f)
    def wrapper(*args, **kwargs):
        if 'uid' not in session:
            flash('You must be logged in to view this page.', 'warning')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return wrapper

@user_bp.route('/dashboard')
@user_login_req
def dashboard():
    # main view
    db = get_db()
    active_res = db.execute(
        '''
        SELECT r.id as res_id, p.location_name, ps.id as spot_num, r.start_time
        FROM reservation r JOIN parking_spot ps ON r.spot_id = ps.id JOIN parking_lot p ON ps.lot_id = p.id
        WHERE r.user_id = ? AND r.end_time IS NULL
        ''', (session['uid'],)
    ).fetchone()
    
    active_res_fmt = None
    if active_res:
        active_res_fmt = dict(active_res)
        active_res_fmt['start_ist'] = format_ist(active_res['start_time'])

    lots_raw = db.execute("SELECT id, location_name, address, price_per_hour FROM parking_lot WHERE status = 'active'").fetchall()
    lots = []
    for lot in lots_raw:
        lot_dict = dict(lot)
        avail_spots = db.execute("SELECT COUNT(id) as count FROM parking_spot WHERE lot_id = ? AND status = 'A'", (lot['id'],)).fetchone()['count']
        lot_dict['avail_spots'] = avail_spots
        lots.append(lot_dict)
    db.close()
    return render_template('user/dashboard.html', lots=lots, active_res=active_res_fmt)

@user_bp.route('/book/<int:lot_id>', methods=['POST'])
@user_login_req
def book_spot(lot_id):
    # book first avail
    uid = session['uid']
    db = get_db()
    if db.execute('SELECT id FROM reservation WHERE user_id = ? AND end_time IS NULL', (uid,)).fetchone():
        flash('You already have an active parking session.', 'danger')
        db.close()
        return redirect(url_for('user.dashboard'))
    avail_spot = db.execute("SELECT id FROM parking_spot WHERE lot_id = ? AND status = 'A' ORDER BY id LIMIT 1", (lot_id,)).fetchone()
    if not avail_spot:
        flash('Sorry, this parking lot is full.', 'warning')
        db.close()
        return redirect(url_for('user.dashboard'))
    spot_id = avail_spot['id']
    db.execute("UPDATE parking_spot SET status = 'O' WHERE id = ?", (spot_id,))
    db.execute('INSERT INTO reservation (user_id, spot_id, start_time) VALUES (?, ?, ?)', (uid, spot_id, datetime.utcnow()))
    db.commit()
    db.close()
    flash('Spot reserved successfully!', 'success')
    return redirect(url_for('user.dashboard'))

@user_bp.route('/release/<int:res_id>', methods=['POST'])
@user_login_req
def release_spot(res_id):
    # end session
    db = get_db()
    res = db.execute('SELECT * FROM reservation WHERE id = ?', (res_id,)).fetchone()
    spot_id = res['spot_id']
    lot = db.execute('SELECT p.price_per_hour FROM parking_lot p JOIN parking_spot ps ON p.id = ps.lot_id WHERE ps.id = ?', (spot_id,)).fetchone()
    now = datetime.utcnow()
    start_time = datetime.strptime(res['start_time'], '%Y-%m-%d %H:%M:%S.%f')
    cost = ((now - start_time).total_seconds() / 3600) * lot['price_per_hour']
    db.execute('UPDATE reservation SET end_time = ?, total_cost = ? WHERE id = ?', (now, cost, res_id))
    db.execute("UPDATE parking_spot SET status = 'A' WHERE id = ?", (spot_id,))
    db.commit()
    db.close()
    flash(f'Spot released. Total cost:  ₹{cost:.2f}', 'info')
    return redirect(url_for('user.dashboard'))

@user_bp.route('/history')
@user_login_req
def history():
    # view past parks
    db = get_db()
    raw_history = db.execute(
        '''
        SELECT p.location_name, p.status as lot_status, r.start_time, r.end_time, r.total_cost
        FROM reservation r
        LEFT JOIN parking_spot ps ON r.spot_id = ps.id
        LEFT JOIN parking_lot p ON ps.lot_id = p.id
        WHERE r.user_id = ? AND r.end_time IS NOT NULL ORDER BY r.start_time DESC
        ''', (session['uid'],)
    ).fetchall()
    proc_history = []
    for item in raw_history:
        item_dict = dict(item)
        item_dict['duration'] = format_duration(item['start_time'], item['end_time'])
        item_dict['start_ist'] = format_ist(item['start_time'])
        item_dict['end_ist'] = format_ist(item['end_time'])
        proc_history.append(item_dict)
    db.close()
    return render_template('user/history.html', history=proc_history)