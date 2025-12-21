import sqlite3
from datetime import datetime
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
                user_name TEXT
            )
            ''')

            conn.execute('''
            CREATE TABLE IF NOT EXISTS prizes (
                prize_id INTEGER PRIMARY KEY,
                image TEXT,
                used INTEGER DEFAULT 0
            )
            ''')

            conn.execute('''
            CREATE TABLE IF NOT EXISTS winners (
                user_id INTEGER,
                prize_id INTEGER,
                win_time TEXT,
                FOREIGN KEY(user_id) REFERENCES users(user_id),
                FOREIGN KEY(prize_id) REFERENCES prizes(prize_id)
            )
            ''')

            conn.commit()

    def add_user(self, user_id, user_name):
        conn = sqlite3.connect(self.database)
        with conn:
            conn.execute('INSERT OR IGNORE INTO users VALUES (?, ?)', (user_id, user_name))
            conn.commit()

    def add_prize(self, data):
        conn = sqlite3.connect(self.database)
        with conn:
            conn.executemany('''INSERT INTO prizes (image) VALUES (?)''', data)
            conn.commit()

    def add_winner(self, user_id, prize_id):
        win_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        conn = sqlite3.connect(self.database)
        with conn:
            cur = conn.cursor() 
            cur.execute("SELECT * FROM winners WHERE user_id = ? AND prize_id = ?", (user_id, prize_id))
            if cur.fetchall():
                return 0
            else:
                conn.execute('''INSERT INTO winners (user_id, prize_id, win_time) VALUES (?, ?, ?)''', (user_id, prize_id, win_time))
                conn.commit()
                return 1

    def mark_prize_used(self, prize_id):
        conn = sqlite3.connect(self.database)
        with conn:
            conn.execute('''UPDATE prizes SET used = 1 WHERE prize_id = ?''', (prize_id,))
            conn.commit()

    def get_users(self):
        conn = sqlite3.connect(self.database)
        cur = conn.cursor()
        cur.execute('SELECT user_id FROM users')
        return [x[0] for x in cur.fetchall()] 
        
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
                GROUP BY w.user_id
                ORDER BY prize_count DESC
                LIMIT 10
            ''')
            return cur.fetchall()
    
    def get_winners_img(self, user_id):
        """Получает список картинок, которые выиграл пользователь"""
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
        """Получает список всех призов"""
        conn = sqlite3.connect(self.database)
        with conn:
            cur = conn.cursor()
            cur.execute('SELECT image FROM prizes')
            return [x[0] for x in cur.fetchall()]
  
def hide_img(img_name):
    image = cv2.imread(f'img/{img_name}')
    blurred_image = cv2.GaussianBlur(image, (15, 15), 0)
    pixelated_image = cv2.resize(blurred_image, (30, 30), interpolation=cv2.INTER_NEAREST)
    pixelated_image = cv2.resize(pixelated_image, (image.shape[1], image.shape[0]), interpolation=cv2.INTER_NEAREST)
    cv2.imwrite(f'hidden_img/{img_name}', pixelated_image)

def create_collage(user_id):
    """Создает коллаж с призами пользователя"""
    db = DatabaseManager(DATABASE)
    
    user_prizes_data = db.get_winners_img(user_id)
    user_prizes = [x[0] for x in user_prizes_data] if user_prizes_data else []
    
    all_prizes = db.get_all_prizes()
    
    if not all_prizes:
        return None
    
    image_paths = []
    for prize in all_prizes:
        if prize in user_prizes:
            path = f'img/{prize}'
        else:
            path = f'hidden_img/{prize}'
        
        if os.path.exists(path):
            image_paths.append(path)
        else:
            continue
    
    if not image_paths:
        return None
    
    images = []
    for path in image_paths:
        image = cv2.imread(path)
        if image is not None:
            image = cv2.resize(image, (200, 200))
            images.append(image)
    
    if not images:
        return None
    
    num_images = len(images)
    num_cols = min(floor(sqrt(num_images)), 3) 
    num_rows = ceil(num_images / num_cols)
    
    img_height, img_width = images[0].shape[:2]
    
    collage = np.zeros((num_rows * img_height, num_cols * img_width, 3), dtype=np.uint8)
    
    for i, image in enumerate(images):
        row = i // num_cols
        col = i % num_cols
        collage[row * img_height:(row + 1) * img_height, 
                col * img_width:(col + 1) * img_width, :] = image
    
    return collage

if __name__ == '__main__':
    manager = DatabaseManager(DATABASE)
    manager.create_tables()
    prizes_img = os.listdir('img')
    data = [(x,) for x in prizes_img]
    manager.add_prize(data)
    
    if not os.path.exists('hidden_img'):
        os.makedirs('hidden_img')
    
    for img in prizes_img:
        hide_img(img)