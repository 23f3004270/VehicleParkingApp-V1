from datetime import datetime
import pytz

IST = pytz.timezone('Asia/Kolkata')

def format_duration(start, end):
    # duration calc
    if not start or not end: return "N/A"
    try:
        start_dt = datetime.strptime(start, '%Y-%m-%d %H:%M:%S.%f')
        end_dt = datetime.strptime(end, '%Y-%m-%d %H:%M:%S.%f')
    except ValueError:
        start_dt = datetime.strptime(start, '%Y-%m-%d %H:%M:%S')
        end_dt = datetime.strptime(end, '%Y-%m-%d %H:%M:%S')

    delta = end_dt - start_dt
    hrs, rem = divmod(delta.seconds, 3600)
    mins, _ = divmod(rem, 60)

    if delta.days > 0: return f"{delta.days}d {hrs}h"
    if hrs > 0: return f"{hrs}h {mins}m"
    return f"{mins}m"

def format_ist(utc_dt_str):
    if not utc_dt_str: return "N/A"
    try:
        utc_dt = datetime.strptime(utc_dt_str, '%Y-%m-%d %H:%M:%S.%f')
    except ValueError:
        utc_dt = datetime.strptime(utc_dt_str, '%Y-%m-%d %H:%M:%S')
    
    utc_dt = pytz.utc.localize(utc_dt)
    ist_dt = utc_dt.astimezone(IST)
    return ist_dt.strftime('%b %d, %Y, %I:%M %p')