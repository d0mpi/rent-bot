import os
import random
import sqlite3
import string
from config import DB_PATH
import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (user_id INTEGER PRIMARY KEY, username TEXT, role TEXT, 
                  referral_link_id INTEGER)''')
    c.execute('''CREATE TABLE IF NOT EXISTS listings
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  type TEXT, 
                  admin_id INTEGER, 
                  image_paths TEXT, 
                  params TEXT,
                  telegram_post_link TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS referral_links
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  admin_id INTEGER, 
                  referral_code TEXT UNIQUE, 
                  description TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS referral_link_clicks
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  referral_link_id INTEGER,
                  listing_id INTEGER,
                  click_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                  user_id INTEGER)''')
    c.execute('''INSERT OR IGNORE INTO users (user_id, username, role) 
                 VALUES (?, ?, ?);''', (462522839, '@l_michael_l', 'superadmin'))
    conn.commit()
    conn.close()

def add_user(user_id, username, role='user', referral_link_id=None):
    conn = get_connection()
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO users (user_id, username, role, referral_link_id) VALUES (?, ?, ?, ?)", 
              (user_id, username, role, referral_link_id))
    conn.commit()
    conn.close()

def generate_referral_code(length=8):
    characters = string.ascii_letters + string.digits
    while True:
        code = ''.join(random.choice(characters) for _ in range(length))
        conn = get_connection()
        c = conn.cursor()
        c.execute("SELECT id FROM referral_links WHERE referral_code=?", (code,))
        if not c.fetchone():
            conn.close()
            return code
        conn.close()

def get_connection():
    return sqlite3.connect(DB_PATH)

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
    image_paths = json.dumps(data.get('image_paths', []))
    params = {k: v for k, v in data.items() if k not in ['type', 'image_paths', 'telegram_post_link'] and v is not None}
    telegram_post_link = data.get('telegram_post_link')
    c.execute('''INSERT INTO listings (type, admin_id, image_paths, params, telegram_post_link)
                 VALUES (?, ?, ?, ?, ?)''',
              (data['type'], admin_id, image_paths, json.dumps(params), telegram_post_link))
    conn.commit()
    conn.close()

def update_listing(listing_id, data):
    conn = get_connection()
    c = conn.cursor()
    image_paths = json.dumps(data.get('image_paths', []))
    params = {k: v for k, v in data.items() if k not in ['type', 'image_paths', 'telegram_post_link'] and v is not None}
    telegram_post_link = data.get('telegram_post_link')
    c.execute('''UPDATE listings SET type=?, image_paths=?, params=?, telegram_post_link=?
                 WHERE id=?''',
              (data['type'], image_paths, json.dumps(params), telegram_post_link, listing_id))
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
    c.execute("SELECT id, type, params, telegram_post_link FROM listings WHERE admin_id=?", (admin_id,))
    listings = [(row[0], row[1], json.loads(row[2]) if row[2] else {}, row[3]) for row in c.fetchall()]
    conn.close()
    return listings

def search_listings(filters):
    conn = get_connection()
    c = conn.cursor()
    query = "SELECT id, type, admin_id, image_paths, params, telegram_post_link FROM listings WHERE 1=1"
    params_list = []
    
    if 'type' in filters:
        query += " AND type=?"
        params_list.append(filters['type'])
    if 'id' in filters:  # Добавляем поддержку фильтра по ID
        query += " AND id=?"
        params_list.append(filters['id'])
    
    c.execute(query, params_list)
    listings = c.fetchall()
    
    result = []
    for listing in listings:
        listing_id, listing_type, admin_id, image_paths, params_json, telegram_post_link = listing
        params = json.loads(params_json) if params_json else {}
        
        matches = True
        for key, value in filters.items():
            if key in ['type', 'id']:
                continue
            if key not in params or params[key] != value:
                matches = False
                break
        
        if matches:
            result.append((
                listing_id,
                listing_type,
                params.get('city', ''),
                params.get('district', ''),
                params.get('rooms', 0),
                params.get('floor', 0),
                admin_id,
                params.get('description', ''),
                json.loads(image_paths) if image_paths else [],
                params,
                telegram_post_link
            ))
    
    conn.close()
    return result

def track_referral_click(referral_link_id, listing_id, user_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute('''INSERT INTO referral_link_clicks (referral_link_id, listing_id, user_id)
                 VALUES (?, ?, ?)''', (referral_link_id, listing_id, user_id))
    conn.commit()
    conn.close()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CREDENTIALS_PATH = os.path.join(BASE_DIR, "handlers/credentials.json")
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_PATH, scope)
client = gspread.authorize(creds)
sheet = client.open("Бот риэлтор")

def get_or_create_worksheet(spreadsheet, title):
    try:
        return spreadsheet.worksheet(title)
    except gspread.exceptions.WorksheetNotFound:
        return spreadsheet.add_worksheet(title=title, rows="100", cols="20")

def sync_clients():
    worksheet = get_or_create_worksheet(sheet, "Пользователи")
    requests_worksheet = get_or_create_worksheet(sheet, "Заявки")
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT user_id, username, referral_link_id FROM users")
    users = c.fetchall()
    conn.close()

    # Получаем данные о заявках из Google Sheets
    requests_data = requests_worksheet.get_all_records()
    request_counts = {}
    for request in requests_data:
        user_id = str(request.get('id', ''))
        if user_id:
            request_counts[user_id] = request_counts.get(user_id, 0) + 1

    # Формируем данные для таблицы Clients
    data = [["user_id", "username", "referral_link_id", "request_count"]]
    for user in users:
        user_id, username, referral_link_id = user
        request_count = request_counts.get(str(user_id), 0)
        data.append([str(user_id), username, str(referral_link_id) if referral_link_id else "", str(request_count)])
    worksheet.update('A1', data)

def sync_referral_stats():
    worksheet = get_or_create_worksheet(sheet, "Реферальная статистика")
    requests_worksheet = get_or_create_worksheet(sheet, "Заявки")
    conn = get_connection()
    c = conn.cursor()
    c.execute('''SELECT rl.id, rl.referral_code, rl.description, 
                 COUNT(DISTINCT u.user_id) as unique_users, 
                 COUNT(rlc.id) as total_clicks
                 FROM referral_links rl 
                 LEFT JOIN users u ON rl.id = u.referral_link_id
                 LEFT JOIN referral_link_clicks rlc ON rl.id = rlc.referral_link_id
                 GROUP BY rl.id''')
    stats = c.fetchall()
    conn.close()

    # Получаем данные о заявках из Google Sheets
    requests_data = requests_worksheet.get_all_records()
    request_counts_by_ref = {}
    conn = get_connection()
    c = conn.cursor()
    for request in requests_data:
        user_id = str(request.get('user_id', ''))
        if user_id:
            c.execute("SELECT referral_link_id FROM users WHERE user_id=?", (int(user_id),))
            result = c.fetchone()
            referral_link_id = result[0] if result else None
            if referral_link_id:
                request_counts_by_ref[referral_link_id] = request_counts_by_ref.get(referral_link_id, 0) + 1
    conn.close()

    # Формируем данные для таблицы Реферальная статистика
    data = [["id", "referral_code", "description", "unique_users", "total_clicks", "request_count"]]
    for stat in stats:
        ref_id, referral_code, description, unique_users, total_clicks = stat
        request_count = request_counts_by_ref.get(ref_id, 0)
        data.append([str(ref_id), referral_code, description, str(unique_users), str(total_clicks), str(request_count)])
    worksheet.update('A1', data)