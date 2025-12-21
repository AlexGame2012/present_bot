import sqlite3
from datetime import datetime, timedelta
from config import DATABASE 
import os
import cv2
import numpy as np
from math import sqrt, ceil, floor

class DatabaseManager:
    def __init__(self, database):
        self.database = database

    def create_tables(self):
        conn = sqlite3.connect(self.database)
        with conn:
            conn.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                user_name TEXT,
                coins INTEGER DEFAULT 0,
                registration_date TEXT DEFAULT CURRENT_TIMESTAMP
            )
            ''')

            conn.execute('''
            CREATE TABLE IF NOT EXISTS prizes (
                prize_id INTEGER PRIMARY KEY AUTOINCREMENT,
                image TEXT,
                used INTEGER DEFAULT 0,
                added_by INTEGER,
                add_date TEXT,
                price INTEGER DEFAULT 50
            )
            ''')

            conn.execute('''
            CREATE TABLE IF NOT EXISTS winners (
                user_id INTEGER,
                prize_id INTEGER,
                win_time TEXT,
                win_type TEXT DEFAULT 'regular',
                FOREIGN KEY(user_id) REFERENCES users(user_id),
                FOREIGN KEY(prize_id) REFERENCES prizes(prize_id)
            )
            ''')

            conn.execute('''
            CREATE TABLE IF NOT EXISTS failed_prizes (
                fail_id INTEGER PRIMARY KEY AUTOINCREMENT,
                prize_id INTEGER,
                user_id INTEGER,
                fail_time TEXT,
                FOREIGN KEY(prize_id) REFERENCES prizes(prize_id),
                FOREIGN KEY(user_id) REFERENCES users(user_id)
            )
            ''')

            conn.execute('''
            CREATE TABLE IF NOT EXISTS bonus_actions (
                action_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                action_type TEXT,
                coins_change INTEGER,
                action_time TEXT,
                FOREIGN KEY(user_id) REFERENCES users(user_id)
            )
            ''')

            conn.execute('''
            CREATE TABLE IF NOT EXISTS bot_settings (
                setting_key TEXT PRIMARY KEY,
                setting_value TEXT
            )
            ''')

            conn.commit()

    def add_user(self, user_id, user_name):
        conn = sqlite3.connect(self.database)
        with conn:
            conn.execute('INSERT OR IGNORE INTO users (user_id, user_name) VALUES (?, ?)', (user_id, user_name or str(user_id)))
            conn.commit()

    def add_prize(self, image_path, added_by=None, price=50):
        add_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        conn = sqlite3.connect(self.database)
        with conn:
            cur = conn.cursor()
            cur.execute('''INSERT INTO prizes (image, added_by, add_date, price) VALUES (?, ?, ?, ?)''', 
                       (image_path, added_by, add_date, price))
            conn.commit()
            return cur.lastrowid

    def add_winner(self, user_id, prize_id, win_type='regular'):
        win_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        conn = sqlite3.connect(self.database)
        with conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM winners WHERE user_id = ? AND prize_id = ?", (user_id, prize_id))
            if cur.fetchall():
                return 0
            else:
                conn.execute('''INSERT INTO winners (user_id, prize_id, win_time, win_type) VALUES (?, ?, ?, ?)''', 
                           (user_id, prize_id, win_time, win_type))
                if win_type == 'regular':
                    self.add_coins(user_id, 10)
                conn.commit()
                return 1

    def add_failed_prize(self, user_id, prize_id):
        fail_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        conn = sqlite3.connect(self.database)
        with conn:
            conn.execute('''INSERT INTO failed_prizes (user_id, prize_id, fail_time) VALUES (?, ?, ?)''', 
                        (user_id, prize_id, fail_time))
            conn.commit()

    def add_coins(self, user_id, amount):
        conn = sqlite3.connect(self.database)
        with conn:
            conn.execute('UPDATE users SET coins = coins + ? WHERE user_id = ?', (amount, user_id))
            action_type = 'add_coins' if amount > 0 else 'spend_coins'
            conn.execute('''INSERT INTO bonus_actions (user_id, action_type, coins_change, action_time) 
                          VALUES (?, ?, ?, ?)''', 
                        (user_id, action_type, amount, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
            conn.commit()

    def get_coins(self, user_id):
        conn = sqlite3.connect(self.database)
        cur = conn.cursor()
        cur.execute('SELECT coins FROM users WHERE user_id = ?', (user_id,))
        result = cur.fetchone()
        return result[0] if result else 0

    def mark_prize_used(self, prize_id):
        conn = sqlite3.connect(self.database)
        with conn:
            conn.execute('UPDATE prizes SET used = 1 WHERE prize_id = ?', (prize_id,))
            conn.commit()

    def get_users(self):
        conn = sqlite3.connect(self.database)
        cur = conn.cursor()
        cur.execute('SELECT user_id FROM users')
        return [x[0] for x in cur.fetchall()]

    def get_all_users(self):
        conn = sqlite3.connect(self.database)
        cur = conn.cursor()
        cur.execute('SELECT user_id, user_name, coins FROM users ORDER BY coins DESC')
        return cur.fetchall()

    def get_prize_img(self, prize_id):
        conn = sqlite3.connect(self.database)
        cur = conn.cursor()
        cur.execute('SELECT image FROM prizes WHERE prize_id = ?', (prize_id,))
        result = cur.fetchall()
        return result[0][0] if result else None

    def get_random_prize(self):
        conn = sqlite3.connect(self.database)
        cur = conn.cursor()
        cur.execute('SELECT prize_id, image FROM prizes WHERE used = 0 ORDER BY RANDOM() LIMIT 1')
        result = cur.fetchall()
        return result[0] if result else None

    def get_user_failed_prizes(self, user_id):
        conn = sqlite3.connect(self.database)
        cur = conn.cursor()
        cur.execute('''SELECT DISTINCT p.prize_id, p.image 
                      FROM failed_prizes fp 
                      JOIN prizes p ON fp.prize_id = p.prize_id 
                      WHERE fp.user_id = ? AND p.used = 0''', (user_id,))
        return cur.fetchall()

    def get_unused_prizes_count(self):
        conn = sqlite3.connect(self.database)
        cur = conn.cursor()
        cur.execute('SELECT COUNT(*) FROM prizes WHERE used = 0')
        result = cur.fetchone()
        return result[0] if result else 0

    def get_winners_count(self, prize_id):
        conn = sqlite3.connect(self.database)
        with conn:
            cur = conn.cursor()
            cur.execute('SELECT COUNT(DISTINCT user_id) FROM winners WHERE prize_id = ?', (prize_id,))
            return cur.fetchall()[0][0]

    def get_rating(self):
        conn = sqlite3.connect(self.database)
        with conn:
            cur = conn.cursor()
            cur.execute('''
                SELECT u.user_name, COUNT(w.user_id) as prize_count
                FROM winners w
                JOIN users u ON w.user_id = u.user_id
                WHERE w.win_type = 'regular'
                GROUP BY w.user_id
                ORDER BY prize_count DESC
                LIMIT 10
            ''')
            return cur.fetchall()

    def get_winners_img(self, user_id):
        conn = sqlite3.connect(self.database)
        with conn:
            cur = conn.cursor()
            cur.execute(''' 
                SELECT image FROM winners 
                INNER JOIN prizes ON 
                winners.prize_id = prizes.prize_id
                WHERE user_id = ?''', (user_id, ))
            return cur.fetchall()

    def get_all_prizes(self):
        conn = sqlite3.connect(self.database)
        with conn:
            cur = conn.cursor()
            try:
                cur.execute('SELECT prize_id, image, used, price FROM prizes ORDER BY add_date DESC')
            except sqlite3.OperationalError:
                cur.execute('SELECT prize_id, image, used FROM prizes ORDER BY add_date DESC')
                prizes = cur.fetchall()
                return [(p[0], p[1], p[2], 50) for p in prizes]
            return cur.fetchall()

    def get_available_prizes(self):
        conn = sqlite3.connect(self.database)
        with conn:
            cur = conn.cursor()
            try:
                cur.execute('SELECT prize_id, image, price FROM prizes WHERE used = 0 ORDER BY price')
            except sqlite3.OperationalError:
                cur.execute('SELECT prize_id, image FROM prizes WHERE used = 0')
                prizes = cur.fetchall()
                return [(p[0], p[1], 50) for p in prizes]
            return cur.fetchall()

    def buy_prize(self, user_id, prize_id):
        conn = sqlite3.connect(self.database)
        with conn:
            cur = conn.cursor()
            try:
                cur.execute('SELECT price FROM prizes WHERE prize_id = ?', (prize_id,))
            except sqlite3.OperationalError:
                price = 50
            else:
                price_result = cur.fetchone()
                if not price_result:
                    return False, "Приз не найден"
                price = price_result[0]
            
            cur.execute('SELECT coins FROM users WHERE user_id = ?', (user_id,))
            coins_result = cur.fetchone()
            if not coins_result:
                return False, "Пользователь не найден"
            
            user_coins = coins_result[0]
            if user_coins < price:
                return False, f"Недостаточно монет. Нужно: {price}, есть: {user_coins}"
            
            cur.execute('UPDATE users SET coins = coins - ? WHERE user_id = ?', (price, user_id))
            win_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            cur.execute('''INSERT INTO winners (user_id, prize_id, win_time, win_type) 
                          VALUES (?, ?, ?, 'purchase')''', (user_id, prize_id, win_time))
            cur.execute('''INSERT INTO bonus_actions (user_id, action_type, coins_change, action_time) 
                          VALUES (?, 'prize_purchase', ?, ?)''', 
                       (user_id, -price, win_time))
            conn.commit()
            return True, "Приз успешно куплен!"

    def set_setting(self, key, value):
        conn = sqlite3.connect(self.database)
        with conn:
            conn.execute('INSERT OR REPLACE INTO bot_settings (setting_key, setting_value) VALUES (?, ?)', 
                        (key, value))
            conn.commit()

    def get_setting(self, key, default=None):
        conn = sqlite3.connect(self.database)
        cur = conn.cursor()
        cur.execute('SELECT setting_value FROM bot_settings WHERE setting_key = ?', (key,))
        result = cur.fetchone()
        return result[0] if result else default

    def get_all_settings(self):
        conn = sqlite3.connect(self.database)
        cur = conn.cursor()
        cur.execute('SELECT setting_key, setting_value FROM bot_settings')
        return dict(cur.fetchall())

    def is_admin(self, user_id):
        admins = self.get_setting('admins', '')
        return str(user_id) in admins.split(',')

    def add_admin(self, user_id):
        admins = self.get_setting('admins', '')
        admins_list = admins.split(',') if admins else []
        if str(user_id) not in admins_list:
            admins_list.append(str(user_id))
            self.set_setting('admins', ','.join(admins_list))
            return True
        return False

def hide_img(img_name):
    image = cv2.imread(f'img/{img_name}')
    if image is None:
        return False
    
    blurred_image = cv2.GaussianBlur(image, (15, 15), 0)
    pixelated_image = cv2.resize(blurred_image, (30, 30), interpolation=cv2.INTER_NEAREST)
    pixelated_image = cv2.resize(pixelated_image, (image.shape[1], image.shape[0]), interpolation=cv2.INTER_NEAREST)
    cv2.imwrite(f'hidden_img/{img_name}', pixelated_image)
    return True

def create_collage(image_paths):
    images = []
    for path in image_paths:
        image = cv2.imread(path)
        if image is not None:
            images.append(image)
        else:
            print(f"Ошибка загрузки: {path}")

    if not images:
        return None

    num_images = len(images)
    num_cols = floor(sqrt(num_images))
    num_rows = ceil(num_images / num_cols)
    
    collage = np.zeros((num_rows * images[0].shape[0], num_cols * images[0].shape[1], 3), dtype=np.uint8)
    
    for i, image in enumerate(images):
        row = i // num_cols
        col = i % num_cols
        collage[row*image.shape[0]:(row+1)*image.shape[0], 
                col*image.shape[1]:(col+1)*image.shape[1], :] = image
    
    return collage

if __name__ == '__main__':
    manager = DatabaseManager(DATABASE)
    manager.create_tables()
    
    if not os.path.exists('img'):
        os.makedirs('img')
    if not os.path.exists('hidden_img'):
        os.makedirs('hidden_img')
    
    prizes_img = os.listdir('img')
    if prizes_img:
        existing_prizes = [x[1] for x in manager.get_all_prizes()] if manager.get_all_prizes() else []
        for img in prizes_img:
            if img not in existing_prizes:
                manager.add_prize(img, None, 50)
            hidden_path = f'hidden_img/{img}'
            if not os.path.exists(hidden_path):
                hide_img(img)
    
    manager.set_setting('send_interval_hours', '1')
    manager.set_setting('max_winners_per_prize', '3')
    manager.set_setting('coins_per_win', '10')
    manager.set_setting('bonus_time_enabled', 'true')
    manager.set_setting('bonus_time_hour', '22')
    
    print("База данных инициализирована!")