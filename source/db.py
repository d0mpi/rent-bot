# db.py
import sqlite3
from config import DB_PATH

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (user_id INTEGER PRIMARY KEY, username TEXT, role TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS listings
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, type TEXT, city TEXT, district TEXT, 
                  rooms INTEGER, price INTEGER, admin_id INTEGER)''')
    conn.commit()
    conn.close()

def get_connection():
    return sqlite3.connect(DB_PATH)

def add_admin(user_id, username):
    conn = get_connection()
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO users (user_id, username, role) VALUES (?, ?, 'admin')", (user_id, username))
    conn.commit()
    conn.close()

def remove_admin(user_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("DELETE FROM users WHERE user_id=? AND role='admin'", (user_id,))
    conn.commit()
    conn.close()

def get_all_admins():
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT user_id, username FROM users WHERE role IN ('admin', 'superadmin')")
    admins = c.fetchall()
    conn.close()
    return admins

def get_user_role(user_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT role FROM users WHERE user_id=?", (user_id,))
    result = c.fetchone()
    conn.close()
    return result[0] if result else None

def add_listing(data, admin_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("INSERT INTO listings (type, city, district, rooms, price, admin_id) VALUES (?, ?, ?, ?, ?, ?)",
              (data['housing_type'], data.get('Город', ''), data.get('Район', ''),
               int(data.get('Количество комнат', 0)), int(data.get('Цена', 0)), admin_id))
    conn.commit()
    conn.close()

def get_listings_by_admin(admin_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT id, type, city, price FROM listings WHERE admin_id=?", (admin_id,))
    listings = c.fetchall()
    conn.close()
    return listings