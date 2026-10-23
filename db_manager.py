import random
import sqlite3
import os
import time
import re
import json
from datetime import datetime, timezone, timedelta

# O'zbekiston vaqti (Toshkent: UTC+5)
UZB_TZ = timezone(timedelta(hours=5))

def get_uzb_now():
    return datetime.now(UZB_TZ)

def get_uzb_time_str(fmt="%Y-%m-%d %H:%M:%S"):
    return datetime.now(UZB_TZ).strftime(fmt)

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
        ("users", "account_id", "TEXT DEFAULT ''"),
        ("users", "home_lat", "REAL DEFAULT NULL"),
        ("users", "home_lng", "REAL DEFAULT NULL")
    ]
    for table, col, col_type in migrations:
        try:
            c.execute(f"ALTER TABLE {table} ADD COLUMN {col} {col_type}")
            conn.commit()
        except Exception:
            pass
    try:
        conn.commit()
    except Exception:
        pass
    conn.close()


def save_user_home_coords(phone, lat, lng):
    try:
        conn = get_connection()
        c = conn.cursor()
        digits = re.sub(r'\D', '', str(phone or ''))
        last9 = digits[-9:] if len(digits) >= 9 else digits
        c.execute("UPDATE users SET home_lat = ?, home_lng = ? WHERE phone LIKE ?", (lat, lng, f"%{last9}%"))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error save_user_home_coords: {e}")
        return False


def get_user_home_coords(phone):
    try:
        conn = get_connection()
        c = conn.cursor()
        digits = re.sub(r'\D', '', str(phone or ''))
        last9 = digits[-9:] if len(digits) >= 9 else digits
        c.execute("SELECT home_lat, home_lng FROM users WHERE phone LIKE ?", (f"%{last9}%",))
        row = c.fetchone()
        conn.close()
        if row and row["home_lat"] is not None and row["home_lng"] is not None:
            return {"lat": float(row["home_lat"]), "lng": float(row["home_lng"])}
        return None
    except Exception:
        return None


def delete_driver_avatar(phone):
    try:
        conn = get_connection()
        c = conn.cursor()
        digits = re.sub(r'\D', '', str(phone or ''))
        last9 = digits[-9:] if len(digits) >= 9 else digits
        c.execute("UPDATE drivers SET avatar_url = '' WHERE phone LIKE ?", (f"%{last9}%",))
        c.execute("UPDATE driver_live SET avatar_url = '' WHERE phone LIKE ?", (f"%{last9}%",))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error delete_driver_avatar: {e}")
        return False

def ensure_uzb_timezone_migration():
    """Bazada avval saqlangan barcha UTC vaqtlarini bir marta O'zbekiston (UTC+5) vaqtiga ko'chirish"""
    try:
        conn = get_connection()
        c = conn.cursor()
        c.execute("CREATE TABLE IF NOT EXISTS sys_settings (key TEXT PRIMARY KEY, val TEXT)")
        c.execute("SELECT val FROM sys_settings WHERE key = 'uzb_tz_migrated_v1'")
        if not c.fetchone():
            try:
                c.execute("UPDATE users SET created_at = datetime(created_at, '+5 hours') WHERE created_at IS NOT NULL AND length(created_at) >= 10")
                c.execute("UPDATE drivers SET created_at = datetime(created_at, '+5 hours') WHERE created_at IS NOT NULL AND length(created_at) >= 10")
                c.execute("INSERT OR REPLACE INTO sys_settings (key, val) VALUES ('uzb_tz_migrated_v1', '1')")
                conn.commit()
            except Exception as e_mig:
                print(f"[TZ MIGRATION INNER ERROR]: {e_mig}")
        conn.close()
    except Exception as e_out:
        print(f"[TZ MIGRATION ERROR]: {e_out}")

def purge_legacy_test_drivers():
    """Barcha eski sinov haydovchilari (ahror, 940401009 yoki account_id yo'q) serverdan butunlay tozalab tashlanadi"""
    try:
        conn = get_connection()
        c = conn.cursor()
        c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='drivers'")
        if c.fetchone():
            c.execute("DELETE FROM drivers WHERE phone LIKE '%940401009%' OR account_id = '' OR account_id IS NULL OR lower(full_name) LIKE '%ahror%'")
            c.execute("DELETE FROM driver_live WHERE phone LIKE '%940401009%' OR lower(driver_name) LIKE '%ahror%'")
            c.execute("DELETE FROM users WHERE (phone LIKE '%940401009%' OR lower(full_name) LIKE '%ahror%') AND role = 'driver'")
            c.execute("DELETE FROM user_avatars WHERE phone_clean LIKE '%940401009%'")
            conn.commit()
            try:
                c.execute("VACUUM")
            except Exception:
                pass
        conn.close()
    except Exception as e:
        print(f"[PURGE ERROR]: {e}")

# Auto-run migration and purge whenever module is loaded
try:
    ensure_db_columns()
    ensure_uzb_timezone_migration()
    purge_legacy_test_drivers()
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
        updated_at TIMESTAMP DEFAULT (datetime('now', '+5 hours'))
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
        house_number TEXT DEFAULT '',
        pin_code TEXT,
        created_at TIMESTAMP DEFAULT (datetime('now', '+5 hours'))
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
        created_at TIMESTAMP DEFAULT (datetime('now', '+5 hours'))
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
        updated_at TIMESTAMP DEFAULT (datetime('now', '+5 hours'))
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
        created_at TIMESTAMP DEFAULT (datetime('now', '+5 hours'))
    );
    """)

    # Insert default initial data if empty
    # To'liq toza tizim - hech qanday mock yoki sinov fuqarolari kiritilmaydi
    pass

    # Tizim jadvallari saqlanadi - hech qanday ma'lumotlar o'chirilmaydi


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
    try:
        purge_legacy_test_drivers()
    except Exception:
        pass
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
def register_user(phone, full_name, role='resident', region='qashqadaryo', district='nishon', mfy='koksoy', street='koksoy_markaziy', house_number=''):
    clean_p = phone.strip()
    digits = re.sub(r'\D', '', clean_p)
    last9 = digits[-9:] if len(digits) >= 9 else digits
    conn = get_connection()
    c = conn.cursor()
    # Check if exists by exact phone or last9 digits
    row = None
    if last9:
        c.execute("SELECT * FROM users WHERE phone = ? OR phone LIKE ?", (clean_p, f"%{last9}%"))
        row = c.fetchone()
    else:
        c.execute("SELECT * FROM users WHERE phone = ?", (clean_p,))
        row = c.fetchone()

    if row:
        u_dict = dict(row)
        acc_id = u_dict.get("account_id")
        if not acc_id:
            acc_id = generate_unique_account_id("XP-")
            u_dict["account_id"] = acc_id
        c.execute("UPDATE users SET full_name = ?, account_id = ? WHERE id = ?", (full_name, acc_id, u_dict["id"]))
        conn.commit()
        u_dict["full_name"] = full_name
        conn.close()
        return {"ok": True, "exists": True, "user": u_dict}

    account_id = generate_unique_account_id("XP-")
    now_uzb = get_uzb_time_str()
    try:
        c.execute("""
        INSERT INTO users (phone, full_name, role, region, district, mfy, street, house_number, account_id, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (clean_p, full_name, role, region, district, mfy, street, house_number, account_id, now_uzb))
        conn.commit()
        user_id = c.lastrowid
    except sqlite3.IntegrityError:
        c.execute("SELECT * FROM users WHERE phone = ? OR phone LIKE ?", (clean_p, f"%{last9}%"))
        row = c.fetchone()
        u_dict = dict(row)
        user_id = u_dict["id"]
        account_id = u_dict.get("account_id") or account_id
        c.execute("UPDATE users SET full_name = ?, account_id = ? WHERE id = ?", (full_name, account_id, user_id))
        conn.commit()
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

def update_user_address(phone, region, district, mfy, street, house_number="", account_id=None):
    conn = get_connection()
    c = conn.cursor()
    target_id = None

    # 1. Search by account_id first if provided
    if account_id:
        c.execute("SELECT id FROM users WHERE account_id = ?", (account_id.strip(),))
        r = c.fetchone()
        if r:
            target_id = r["id"]

    # 2. Search by phone digits if not found by account_id
    if not target_id and phone:
        clean_p = re.sub(r'\D', '', str(phone or ''))
        last9 = clean_p[-9:] if len(clean_p) >= 9 else clean_p
        if last9:
            c.execute("SELECT id, phone FROM users WHERE role = 'resident'")
            for r in c.fetchall():
                r_digits = re.sub(r'\D', '', str(r["phone"] or ''))
                if r_digits.endswith(last9) or last9 in r_digits:
                    target_id = r["id"]
                    break

    # 3. Update existing user (NEVER CREATE DUPLICATE USER ON ADDRESS CHANGE)
    if target_id:
        c.execute("""
            UPDATE users
            SET region = COALESCE(NULLIF(?, ''), region),
                district = COALESCE(NULLIF(?, ''), district),
                mfy = COALESCE(NULLIF(?, ''), mfy),
                street = COALESCE(NULLIF(?, ''), street),
                house_number = COALESCE(NULLIF(?, ''), house_number)
            WHERE id = ?
        """, (region, district, mfy, street, house_number, target_id))
        conn.commit()

    conn.close()
    return True

def update_user_name(phone, account_id, full_name):
    conn = get_connection()
    c = conn.cursor()
    target_id = None
    clean_name = str(full_name or '').strip()
    if not clean_name:
        conn.close()
        return False

    # 1. Search by account_id first if provided
    if account_id:
        c.execute("SELECT id FROM users WHERE account_id = ?", (account_id.strip(),))
        r = c.fetchone()
        if r:
            target_id = r["id"]

    # 2. Search by phone digits if not found by account_id
    if not target_id and phone:
        clean_p = re.sub(r'\D', '', str(phone or ''))
        last9 = clean_p[-9:] if len(clean_p) >= 9 else clean_p
        if last9:
            c.execute("SELECT id, phone FROM users")
            for r in c.fetchall():
                r_digits = re.sub(r'\D', '', str(r["phone"] or ''))
                if r_digits.endswith(last9) or last9 in r_digits:
                    target_id = r["id"]
                    break

    if target_id:
        c.execute("UPDATE users SET full_name = ? WHERE id = ?", (clean_name, target_id))
        conn.commit()

    conn.close()
    return True

def get_user_by_phone(phone):
    clean_p = re.sub(r'\D', '', str(phone or ''))
    last9 = clean_p[-9:] if len(clean_p) >= 9 else clean_p
    if not last9:
        return None
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE role = 'resident'")
    rows = c.fetchall()
    for row in rows:
        u_dict = dict(row)
        u_digits = re.sub(r'\D', '', str(u_dict.get('phone', '')))
        if u_digits.endswith(last9) or last9 in u_digits:
            if not u_dict.get("account_id"):
                acc_id = generate_unique_account_id("XP-")
                c.execute("UPDATE users SET account_id = ? WHERE id = ?", (acc_id, u_dict["id"]))
                conn.commit()
                u_dict["account_id"] = acc_id
            conn.close()
            return u_dict
    conn.close()
    return None

def get_user_by_account_id(account_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE account_id = ?", (account_id.strip(),))
    row = c.fetchone()
    if not row:
        # Check without XP- prefix or partial
        c.execute("SELECT * FROM users WHERE account_id LIKE ?", (f"%{account_id.strip()}%",))
        row = c.fetchone()
    conn.close()
    return dict(row) if row else None

def delete_user_by_id(user_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("DELETE FROM users WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()
    return True

def get_filtered_users(region=None, district=None, mfy=None, street=None):
    conn = get_connection()
    c = conn.cursor()
    query = "SELECT * FROM users WHERE role = 'resident'"
    params = []
    if region:
        query += " AND region = ?"
        params.append(region)
    if district:
        query += " AND district = ?"
        params.append(district)
    if mfy:
        query += " AND mfy = ?"
        params.append(mfy)
    if street:
        query += " AND street = ?"
        params.append(street)
    query += " ORDER BY region, district, mfy, street, full_name ASC"
    c.execute(query, params)
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows



# --- DRIVER FUNCTIONS ---
def add_driver(phone, full_name, truck_plate, password='gaz2026', truck_model='Isuzu', truck_color='Oq', assigned_region='qashqadaryo', assigned_district='nishon', assigned_mfy='koksoy'):
    clean_p = phone.strip()
    digits = re.sub(r'\D', '', clean_p)
    last9 = digits[-9:] if len(digits) >= 9 else digits
    clean_plate = re.sub(r'[^A-Z0-9]', '', str(truck_plate).upper())

    conn = get_connection()
    c = conn.cursor()

    # 1. Telefon raqami bazada bormi (oxirgi 9 ta raqam bo'yicha)?
    if last9:
        c.execute("SELECT * FROM drivers")
        for r in c.fetchall():
            r_dict = dict(r)
            d_digits = re.sub(r'\D', '', str(r_dict.get('phone') or ''))
            d_last9 = d_digits[-9:] if len(d_digits) >= 9 else d_digits
            if d_last9 and (d_last9 == last9 or (len(last9) == 9 and last9 in d_digits)):
                d_name = r_dict.get('full_name', 'Boshqa haydovchi')
                acc = r_dict.get('account_id', '')
                conn.close()
                return {
                    "ok": False,
                    "error": "phone_exists",
                    "message": f"Ushbu telefon raqami allaqachon ro‘yxatdan o‘tgan! ({d_name} — {acc})"
                }

    # 2. Davlat raqami bazada bormi (harflar katta-kichikligidan qat'i nazar, aynan bir xil)?
    if clean_plate:
        c.execute("SELECT * FROM drivers")
        for r in c.fetchall():
            r_dict = dict(r)
            d_plate = re.sub(r'[^A-Z0-9]', '', str(r_dict.get('truck_plate') or '').upper())
            if d_plate == clean_plate:
                d_name = r_dict.get('full_name', 'Boshqa haydovchi')
                acc = r_dict.get('account_id', '')
                conn.close()
                return {
                    "ok": False,
                    "error": "plate_exists",
                    "message": f"Ushbu davlat raqami allaqachon ro‘yxatdan o‘tgan! ({d_name} — {acc})"
                }

    account_id = generate_unique_account_id("HP-")
    now_uzb = get_uzb_time_str()

    c.execute("""
    INSERT INTO drivers (phone, full_name, truck_model, truck_plate, truck_color, assigned_region, assigned_district, assigned_mfy, password, account_id, is_active, created_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?)
    """, (clean_p, full_name, truck_model, clean_plate, truck_color, assigned_region, assigned_district, assigned_mfy, password, account_id, now_uzb))
    
    # Also ensure user table has driver role and same account_id
    c.execute("""
    INSERT OR REPLACE INTO users (phone, full_name, role, region, district, mfy, account_id, two_step_password, two_step_hint, created_at)
    VALUES (?, ?, 'driver', ?, ?, ?, ?, NULL, NULL, ?)
    """, (clean_p, full_name, assigned_region, assigned_district, assigned_mfy, account_id, now_uzb))
    c.execute("UPDATE users SET two_step_password = NULL, two_step_hint = NULL WHERE phone = ? OR phone LIKE ?", (clean_p, f"%{clean_p[-9:]}%"))

    # Also register in driver_live with initial WAITING status
    c.execute("""
    INSERT OR REPLACE INTO driver_live (phone, driver_name, truck_plate, truck_model, truck_color, status, stage, lat, lng, region, district, mfy)
    VALUES (?, ?, ?, ?, ?, 'waiting', 'collect', NULL, NULL, ?, ?, ?)
    """, (clean_p, full_name, clean_plate, truck_model, truck_color, assigned_region, assigned_district, assigned_mfy))

    conn.commit()
    conn.close()
    return {"ok": True, "account_id": account_id, "message": f"Haydovchi {full_name} ({clean_plate}) muvaffaqiyatli qo‘shildi!"}



def get_driver_by_phone(phone):
    if not phone:
        return None
    raw = str(phone).strip()
    digits = re.sub(r'\D', '', raw)
    last9 = digits[-9:] if len(digits) >= 9 else digits
    if not last9:
        return None
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM drivers")
    for r in c.fetchall():
        d_dict = dict(r)
        d_digits = re.sub(r'\D', '', str(d_dict.get('phone', '')))
        if d_digits.endswith(last9) or last9 in d_digits:
            conn.close()
            return d_dict
    conn.close()
    return None


def get_driver_by_plate(plate):
    if not plate:
        return None
    clean_p = re.sub(r'[^A-Z0-9]', '', str(plate).upper())
    if not clean_p:
        return None
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM drivers")
    for r in c.fetchall():
        d_dict = dict(r)
        d_plate = re.sub(r'[^A-Z0-9]', '', str(d_dict.get('truck_plate', '')).upper())
        if d_plate == clean_p:
            conn.close()
            return d_dict
    conn.close()
    return None


def get_driver_by_account_id(account_id):
    if not account_id:
        return None
    conn = get_connection()
    c = conn.cursor()
    clean_id = str(account_id).strip().upper()
    c.execute("SELECT * FROM drivers WHERE (UPPER(account_id) = ? OR UPPER(account_id) = ?) AND is_active = 1", 
              (clean_id, f"HP-{clean_id}"))
    row = c.fetchone()
    if row:
        conn.close()
        return dict(row)
    digits = re.sub(r'\D', '', clean_id)
    if digits and len(digits) >= 4:
        c.execute("SELECT * FROM drivers WHERE account_id LIKE ? AND is_active = 1", (f"%{digits}%",))
        row = c.fetchone()
        if row:
            conn.close()
            return dict(row)
    c.execute("SELECT * FROM drivers WHERE is_active = 1")
    for r in c.fetchall():
        d_dict = dict(r)
        acc = str(d_dict.get('account_id', '')).upper()
        if clean_id in acc or acc in clean_id or (digits and digits in re.sub(r'\D', '', acc)):
            conn.close()
            return d_dict
    conn.close()
    return None


def update_driver_admin_credentials(phone, field, new_value):
    conn = get_connection()
    c = conn.cursor()
    raw = str(phone or '').strip()
    digits = re.sub(r'\D', '', raw)
    last9 = digits[-9:] if len(digits) >= 9 else digits

    c.execute("SELECT * FROM drivers WHERE phone = ? OR phone LIKE ? OR phone LIKE ?", (raw, f"%{last9}%", f"%{digits}%"))
    drv = c.fetchone()
    if not drv:
        conn.close()
        return {"ok": False, "message": "Haydovchi topilmadi"}

    old_phone = drv["phone"]
    clean_old_last9 = re.sub(r'\D', '', old_phone)[-9:]

    if field == "full_name":
        c.execute("UPDATE drivers SET full_name = ? WHERE phone = ?", (new_value.strip(), old_phone))
        c.execute("UPDATE users SET full_name = ? WHERE phone LIKE ?", (new_value.strip(), f"%{clean_old_last9}%"))
        c.execute("UPDATE driver_live SET driver_name = ? WHERE phone LIKE ?", (new_value.strip(), f"%{clean_old_last9}%"))
    elif field == "phone":
        new_phone = new_value.strip()
        c.execute("UPDATE drivers SET phone = ? WHERE phone = ?", (new_phone, old_phone))
        c.execute("UPDATE users SET phone = ? WHERE phone LIKE ?", (new_phone, f"%{clean_old_last9}%"))
        c.execute("UPDATE driver_live SET phone = ? WHERE phone LIKE ?", (new_phone, f"%{clean_old_last9}%"))
        c.execute("UPDATE sessions SET phone = ? WHERE phone LIKE ?", (new_phone, f"%{clean_old_last9}%"))
    elif field == "truck_plate":
        new_plate = new_value.strip().upper()
        c.execute("UPDATE drivers SET truck_plate = ? WHERE phone = ?", (new_plate, old_phone))
        c.execute("UPDATE driver_live SET truck_plate = ? WHERE phone LIKE ?", (new_plate, f"%{clean_old_last9}%"))
    elif field == "truck_model":
        new_model = new_value.strip()
        c.execute("UPDATE drivers SET truck_model = ? WHERE phone = ?", (new_model, old_phone))
        c.execute("UPDATE driver_live SET truck_model = ? WHERE phone LIKE ?", (new_model, f"%{clean_old_last9}%"))
    elif field == "truck_color":
        new_color = new_value.strip()
        c.execute("UPDATE drivers SET truck_color = ? WHERE phone = ?", (new_color, old_phone))
        c.execute("UPDATE driver_live SET truck_color = ? WHERE phone LIKE ?", (new_color, f"%{clean_old_last9}%"))
    elif field == "password":
        c.execute("UPDATE drivers SET password = ? WHERE phone = ?", (new_value.strip(), old_phone))

    conn.commit()
    target_phone = new_value.strip() if field == 'phone' else old_phone
    c.execute("SELECT * FROM drivers WHERE phone = ?", (target_phone,))
    updated = c.fetchone()
    conn.close()
    return {"ok": True, "driver": dict(updated) if updated else None}

def update_driver_profile(account_phone, driver_name=None, truck_plate=None, truck_model=None, truck_color=None, new_phone=None):
    clean_p = re.sub(r'\D', '', str(account_phone or ''))
    if len(clean_p) < 9:
        return False
    last9 = clean_p[-9:]
    conn = get_connection()
    c = conn.cursor()

    # FAQAT driver_live jadvali yangilanadi (aholi ko'rishi uchun)!
    # Asosiy drivers jadvali (Adminning qat'iy rasmiy ma'lumotlari) mutlaqo o'zgarmaydi!
    c.execute("""
        UPDATE driver_live
        SET driver_name = COALESCE(NULLIF(?, ''), driver_name),
            truck_plate = COALESCE(NULLIF(?, ''), truck_plate),
            truck_model = COALESCE(NULLIF(?, ''), truck_model),
            truck_color = COALESCE(NULLIF(?, ''), truck_color),
            phone = COALESCE(NULLIF(?, ''), phone)
        WHERE phone LIKE ?
    """, (driver_name, truck_plate, truck_model, truck_color, new_phone, f"%{last9}%"))

    conn.commit()
    conn.close()
    return True

def get_all_drivers():
    try:
        purge_legacy_test_drivers()
    except Exception:
        pass
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM drivers WHERE is_active = 1 AND phone NOT LIKE '%940401009%' AND lower(full_name) NOT LIKE '%ahror%' AND account_id != '' AND account_id IS NOT NULL ORDER BY id DESC")
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
    try:
        c.execute("VACUUM")
    except Exception:
        pass
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
    updates = ["lat = ?, lng = ?, updated_at = (datetime('now', '+5 hours'))"]
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
def save_user_avatar(phone, role, avatar_url, account_id=""):
    conn = get_connection()
    c = conn.cursor()
    clean_p = re.sub(r'\D', '', str(phone or ''))
    acc_clean = str(account_id or '').strip()

    c.execute("""
        CREATE TABLE IF NOT EXISTS user_avatars (
            phone_clean TEXT PRIMARY KEY,
            full_phone TEXT,
            role TEXT,
            avatar_url TEXT,
            updated_at TIMESTAMP DEFAULT (datetime('now', '+5 hours'))
        )
    """)
    if clean_p:
        c.execute("""
            INSERT OR REPLACE INTO user_avatars (phone_clean, full_phone, role, avatar_url, updated_at)
            VALUES (?, ?, ?, ?, (datetime('now', '+5 hours')))
        """, (clean_p[-9:], phone, role, avatar_url))

    if role == 'driver':
        if clean_p:
            c.execute("UPDATE drivers SET avatar_url = ? WHERE phone LIKE ?", (avatar_url, f"%{clean_p[-9:]}%"))
            c.execute("UPDATE driver_live SET updated_at = (datetime('now', '+5 hours')), avatar_url = ? WHERE phone LIKE ?", (avatar_url, f"%{clean_p[-9:]}%"))
        if acc_clean:
            c.execute("UPDATE drivers SET avatar_url = ? WHERE (UPPER(account_id) = UPPER(?) OR UPPER(account_id) = ?)", 
                      (avatar_url, acc_clean, f"HP-{acc_clean.replace('HP-', '')}"))
            c.execute("UPDATE driver_live SET avatar_url = ? WHERE UPPER(driver_name) LIKE ? OR UPPER(truck_plate) LIKE ?", (avatar_url, f"%{acc_clean}%", f"%{acc_clean}%"))
    else:
        if clean_p:
            c.execute("UPDATE users SET avatar_url = ? WHERE phone LIKE ?", (avatar_url, f"%{clean_p[-9:]}%"))
    conn.commit()
    conn.close()
    return True

def get_user_avatar(phone, role='resident', account_id=''):
    conn = get_connection()
    c = conn.cursor()
    clean_p = re.sub(r'\D', '', str(phone or ''))
    last9 = clean_p[-9:] if len(clean_p) >= 9 else clean_p
    acc_clean = str(account_id or '').strip()

    # 1. Check by account_id in drivers
    if acc_clean:
        try:
            c.execute("SELECT avatar_url FROM drivers WHERE (UPPER(account_id) = UPPER(?) OR UPPER(account_id) = ? OR account_id LIKE ?) AND avatar_url IS NOT NULL AND avatar_url != ''", 
                      (acc_clean, f"HP-{acc_clean.replace('HP-', '')}", f"%{acc_clean}%"))
            r = c.fetchone()
            if r and r["avatar_url"]:
                conn.close()
                return r["avatar_url"]
        except Exception:
            pass

    # 2. Check dedicated user_avatars table
    if last9:
        try:
            c.execute("SELECT avatar_url FROM user_avatars WHERE phone_clean = ? AND avatar_url != ''", (last9,))
            row = c.fetchone()
            if row and row["avatar_url"]:
                conn.close()
                return row["avatar_url"]
        except Exception:
            pass

    # 3. Check drivers table if driver
    if last9 and role == 'driver':
        try:
            c.execute("SELECT avatar_url FROM drivers WHERE phone LIKE ? AND avatar_url != ''", (f"%{last9}%",))
            row = c.fetchone()
            if row and row["avatar_url"]:
                conn.close()
                return row["avatar_url"]
        except Exception:
            pass

    # 4. Check users table
    if last9:
        try:
            c.execute("SELECT avatar_url FROM users WHERE phone LIKE ? AND avatar_url != ''", (f"%{last9}%",))
            row = c.fetchone()
            if row and row["avatar_url"]:
                conn.close()
                return row["avatar_url"]
        except Exception:
            pass

    conn.close()
    return ""

def upsert_driver_live(phone, driver_name="", truck_plate="", truck_model="", truck_color="", status="waiting", stage="collect", lat=None, lng=None, region="", district="", mfy="", street="", street_name="", avatar_url=""):
    conn = get_connection()
    c = conn.cursor()
    clean_p = re.sub(r'\D', '', str(phone or ''))
    
    # Check if driver deactivated by admin
    c.execute("SELECT * FROM drivers WHERE phone LIKE ?", (f"%{clean_p[-9:]}%",))
    drv_row = c.fetchone()
    if drv_row and drv_row["is_active"] == 0:
        conn.close()
        return False
        
    c.execute("SELECT * FROM driver_live WHERE phone LIKE ?", (f"%{clean_p[-9:]}%",))
    live_row = c.fetchone()

    f_name = driver_name or (live_row["driver_name"] if live_row else "") or (drv_row["full_name"] if drv_row else "") or ""
    f_plate = truck_plate or (live_row["truck_plate"] if live_row else "") or (drv_row["truck_plate"] if drv_row else "") or ""
    f_model = truck_model or (live_row["truck_model"] if live_row else "") or (drv_row["truck_model"] if drv_row else "") or "Isuzu NPR 75"
    f_color = truck_color or (live_row["truck_color"] if live_row else "") or (drv_row["truck_color"] if drv_row else "") or "Oq"
    f_reg = region or (live_row["region"] if live_row else "") or (drv_row["assigned_region"] if drv_row else "") or ""
    f_dist = district or (live_row["district"] if live_row else "") or (drv_row["assigned_district"] if drv_row else "") or ""
    f_mfy = mfy or (live_row["mfy"] if live_row else "") or (drv_row["assigned_mfy"] if drv_row else "") or ""
    f_street = street or (live_row["street"] if live_row else "") or "istiqlol"
    f_street_name = street_name or (live_row["street_name"] if live_row else "") or "Istiqlol ko‘chasi"
    final_avatar = avatar_url or (drv_row["avatar_url"] if drv_row else "") or ""
    
    lat_val = float(lat) if lat is not None else None
    lng_val = float(lng) if lng is not None else None

    c.execute("""
        INSERT OR REPLACE INTO driver_live 
        (phone, driver_name, truck_plate, truck_model, truck_color, status, stage, lat, lng, region, district, mfy, street, street_name, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, (datetime('now', '+5 hours')))
    """, (phone, f_name, f_plate, f_model, f_color, status, stage, lat_val, lng_val, f_reg, f_dist, f_mfy, f_street, f_street_name))
    
    conn.commit()
    conn.close()
    return True

def get_active_trucks(region=None, district=None, mfy=None):
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        SELECT d.phone, 
               d.account_id,
               COALESCE(NULLIF(l.driver_name, ''), d.full_name) as full_name, 
               COALESCE(NULLIF(l.truck_model, ''), d.truck_model) as truck_model, 
               COALESCE(NULLIF(l.truck_plate, ''), d.truck_plate) as truck_plate, 
               COALESCE(NULLIF(l.truck_color, ''), d.truck_color) as truck_color,
               d.assigned_region, d.assigned_district, d.assigned_mfy, d.avatar_url,
               l.lat,
               l.lng,
               COALESCE(l.status, 'waiting') as status,
               COALESCE(l.stage, 'collect') as stage,
               COALESCE(l.street, 'istiqlol') as street,
               COALESCE(l.street_name, 'Istiqlol ko‘chasi') as street_name,
               COALESCE(l.mfy, d.assigned_mfy, 'koksoy') as live_mfy,
               COALESCE(l.district, d.assigned_district, 'nishon') as live_dist,
               COALESCE(l.region, d.assigned_region, 'qashqadaryo') as live_reg,
               l.updated_at
        FROM drivers d
        INNER JOIN driver_live l ON (d.phone = l.phone OR l.phone LIKE '%' || SUBSTR(REPLACE(REPLACE(d.phone, '+', ''), ' ', ''), -9))
        WHERE d.is_active = 1 
          AND l.status != 'waiting'
          AND l.lat IS NOT NULL AND l.lat != 0
          AND (strftime('%s', 'now') - strftime('%s', l.updated_at)) <= 600
        ORDER BY d.id DESC
    """)
    rows = c.fetchall()
    conn.close()
    
    results = []
    seen_plates = set()
    for r in rows:
        d = dict(r)
        
        # User requirement: Agar xaritadagi ma'lumotlari aniqlanmasa, aholiga ko'rsatilmasin, standart koordinata berilmasin!
        if d.get('lat') is None or d.get('lng') is None or d.get('lat') == 0 or d.get('lng') == 0:
            continue
            
        pl_clean = re.sub(r'\s+', '', str(d.get("truck_plate", ""))).upper()
        if not pl_clean:
            pl_clean = re.sub(r'\D', '', str(d.get("phone", "")))
        if pl_clean in seen_plates:
            continue
        seen_plates.add(pl_clean)
        
        results.append(d)
        
    return results
