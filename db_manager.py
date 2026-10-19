import random
import sqlite3
import os
import time
import re
import json

DB_PATH = os.path.join(os.path.dirname(__file__), "xonadon_plus.db")

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def ensure_db_columns():
    conn = get_connection()
    c = conn.cursor()
    migrations = [
        ("drivers", "avatar_url", "TEXT DEFAULT ''"),
        ("drivers", "account_id", "TEXT DEFAULT ''"),
        ("driver_live", "avatar_url", "TEXT DEFAULT ''"),
        ("users", "avatar_url", "TEXT DEFAULT ''"),
        ("users", "account_id", "TEXT DEFAULT ''")
    ]
    for table, col, col_type in migrations:
        try:
            c.execute(f"ALTER TABLE {table} ADD COLUMN {col} {col_type}")
        except Exception:
            pass
    conn.commit()
    conn.close()

# Auto-run migration whenever module is loaded
try:
    ensure_db_columns()
except Exception as _e:
    pass

def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    # 1. Users Table (Fuqarolar va Haydovchilar)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS user_avatars (
        phone_clean TEXT PRIMARY KEY,
        full_phone TEXT,
        role TEXT,
        avatar_url TEXT,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

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
    # To'liq toza tizim - hech qanday mock yoki sinov fuqarolari kiritilmaydi
    pass

    # Clean up any lingering mock seed drivers
    try:
        cursor.execute("DELETE FROM drivers WHERE phone LIKE '%901234567%' OR truck_plate LIKE '%30 782 AGA%';")
        cursor.execute("DELETE FROM driver_live WHERE phone LIKE '%901234567%' OR truck_plate LIKE '%30 782 AGA%';")
    except Exception:
        pass

    # Foydalanuvchi talabiga ko'ra barcha eski mashina, haydovchi va 2FA ma'lumotlarini tozalash
    try:
        cursor.execute("DELETE FROM drivers;")
        cursor.execute("DELETE FROM driver_live;")
        cursor.execute("UPDATE users SET two_step_password = NULL, two_step_hint = NULL;")
        cursor.execute("DELETE FROM sessions;"); cursor.execute("DELETE FROM user_avatars;"); cursor.execute("DELETE FROM users;")
    except Exception as _we:
        pass

    try:
        cursor.execute("ALTER TABLE drivers ADD COLUMN account_id TEXT;")
    except Exception:
        pass
    try:
        cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_drivers_account_id ON drivers(account_id);")
    except Exception:
        pass

    conn.commit()
    conn.close()
    print("Database initialized successfully at:", DB_PATH)



def generate_unique_account_id(prefix="XP-"):
    conn = get_connection()
    c = conn.cursor()
    for _ in range(1000):
        rand_num = random.randint(100000, 999999)
        candidate = f"{prefix}{rand_num}"
        c.execute("SELECT 1 FROM users WHERE account_id = ?", (candidate,))
        if not c.fetchone():
            c.execute("SELECT 1 FROM drivers WHERE account_id = ?", (candidate,))
            if not c.fetchone():
                conn.close()
                return candidate
    conn.close()
    return f"{prefix}{int(time.time() * 1000) % 1000000:06d}"

# --- USER FUNCTIONS ---
def register_user(phone, full_name, role='resident', region='qashqadaryo', district='nishon', mfy='koksoy', street='koksoy_markaziy', house_number='1-uy'):
    clean_p = phone.strip()
    conn = get_connection()
    c = conn.cursor()
    # Check if exists
    c.execute("SELECT * FROM users WHERE phone = ?", (clean_p,))
    row = c.fetchone()
    if row:
        u_dict = dict(row)
        if not u_dict.get("account_id"):
            acc_id = generate_unique_account_id("XP-")
            c.execute("UPDATE users SET account_id = ? WHERE phone = ?", (acc_id, clean_p))
            conn.commit()
            u_dict["account_id"] = acc_id
        conn.close()
        return {"ok": True, "exists": True, "user": u_dict}

    account_id = generate_unique_account_id("XP-")
    c.execute("""
    INSERT INTO users (phone, full_name, role, region, district, mfy, street, house_number, account_id)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (clean_p, full_name, role, region, district, mfy, street, house_number, account_id))
    conn.commit()
    user_id = c.lastrowid
    conn.close()
    return {
        "ok": True,
        "user": {
            "id": user_id,
            "account_id": account_id,
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
    if not row:
        clean_p = re.sub(r'\D', '', phone)
        c.execute("SELECT * FROM users WHERE phone LIKE ?", (f"%{clean_p[-9:]}%",))
        row = c.fetchone()
    if not row:
        conn.close()
        return None
    user_dict = dict(row)
    if not user_dict.get("account_id"):
        acc_id = generate_unique_account_id("XP-")
        c.execute("UPDATE users SET account_id = ? WHERE id = ?", (acc_id, user_dict["id"]))
        conn.commit()
        user_dict["account_id"] = acc_id
    conn.close()
    return user_dict


# --- DRIVER FUNCTIONS ---
def add_driver(phone, full_name, truck_plate, password='gaz2026', truck_model='Isuzu NPR 75', truck_color='Oq (Sariq chiziqli)', assigned_region='qashqadaryo', assigned_district='nishon', assigned_mfy='koksoy'):
    clean_p = phone.strip()
    conn = get_connection()
    c = conn.cursor()

    c.execute("SELECT account_id FROM drivers WHERE phone = ?", (clean_p,))
    row = c.fetchone()
    account_id = row["account_id"] if row and row["account_id"] else generate_unique_account_id("XP-")

    c.execute("""
    INSERT OR REPLACE INTO drivers (phone, full_name, truck_model, truck_plate, truck_color, assigned_region, assigned_district, assigned_mfy, password, account_id, is_active)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
    """, (clean_p, full_name, truck_model, truck_plate, truck_color, assigned_region, assigned_district, assigned_mfy, password, account_id))
    
    # Also ensure user table has driver role and same account_id
    c.execute("""
    INSERT OR REPLACE INTO users (phone, full_name, role, region, district, mfy, account_id, two_step_password, two_step_hint)
    VALUES (?, ?, 'driver', ?, ?, ?, ?, NULL, NULL)
    """, (clean_p, full_name, assigned_region, assigned_district, assigned_mfy, account_id))
    c.execute("UPDATE users SET two_step_password = NULL, two_step_hint = NULL WHERE phone = ? OR phone LIKE ?", (clean_p, f"%{clean_p[-9:]}%"))

    # Also register in driver_live
    c.execute("""
    INSERT OR REPLACE INTO driver_live (phone, driver_name, truck_plate, truck_model, truck_color, status, stage, lat, lng, region, district, mfy)
    VALUES (?, ?, ?, ?, ?, 'arrived', 'collect', 38.665, 65.698, ?, ?, ?)
    """, (clean_p, full_name, truck_plate, truck_model, truck_color, assigned_region, assigned_district, assigned_mfy))

    conn.commit()
    conn.close()
    return {"ok": True, "account_id": account_id, "message": f"Haydovchi {full_name} ({truck_plate}) muvaffaqiyatli qo‘shildi!"}

def get_driver_by_phone(phone):
    conn = get_connection()
    c = conn.cursor()
    raw = str(phone or '').strip()
    digits = re.sub(r'\D', '', raw)
    last9 = digits[-9:] if len(digits) >= 9 else digits
    c.execute("SELECT * FROM drivers WHERE (phone = ? OR phone LIKE ? OR phone LIKE ?) AND is_active = 1", (raw, f"%{last9}%", f"%{digits}%"))
    row = c.fetchone()
    conn.close()
    return dict(row) if row else None

def get_all_drivers():
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM drivers WHERE is_active = 1 ORDER BY id DESC")
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def is_driver_deleted(phone):
    # Blacklist yo'q: shunchaki drivers jadvalida mavjud yoki mavjud emasligi tekshiriladi
    if not phone:
        return False
    driver = get_driver_by_phone(phone)
    return driver is None

def clear_all_drivers_and_trucks():
    conn = get_connection()
    c = conn.cursor()
    c.execute("DELETE FROM drivers")
    c.execute("DELETE FROM driver_live")
    c.execute("DELETE FROM users WHERE role = 'driver'")
    c.execute("UPDATE users SET two_step_password = NULL, two_step_hint = NULL")
    c.execute("DELETE FROM sessions")
    conn.commit()
    conn.close()
    return True

def delete_driver(phone):
    conn = get_connection()
    c = conn.cursor()
    raw = str(phone or '').strip()
    digits = re.sub(r'\D', '', raw)
    last9 = digits[-9:] if len(digits) >= 9 else digits
    pattern_last9 = f"%{last9}%"
    pattern_digits = f"%{digits}%"

    # 1. Delete from drivers table
    c.execute("DELETE FROM drivers WHERE phone = ? OR phone LIKE ? OR phone LIKE ?", (raw, pattern_last9, pattern_digits))

    # 2. Delete from driver_live table
    c.execute("DELETE FROM driver_live WHERE phone = ? OR phone LIKE ? OR phone LIKE ?", (raw, pattern_last9, pattern_digits))

    # 3. Delete from users table (including 2FA password, 2FA hint, and account_id)
    c.execute("DELETE FROM users WHERE phone = ? OR phone LIKE ? OR phone LIKE ?", (raw, pattern_last9, pattern_digits))

    # 4. Terminate and delete all sessions immediately
    c.execute("DELETE FROM sessions WHERE phone = ? OR phone LIKE ? OR phone LIKE ?", (raw, pattern_last9, pattern_digits))

    # 5. Delete uploaded avatars
    try:
        c.execute("DELETE FROM avatars WHERE phone = ? OR phone LIKE ? OR phone LIKE ?", (raw, pattern_last9, pattern_digits))
    except Exception:
        pass

    # No blacklist: barcha ma'lumotlar o'chiriladi, admin xohlagan payt qayta qo'shishi mumkin

    conn.commit()
    conn.close()
    return True


# --- SESSIONS FUNCTIONS ---
def update_or_create_session(device_id, phone, device_name, os_name, ip_address='Tarmoqda'):
    conn = get_connection()
    c = conn.cursor()
    now = int(time.time() * 1000)
    clean_p = re.sub(r'\D', '', str(phone or ''))
    c.execute("""
    INSERT OR REPLACE INTO sessions (id, phone, device_name, os_name, ip_address, last_active_time, is_active)
    VALUES (?, ?, ?, ?, ?, ?, 1)
    """, (device_id, clean_p, device_name, os_name, ip_address, now))
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
    clean_p = re.sub(r'\D', '', str(phone or ''))
    c.execute("SELECT * FROM sessions WHERE (phone = ? OR phone = ?) AND is_active = 1 ORDER BY last_active_time DESC", (clean_p, '+' + clean_p))
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
    clean_p = re.sub(r'\D', '', str(phone or ''))
    c.execute("UPDATE sessions SET is_active = 0 WHERE (phone = ? OR phone = ?) AND id != ?", (clean_p, '+' + clean_p, current_device_id))
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
    clean_p = re.sub(r'\D', '', phone)
    last9 = clean_p[-9:] if len(clean_p) >= 9 else clean_p
    conn = get_connection()
    c = conn.cursor()
    # Ensure drivers table has columns
    try:
        c.execute("ALTER TABLE drivers ADD COLUMN two_step_password TEXT")
    except Exception:
        pass
    try:
        c.execute("ALTER TABLE drivers ADD COLUMN two_step_hint TEXT")
    except Exception:
        pass
    
    # Update users
    c.execute("SELECT id FROM users WHERE phone LIKE ?", (f"%{last9}%",))
    u = c.fetchone()
    if u:
        c.execute("UPDATE users SET two_step_password = ?, two_step_hint = ? WHERE phone LIKE ?", 
                  (password.strip(), hint.strip(), f"%{last9}%"))
    else:
        c.execute("INSERT INTO users (phone, full_name, role, two_step_password, two_step_hint) VALUES (?, ?, 'driver', ?, ?)",
                  (f"+998{last9}", "Haydovchi", password.strip(), hint.strip()))
    
    # Also update drivers table
    try:
        c.execute("UPDATE drivers SET two_step_password = ?, two_step_hint = ? WHERE phone LIKE ?",
                  (password.strip(), hint.strip(), f"%{last9}%"))
    except Exception:
        pass
    conn.commit()
    conn.close()
    return {"ok": True, "message": "Ikki bosqichli kalit so‘z muvaffaqiyatli saqlandi!"}

def get_user_2fa_status(phone):
    clean_p = re.sub(r'\D', '', phone)
    last9 = clean_p[-9:] if len(clean_p) >= 9 else clean_p
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT two_step_password, two_step_hint FROM users WHERE phone LIKE ?", (f"%{last9}%",))
    row = c.fetchone()
    if not row or not row["two_step_password"]:
        try:
            c.execute("SELECT two_step_password, two_step_hint FROM drivers WHERE phone LIKE ?", (f"%{last9}%",))
            row = c.fetchone()
        except Exception:
            pass
    conn.close()
    if row and row["two_step_password"]:
        return {"has_2fa": True, "hint": row["two_step_hint"] or ""}
    return {"has_2fa": False, "hint": ""}

def verify_user_2fa(phone, password):
    clean_p = re.sub(r'\D', '', phone)
    last9 = clean_p[-9:] if len(clean_p) >= 9 else clean_p
    status = get_user_2fa_status(phone)
    if not status.get("has_2fa"):
        return True
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT two_step_password FROM users WHERE phone LIKE ?", (f"%{last9}%",))
    row = c.fetchone()
    if not row or not row["two_step_password"]:
        try:
            c.execute("SELECT two_step_password FROM drivers WHERE phone LIKE ?", (f"%{last9}%",))
            row = c.fetchone()
        except Exception:
            pass
    conn.close()
    if not row or not row["two_step_password"]:
        return True
    return str(row["two_step_password"]).strip() == str(password).strip()

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

# --- AVATAR & ACTIVE TRUCKS FUNCTIONS ---
def save_user_avatar(phone, role, avatar_url):
    conn = get_connection()
    c = conn.cursor()
    clean_p = re.sub(r'\D', '', str(phone or ''))
    if not clean_p:
        conn.close()
        return False
        
    c.execute("""
        CREATE TABLE IF NOT EXISTS user_avatars (
            phone_clean TEXT PRIMARY KEY,
            full_phone TEXT,
            role TEXT,
            avatar_url TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    c.execute("""
        INSERT OR REPLACE INTO user_avatars (phone_clean, full_phone, role, avatar_url, updated_at)
        VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
    """, (clean_p[-9:], phone, role, avatar_url))

    if role == 'driver':
        c.execute("UPDATE drivers SET avatar_url = ? WHERE phone LIKE ?", (avatar_url, f"%{clean_p[-9:]}%"))
        c.execute("UPDATE driver_live SET updated_at = CURRENT_TIMESTAMP WHERE phone LIKE ?", (f"%{clean_p[-9:]}%",))
    else:
        c.execute("UPDATE users SET avatar_url = ? WHERE phone LIKE ?", (avatar_url, f"%{clean_p[-9:]}%"))
    conn.commit()
    conn.close()
    return True

def get_user_avatar(phone, role='resident'):
    conn = get_connection()
    c = conn.cursor()
    clean_p = re.sub(r'\D', '', str(phone or ''))
    if len(clean_p) < 9:
        conn.close()
        return ""
    
    # 1. Check dedicated user_avatars table first
    try:
        c.execute("SELECT avatar_url FROM user_avatars WHERE phone_clean = ?", (clean_p[-9:],))
        row = c.fetchone()
        if row and row["avatar_url"]:
            conn.close()
            return row["avatar_url"]
    except Exception:
        pass

    # 2. Check drivers table if driver
    if role == 'driver':
        c.execute("SELECT avatar_url FROM drivers WHERE phone LIKE ?", (f"%{clean_p[-9:]}%",))
        row = c.fetchone()
        if row and row["avatar_url"]:
            conn.close()
            return row["avatar_url"]

    # 3. Check users table
    c.execute("SELECT avatar_url FROM users WHERE phone LIKE ?", (f"%{clean_p[-9:]}%",))
    row = c.fetchone()
    if row and row["avatar_url"]:
        conn.close()
        return row["avatar_url"]

    conn.close()
    return ""

def upsert_driver_live(phone, driver_name, truck_plate, truck_model, truck_color, status, stage, lat, lng, region, district, mfy, street, street_name, avatar_url=""):
    conn = get_connection()
    c = conn.cursor()
    clean_p = re.sub(r'\D', '', str(phone or ''))
    
    # Check if driver deactivated by admin
    c.execute("SELECT is_active, avatar_url FROM drivers WHERE phone LIKE ?", (f"%{clean_p[-9:]}%",))
    drv_row = c.fetchone()
    if drv_row and drv_row["is_active"] == 0:
        conn.close()
        return False
        
    final_avatar = avatar_url or (drv_row["avatar_url"] if drv_row else "") or ""
    
    c.execute("""
        INSERT OR REPLACE INTO driver_live 
        (phone, driver_name, truck_plate, truck_model, truck_color, status, stage, lat, lng, region, district, mfy, street, street_name, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
    """, (phone, driver_name, truck_plate, truck_model, truck_color, status, stage, float(lat), float(lng), region, district, mfy, street, street_name))
    
    c.execute("""
        UPDATE drivers 
        SET full_name = COALESCE(NULLIF(?, ''), full_name),
            truck_plate = COALESCE(NULLIF(?, ''), truck_plate),
            truck_model = COALESCE(NULLIF(?, ''), truck_model),
            truck_color = COALESCE(NULLIF(?, ''), truck_color),
            assigned_mfy = COALESCE(NULLIF(?, ''), assigned_mfy),
            assigned_district = COALESCE(NULLIF(?, ''), assigned_district),
            assigned_region = COALESCE(NULLIF(?, ''), assigned_region)
        WHERE phone LIKE ?
    """, (driver_name, truck_plate, truck_model, truck_color, mfy, district, region, f"%{clean_p[-9:]}%"))
                  
    conn.commit()
    conn.close()
    return True

def get_active_trucks(region=None, district=None, mfy=None):
    conn = get_connection()
    c = conn.cursor()
    
    def norm(s):
        return re.sub(r'[^a-zA-Z0-9]', '', str(s or '')).lower()
        
    target_mfy = norm(mfy)
    target_dist = norm(district)
    target_reg = norm(region)
    
    c.execute("""
        SELECT d.phone, 
               COALESCE(NULLIF(l.driver_name, ''), d.full_name) as full_name, 
               COALESCE(NULLIF(l.truck_model, ''), d.truck_model) as truck_model, 
               COALESCE(NULLIF(l.truck_plate, ''), d.truck_plate) as truck_plate, 
               COALESCE(NULLIF(l.truck_color, ''), d.truck_color) as truck_color,
               d.assigned_region, d.assigned_district, d.assigned_mfy, d.avatar_url,
               COALESCE(l.lat, 38.685) as lat,
               COALESCE(l.lng, 65.680) as lng,
               COALESCE(l.status, 'arrived') as status,
               COALESCE(l.stage, 'collect') as stage,
               COALESCE(l.street, 'istiqlol') as street,
               COALESCE(l.street_name, 'Istiqlol ko‘chasi') as street_name,
               COALESCE(l.mfy, d.assigned_mfy) as live_mfy,
               COALESCE(l.district, d.assigned_district) as live_dist,
               COALESCE(l.region, d.assigned_region) as live_reg,
               l.updated_at
        FROM drivers d
        LEFT JOIN driver_live l ON (d.phone = l.phone OR l.phone LIKE '%' || SUBSTR(REPLACE(REPLACE(d.phone, '+', ''), ' ', ''), -9))
        WHERE d.is_active = 1
    """)
    rows = c.fetchall()
    conn.close()
    
    results = []
    seen_plates = set()
    for r in rows:
        d = dict(r)
        
        # Strictly hide any driver in waiting / idle / paused / stopped / kutish mode
        st_lower = str(d.get('status', '')).strip().lower()
        if st_lower in ['waiting', 'idle', 'paused', 'stopped', 'kutish']:
            continue
        if not st_lower:
            d['status'] = 'arrived'
            
        cur_mfy = norm(d.get('live_mfy') or d.get('assigned_mfy'))
        cur_dist = norm(d.get('live_dist') or d.get('assigned_district'))
        cur_reg = norm(d.get('live_reg') or d.get('assigned_region'))
        
        # MFY filter
        if target_mfy and cur_mfy and target_mfy != cur_mfy:
            continue
        if target_dist and cur_dist and target_dist != cur_dist:
            continue
            
        pl_clean = re.sub(r'\s+', '', str(d.get("truck_plate", ""))).upper()
        if pl_clean in seen_plates:
            continue
        seen_plates.add(pl_clean)
        
        results.append(d)
        
    return results
