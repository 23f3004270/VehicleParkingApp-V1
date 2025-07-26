from flask import Blueprint, render_template, request, redirect, url_for, session, flash
import sqlite3
from functools import wraps
from datetime import datetime

DB_FILE = 'parkezily.db'

user_bp = Blueprint('user', __name__, template_folder='templates')

def get_db():
    # db connect
    db = sqlite3.connect(DB_FILE)
    db.row_factory = sqlite3.Row
    return db

def user_login_req(f):
    # decorator check
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
    # main user view
    uid = session['uid']
    db = get_db()
    
    # check active park
    active_res = db.execute(
        '''
        SELECT r.id as res_id, p.location_name, ps.id as spot_num, r.start_time
        FROM reservation r
        JOIN parking_spot ps ON r.spot_id = ps.id
        JOIN parking_lot p ON ps.lot_id = p.id
        WHERE r.user_id = ? AND r.end_time IS NULL
        ''', (uid,)
    ).fetchone()

    # get all lots
    lots_raw = db.execute('SELECT id, location_name, address, price_per_hour FROM parking_lot').fetchall()
    
    # get spot counts
    lots = []
    for lot in lots_raw:
        lot_dict = dict(lot)
        avail_spots = db.execute(
            "SELECT COUNT(id) as count FROM parking_spot WHERE lot_id = ? AND status = 'A'", (lot['id'],)
        ).fetchone()['count']
        lot_dict['avail_spots'] = avail_spots
        lots.append(lot_dict)

    db.close()
    return render_template('user/dashboard.html', lots=lots, active_res=active_res)

@user_bp.route('/book/<int:lot_id>', methods=['POST'])
@user_login_req
def book_spot(lot_id):
    # book first avail
    uid = session['uid']
    db = get_db()

    # check existing
    existing = db.execute('SELECT id FROM reservation WHERE user_id = ? AND end_time IS NULL', (uid,)).fetchone()
    if existing:
        flash('You already have an active parking session.', 'danger')
        db.close()
        return redirect(url_for('user.dashboard'))

    # find spot
    avail_spot = db.execute(
        "SELECT id FROM parking_spot WHERE lot_id = ? AND status = 'A' ORDER BY id LIMIT 1", (lot_id,)
    ).fetchone()

    if not avail_spot:
        flash('Sorry, this parking lot is full.', 'warning')
        db.close()
        return redirect(url_for('user.dashboard'))

    spot_id = avail_spot['id']
    
    # occupy spot
    db.execute("UPDATE parking_spot SET status = 'O' WHERE id = ?", (spot_id,))
    
    # create reservation
    now = datetime.utcnow()
    db.execute(
        'INSERT INTO reservation (user_id, spot_id, start_time) VALUES (?, ?, ?)',
        (uid, spot_id, now)
    )
    
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
    
    # get lot price
    lot = db.execute(
        '''
        SELECT p.price_per_hour FROM parking_lot p
        JOIN parking_spot ps ON p.id = ps.lot_id
        WHERE ps.id = ?
        ''', (spot_id,)
    ).fetchone()
    
    # calc cost
    now = datetime.utcnow()
    start_time = datetime.strptime(res['start_time'], '%Y-%m-%d %H:%M:%S.%f')
    duration_secs = (now - start_time).total_seconds()
    duration_hrs = duration_secs / 3600
    cost = duration_hrs * lot['price_per_hour']

    # update records
    db.execute(
        'UPDATE reservation SET end_time = ?, total_cost = ? WHERE id = ?',
        (now, cost, res_id)
    )
    db.execute("UPDATE parking_spot SET status = 'A' WHERE id = ?", (spot_id,))
    
    db.commit()
    db.close()
    flash(f'Spot released. Total cost: ${cost:.2f}', 'info')
    return redirect(url_for('user.dashboard'))

@user_bp.route('/history')
@user_login_req
def format_duration(start, end):
    # duration helper
    if not end:
        return "N/A"
    start_dt = datetime.strptime(start, '%Y-%m-%d %H:%M:%S.%f')
    end_dt = datetime.strptime(end, '%Y-%m-%d %H:%M:%S.%f')
    delta = end_dt - start_dt
    
    hrs, rem = divmod(delta.seconds, 3600)
    mins, secs = divmod(rem, 60)
    
    if hrs > 0:
        return f"{hrs}h {mins}m"
    elif mins > 0:
        return f"{mins}m {secs}s"
    return f"{secs}s"

@user_bp.route('/history')
@user_login_req
def history():
    # view past parks
    uid = session['uid']
    db = get_db()
    
    raw_history = db.execute(
        '''
        SELECT p.location_name, r.start_time, r.end_time, r.total_cost
        FROM reservation r
        JOIN parking_spot ps ON r.spot_id = ps.id
        JOIN parking_lot p ON ps.lot_id = p.id
        WHERE r.user_id = ? AND r.end_time IS NOT NULL
        ORDER BY r.start_time DESC
        ''', (uid,)
    ).fetchall()
    
    # process history
    processed_history = []
    for item in raw_history:
        item_dict = dict(item)
        item_dict['duration'] = format_duration(item['start_time'], item['end_time'])
        processed_history.append(item_dict)
    
    db.close()
    return render_template('user/history.html', history=processed_history)