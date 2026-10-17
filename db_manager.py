import sqlite3
import os
import time

DB_PATH = os.path.join(os.path.dirname(__file__), "xonadon_plus.db")

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    # 1. Users Table (Fuqarolar va Haydovchilar)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        phone TEXT UNIQUE NOT NULL,
        full_name TEXT NOT NULL,
        role TEXT NOT NULL DEFAULT 'resident',
        region TEXT DEFAULT 'qashqadaryo',
        district TEXT DEFAULT 'nishon',
        mfy TEXT DEFAULT 'koksoy',
        street TEXT DEFAULT 'koksoy_markaziy',
        house_number TEXT DEFAULT '1-uy',
        pin_code TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # 2. Drivers Table (Admin ruxsat bergan haydovchilar)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS drivers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        phone TEXT UNIQUE NOT NULL,
        full_name TEXT NOT NULL,
        truck_model TEXT DEFAULT 'Isuzu NPR 75',
        truck_plate TEXT NOT NULL,
        truck_color TEXT DEFAULT 'Oq (Sariq chiziqli)',
        assigned_region TEXT DEFAULT 'qashqadaryo',
        assigned_district TEXT DEFAULT 'nishon',
        assigned_mfy TEXT DEFAULT 'koksoy',
        password TEXT NOT NULL DEFAULT 'gaz2026',
        is_active INTEGER DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # 3. Active Sessions Table (Real faol seanslar va qurilmalar)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS sessions (
        id TEXT PRIMARY KEY,
        phone TEXT NOT NULL,
        device_name TEXT NOT NULL,
        os_name TEXT NOT NULL,
        ip_address TEXT DEFAULT 'Tarmoqda',
        last_active_time INTEGER NOT NULL,
        is_active INTEGER DEFAULT 1
    );
    """)

    # 4. Driver Live Location & Tracking Table (Jonli GPS koordinatalari)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS driver_live (
        phone TEXT PRIMARY KEY,
        driver_name TEXT NOT NULL,
        truck_plate TEXT NOT NULL,
        truck_model TEXT DEFAULT 'Isuzu NPR 75',
        truck_color TEXT DEFAULT 'Oq (Sariq chiziqli)',
        status TEXT DEFAULT 'idle',
        stage TEXT DEFAULT 'collect',
        lat REAL DEFAULT 38.665,
        lng REAL DEFAULT 65.698,
        region TEXT DEFAULT 'qashqadaryo',
        district TEXT DEFAULT 'nishon',
        mfy TEXT DEFAULT 'koksoy',
        street TEXT DEFAULT 'koksoy_markaziy',
        street_name TEXT DEFAULT 'Ko‘ksoy markaziy ko‘chasi',
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # 5. OTP Codes Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS otp_codes (
        phone TEXT PRIMARY KEY,
        code TEXT NOT NULL,
        expires_at INTEGER NOT NULL
    );
    """)

    # 6. Admin IDs Table (Telegram Bot Adminlari)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS bot_admins (
        chat_id INTEGER PRIMARY KEY,
        full_name TEXT,
        username TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # Insert default initial data if empty
    cursor.execute("SELECT COUNT(*) as cnt FROM users;")
    if cursor.fetchone()["cnt"] == 0:
        cursor.execute("""
        INSERT INTO users (phone, full_name, role, region, district, mfy, street, house_number)
        VALUES 
        ('+998940401009', 'Rustam Abdullayev', 'resident', 'qashqadaryo', 'nishon', 'koksoy', 'koksoy_markaziy', '12-uy'),
        ('+998901234567', 'Islomov Javohir', 'driver', 'qashqadaryo', 'nishon', 'koksoy', 'koksoy_markaziy', '1-uy');
        """)

    cursor.execute("SELECT COUNT(*) as cnt FROM drivers;")
    if cursor.fetchone()["cnt"] == 0:
        cursor.execute("""
        INSERT INTO drivers (phone, full_name, truck_model, truck_plate, truck_color, assigned_region, assigned_district, assigned_mfy, password)
        VALUES 
        ('+998901234567', 'Islomov Javohir', 'Isuzu NPR 75', '30 782 AGA', 'Oq (Sariq chiziqli)', 'qashqadaryo', 'nishon', 'koksoy', 'gaz2026'),
        ('+998940401009', 'Ahror Suyunov', 'Isuzu NPR 75', '70 M 260 EB', 'Oq (Sariq chiziqli)', 'qashqadaryo', 'nishon', 'koksoy', 'ahrorbek2005');
        """)
        cursor.execute("""
        INSERT OR REPLACE INTO driver_live (phone, driver_name, truck_plate, truck_model, truck_color, status, stage, lat, lng, region, district, mfy, street, street_name)
        VALUES 
        ('+998901234567', 'Islomov Javohir', '30 782 AGA', 'Isuzu NPR 75', 'Oq (Sariq chiziqli)', 'working', 'collect', 38.665, 65.698, 'qashqadaryo', 'nishon', 'koksoy', 'koksoy_markaziy', 'Ko‘ksoy markaziy ko‘chasi'),
        ('+998940401009', 'Ahror Suyunov', '70 M 260 EB', 'Isuzu NPR 75', 'Oq (Sariq chiziqli)', 'working', 'collect', 38.665, 65.698, 'qashqadaryo', 'nishon', 'koksoy', 'koksoy_markaziy', 'Ko‘ksoy markaziy ko‘chasi');
        """)

    conn.commit()
    conn.close()
    print("Database initialized successfully at:", DB_PATH)


# --- USER FUNCTIONS ---
def register_user(phone, full_name, role='resident', region='qashqadaryo', district='nishon', mfy='koksoy', street='koksoy_markaziy', house_number='1-uy'):
    clean_p = phone.strip()
    conn = get_connection()
    c = conn.cursor()
    # Check if exists
    c.execute("SELECT * FROM users WHERE phone = ?", (clean_p,))
    row = c.fetchone()
    if row:
        conn.close()
        return {"ok": False, "exists": True, "message": "Ushbu telefon raqam allaqachon ro‘yxatdan o‘tgan!"}

    c.execute("""
    INSERT INTO users (phone, full_name, role, region, district, mfy, street, house_number)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (clean_p, full_name, role, region, district, mfy, street, house_number))
    conn.commit()
    user_id = c.lastrowid
    conn.close()
    return {
        "ok": True,
        "user": {
            "id": user_id,
            "phone": clean_p,
            "full_name": full_name,
            "role": role,
            "region": region,
            "district": district,
            "mfy": mfy,
            "street": street,
            "house_number": house_number
        }
    }

def get_user_by_phone(phone):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE phone = ?", (phone.strip(),))
    row = c.fetchone()
    conn.close()
    return dict(row) if row else None


# --- DRIVER FUNCTIONS ---
def add_driver(phone, full_name, truck_plate, password='gaz2026', truck_model='Isuzu NPR 75', truck_color='Oq (Sariq chiziqli)', assigned_region='qashqadaryo', assigned_district='nishon', assigned_mfy='koksoy'):
    clean_p = phone.strip()
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
    INSERT OR REPLACE INTO drivers (phone, full_name, truck_model, truck_plate, truck_color, assigned_region, assigned_district, assigned_mfy, password, is_active)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
    """, (clean_p, full_name, truck_model, truck_plate, truck_color, assigned_region, assigned_district, assigned_mfy, password))
    
    # Also ensure user table has driver role
    c.execute("""
    INSERT OR REPLACE INTO users (phone, full_name, role, region, district, mfy)
    VALUES (?, ?, 'driver', ?, ?, ?)
    """, (clean_p, full_name, assigned_region, assigned_district, assigned_mfy))

    # Also register in driver_live
    c.execute("""
    INSERT OR REPLACE INTO driver_live (phone, driver_name, truck_plate, truck_model, truck_color, status, stage, lat, lng, region, district, mfy)
    VALUES (?, ?, ?, ?, ?, 'idle', 'collect', 38.665, 65.698, ?, ?, ?)
    """, (clean_p, full_name, truck_plate, truck_model, truck_color, assigned_region, assigned_district, assigned_mfy))

    conn.commit()
    conn.close()
    return {"ok": True, "message": f"Haydovchi {full_name} ({truck_plate}) muvaffaqiyatli qo‘shildi!"}

def get_driver_by_phone(phone):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM drivers WHERE phone = ? AND is_active = 1", (phone.strip(),))
    row = c.fetchone()
    conn.close()
    return dict(row) if row else None

def get_all_drivers():
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM drivers ORDER BY id DESC")
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def delete_driver(phone):
    conn = get_connection()
    c = conn.cursor()
    c.execute("DELETE FROM drivers WHERE phone = ?", (phone.strip(),))
    c.execute("DELETE FROM driver_live WHERE phone = ?", (phone.strip(),))
    conn.commit()
    conn.close()
    return True


# --- SESSIONS FUNCTIONS ---
def update_or_create_session(device_id, phone, device_name, os_name, ip_address='Tarmoqda'):
    conn = get_connection()
    c = conn.cursor()
    now = int(time.time() * 1000)
    c.execute("""
    INSERT OR REPLACE INTO sessions (id, phone, device_name, os_name, ip_address, last_active_time, is_active)
    VALUES (?, ?, ?, ?, ?, ?, 1)
    """, (device_id, phone.strip(), device_name, os_name, ip_address, now))
    conn.commit()
    conn.close()

def check_session_active(device_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT is_active FROM sessions WHERE id = ?", (device_id,))
    row = c.fetchone()
    conn.close()
    if row is None:
        return True # Default to active if not recorded
    return bool(row["is_active"])

def get_user_sessions(phone):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM sessions WHERE phone = ? AND is_active = 1 ORDER BY last_active_time DESC", (phone.strip(),))
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def terminate_session(device_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("UPDATE sessions SET is_active = 0 WHERE id = ?", (device_id,))
    conn.commit()
    conn.close()
    return True

def terminate_other_sessions(phone, current_device_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("UPDATE sessions SET is_active = 0 WHERE phone = ? AND id != ?", (phone.strip(), current_device_id))
    conn.commit()
    conn.close()
    return True


# --- DRIVER LIVE TRACKING ---
def update_driver_location(phone, lat, lng, status=None, stage=None, street=None, street_name=None):
    conn = get_connection()
    c = conn.cursor()
    updates = ["lat = ?, lng = ?, updated_at = CURRENT_TIMESTAMP"]
    params = [float(lat), float(lng)]
    if status:
        updates.append("status = ?")
        params.append(status)
    if stage:
        updates.append("stage = ?")
        params.append(stage)
    if street:
        updates.append("street = ?")
        params.append(street)
    if street_name:
        updates.append("street_name = ?")
        params.append(street_name)
    params.append(phone.strip())

    c.execute(f"UPDATE driver_live SET {', '.join(updates)} WHERE phone = ?", tuple(params))
    conn.commit()
    conn.close()

def get_live_driver(mfy='koksoy'):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM driver_live WHERE mfy = ? ORDER BY updated_at DESC LIMIT 1", (mfy,))
    row = c.fetchone()
    conn.close()
    return dict(row) if row else None


# --- BOT ADMINS ---
def add_bot_admin(chat_id, full_name="", username=""):
    conn = get_connection()
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO bot_admins (chat_id, full_name, username) VALUES (?, ?, ?)", (chat_id, full_name, username))
    conn.commit()
    conn.close()

def is_bot_admin(chat_id):
    # Strictly anchor ID 1838588800 as the sole owner admin
    if str(chat_id) == "1838588800" or chat_id == 1838588800:
        return True
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT chat_id FROM bot_admins WHERE chat_id = ?", (chat_id,))
    row = c.fetchone()
    conn.close()
    return bool(row)


# --- TWO-STEP VERIFICATION (2FA - TELEGRAM USLUBIDA KALIT SO'Z) ---
def set_user_2fa(phone, password, hint=""):
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
    UPDATE users SET two_step_password = ?, two_step_hint = ? WHERE phone = ?
    """, (password.strip(), hint.strip(), phone.strip()))
    conn.commit()
    conn.close()
    return {"ok": True, "message": "Ikki bosqichli kalit so‘z muvaffaqiyatli saqlandi!"}

def get_user_2fa_status(phone):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT two_step_password, two_step_hint FROM users WHERE phone = ?", (phone.strip(),))
    row = c.fetchone()
    conn.close()
    if row and row["two_step_password"]:
        return {"has_2fa": True, "hint": row["two_step_hint"] or ""}
    return {"has_2fa": False, "hint": ""}

def verify_user_2fa(phone, password):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT two_step_password FROM users WHERE phone = ?", (phone.strip(),))
    row = c.fetchone()
    conn.close()
    if not row or not row["two_step_password"]:
        return True # 2FA not set
    return row["two_step_password"] == password.strip()

def get_all_bot_admins():
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT chat_id FROM bot_admins")
    rows = c.fetchall()
    conn.close()
    return [r["chat_id"] for r in rows]

if __name__ == "__main__":
    init_db()


# --- OTP VERIFICATION ---
def set_otp(phone, code, expire_secs=300):
    clean_p = re.sub(r'\D', '', phone)
    expires_at = int(time.time()) + expire_secs
    conn = get_connection()
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO otp_codes (phone, code, expires_at) VALUES (?, ?, ?)", (clean_p, str(code).strip(), expires_at))
    conn.commit()
    conn.close()

def verify_otp(phone, code):
    clean_p = re.sub(r'\D', '', phone)
    now = int(time.time())
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT code, expires_at FROM otp_codes WHERE phone = ?", (clean_p,))
    row = c.fetchone()
    conn.close()
    if not row:
        return False
    if row["expires_at"] < now:
        return False
    return str(row["code"]).strip() == str(code).strip()
