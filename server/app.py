import sqlite3
import json
import datetime
import os
import functools
from flask import Flask, render_template, request, jsonify, g, session, redirect, url_for

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'sgml_secret_key_fixed_2025')
DB_FILE = os.environ.get('DB_PATH', 'machines.db')

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DB_FILE)
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def init_db():
    with app.app_context():
        db = get_db()
        # Create table for machines
        db.execute('''
            CREATE TABLE IF NOT EXISTS machines (
                id TEXT PRIMARY KEY,
                hostname TEXT,
                ip TEXT,
                os_info TEXT,
                cpu_info TEXT,
                memory_info TEXT,
                disk_info TEXT,
                uptime REAL,
                last_seen TIMESTAMP,
                manufacturer TEXT,
                serial_number TEXT,
                geolocation TEXT,
                installed_software TEXT,
                metrics TEXT,
                user_info TEXT,
                pending_command TEXT
            )
        ''')
        # Simple migration: Add columns if not exists
        try:
            db.execute("ALTER TABLE machines ADD COLUMN user_info TEXT")
        except:
            pass
        try:
            db.execute("ALTER TABLE machines ADD COLUMN pending_command TEXT")
        except:
            pass
            
        db.commit()

@app.template_filter('from_json')
def from_json_filter(value):
    if value:
        try:
            return json.loads(value)
        except:
            return value
    return {}

@app.template_filter('format_uptime')
def format_uptime_filter(seconds):
    if seconds is None: return "N/A"
    return str(datetime.timedelta(seconds=int(seconds)))


# Auth Decorator
def login_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if session.get('user') is None:
            return redirect(url_for('login'))
        return view(**kwargs)
    return wrapped_view

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = request.form['username']
        pwd = request.form['password']
        
        # Hardcoded credentials as requested
        if user == 'gaspar' and pwd == '123!@#AS':
            session['user'] = user
            return redirect(url_for('index'))
        else:
            return render_template('login.html', error="Usuário ou senha incorretos")
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/')
@login_required
def index():
    db = get_db()
    cursor = db.execute('SELECT * FROM machines ORDER BY last_seen DESC')
    machines = cursor.fetchall()
    return render_template('dashboard.html', machines=machines)

@app.route('/machine/<id>')
@login_required
def machine_detail(id):
    db = get_db()
    cursor = db.execute('SELECT * FROM machines WHERE id = ?', (id,))
    machine = cursor.fetchone()
    if machine:
        return render_template('detail.html', machine=machine)
    return "Machine not found", 404

@app.route('/api/report', methods=['POST'])
def report():
    data = request.json
    db = get_db()
    
    # Extract core fields
    machine_id = data.get('uuid') or data.get('serial_number') or data.get('hostname')
    hostname = data.get('hostname')
    ip = data.get('ip')
    os_info = json.dumps(data.get('os'))
    cpu_info = json.dumps(data.get('cpu'))
    memory_info = json.dumps(data.get('memory'))
    disk_info = json.dumps(data.get('disk'))
    uptime = data.get('uptime')
    manufacturer = data.get('manufacturer')
    serial_number = data.get('serial_number')
    geolocation = json.dumps(data.get('geolocation'))
    installed_software = json.dumps(data.get('software'))
    metrics = json.dumps(data.get('metrics'))
    
    user_info = json.dumps(data.get('user_info'))
    
    now = datetime.datetime.now()
    
    db.execute('''
        INSERT INTO machines (id, hostname, ip, os_info, cpu_info, memory_info, disk_info, uptime, last_seen, manufacturer, serial_number, geolocation, installed_software, metrics, user_info)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            hostname=excluded.hostname,
            ip=excluded.ip,
            os_info=excluded.os_info,
            cpu_info=excluded.cpu_info,
            memory_info=excluded.memory_info,
            disk_info=excluded.disk_info,
            uptime=excluded.uptime,
            last_seen=excluded.last_seen,
            manufacturer=excluded.manufacturer,
            serial_number=excluded.serial_number,
            geolocation=excluded.geolocation,
            installed_software=excluded.installed_software,
            metrics=excluded.metrics,
            user_info=excluded.user_info
    ''', (machine_id, hostname, ip, os_info, cpu_info, memory_info, disk_info, uptime, now, manufacturer, serial_number, geolocation, installed_software, metrics, user_info))
    
    # Check for pending commands to send back to agent
    command = ""
    try:
        cur = db.execute("SELECT pending_command FROM machines WHERE id = ?", (machine_id,))
        row = cur.fetchone()
        if row and row['pending_command']:
            command = row['pending_command']
            # Clear command after sending
            db.execute("UPDATE machines SET pending_command = NULL WHERE id = ?", (machine_id,))
    except:
        pass

    db.commit()
    return jsonify({"status": "success", "message": "Data received", "command": command}), 200

# Ensure DB tables exist when running via Gunicorn
init_db()

@app.route('/machine/<machine_id>/action', methods=['POST'])
@login_required
def machine_action(machine_id):
    action = request.form.get('action')
    if action in ['restart', 'shutdown']:
        db = get_db()
        db.execute("UPDATE machines SET pending_command = ? WHERE id = ?", (action, machine_id))
        db.commit()
    return redirect(url_for('machine_detail', machine_id=machine_id))

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
