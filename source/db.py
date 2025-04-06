import sqlite3
from config import DB_PATH
import json

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (user_id INTEGER PRIMARY KEY, username TEXT, role TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS listings
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, type TEXT, city TEXT, district TEXT, 
                  rooms INTEGER, floor INTEGER, max_price INTEGER, min_price INTEGER, 
                  admin_id INTEGER, description TEXT, image_paths TEXT)''')
    c.execute('''INSERT OR IGNORE INTO users (user_id, username, role) 
                 VALUES (?, ?, ?);''', (462522839, '@l_michael_l', 'superadmin'))
    conn.commit()
    conn.close()

def get_connection():
    return sqlite3.connect(DB_PATH)

def add_user(user_id, username, role='admin'):
    conn = get_connection()
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO users (user_id, username, role) VALUES (?, ?, ?)", (user_id, username, role))
    conn.commit()
    conn.close()

def remove_user(user_id):
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
    image_paths = json.dumps(data.get('image_paths', []))  # Всегда валидный JSON
    c.execute('''INSERT INTO listings (type, city, district, rooms, floor, max_price, min_price, admin_id, description, image_paths)
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
              (data['type'], data.get('city', ''), data.get('district', ''),
               int(data.get('rooms', 0)), int(data.get('floor', 0)),
               int(data.get('max_price', 0)), int(data.get('min_price', 0)),
               admin_id, data.get('description', ''), image_paths))
    conn.commit()
    conn.close()

def update_listing(listing_id, data):
    conn = get_connection()
    c = conn.cursor()
    image_paths = json.dumps(data.get('image_paths', []))  # Всегда валидный JSON
    c.execute('''UPDATE listings SET type=?, city=?, district=?, rooms=?, floor=?, max_price=?, min_price=?, 
                 description=?, image_paths=? WHERE id=?''',
              (data['type'], data.get('city', ''), data.get('district', ''),
               int(data.get('rooms', 0)), int(data.get('floor', 0)),
               int(data.get('max_price', 0)), int(data.get('min_price', 0)),
               data.get('description', ''), image_paths, listing_id))
    conn.commit()
    conn.close()

def delete_listing(listing_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("DELETE FROM listings WHERE id=?", (listing_id,))
    conn.commit()
    conn.close()

def get_listings_by_admin(admin_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT id, type, city, max_price FROM listings WHERE admin_id=?", (admin_id,))
    listings = c.fetchall()
    conn.close()
    return listings

def search_listings(filters):
    conn = get_connection()
    c = conn.cursor()
    query = "SELECT id, type, city, district, rooms, floor, max_price, min_price, admin_id, description, image_paths FROM listings WHERE 1=1"
    params = []
    for key, value in filters.items():
        if key in ['rooms', 'floor', 'max_price', 'min_price']:
            query += f" AND {key}=?"
            params.append(int(value))
        else:
            query += f" AND {key}=?"
            params.append(value)
    c.execute(query, params)
    listings = c.fetchall()
    conn.close()
    # Обрабатываем None и пустую строку как пустой список
    return [(l[0], l[1], l[2], l[3], l[4], l[5], l[6], l[7], l[8], l[9], json.loads(l[10] if l[10] and l[10] != '' else '[]')) for l in listings]