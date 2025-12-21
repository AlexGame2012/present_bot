from telebot import TeleBot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from logic import *
import schedule
import threading
import time
from config import *
import os
import cv2
import tempfile

bot = TeleBot(API_TOKEN)

def gen_markup(id):
    markup = InlineKeyboardMarkup()
    markup.row_width = 1
    markup.add(InlineKeyboardButton("Получить!", callback_data=id))
    return markup

@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    prize_id = call.data
    user_id = call.message.chat.id

    img = manager.get_prize_img(prize_id)
    with open(f'img/{img}', 'rb') as photo:
        bot.send_photo(user_id, photo)

def send_message():
    result = manager.get_random_prize()
    if result:
        prize_id, img = result[:2]
        manager.mark_prize_used(prize_id)
        hide_img(img)
        for user in manager.get_users():
            with open(f'hidden_img/{img}', 'rb') as photo:
                bot.send_photo(user, photo, reply_markup=gen_markup(id=prize_id))

def shedule_thread():
    schedule.every().hour.do(send_message) 
    while True:
        schedule.run_pending()
        time.sleep(1)

@bot.message_handler(commands=['start'])
def handle_start(message):
    user_id = message.chat.id
    if user_id in manager.get_users():
        bot.reply_to(message, "Ты уже зарегистрирован!")
    else:
        manager.add_user(user_id, message.from_user.username or str(user_id))
        bot.reply_to(message, """Привет! Добро пожаловать! 
Тебя успешно зарегистрировали!
Каждый час тебе будут приходить новые картинки и у тебя будет шанс их получить!
Для этого нужно быстрее всех нажать на кнопку 'Получить!'

Только три первых пользователя получат картинку!

📊 Доступные команды:
/rating - посмотреть рейтинг победителей
/myscore - посмотреть свою коллекцию призов""")

@bot.message_handler(commands=['rating'])
def handle_rating(message):
    rating_data = manager.get_rating()  
    
    if rating_data:
        table_header = "| USERNAME      | PRIZES WON   |\n" + "─" * 31 + "\n"
        
        rows = []
        for i, (username, count) in enumerate(rating_data, 1):
            if i == 1:
                place = "🥇 "
            elif i == 2:
                place = "🥈 "
            elif i == 3:
                place = "🥉 "
            else:
                place = f"{i}. "
            
            username_display = str(username)[:12] if len(str(username)) > 12 else str(username)
            rows.append(f"{place}{username_display:<15} - {count:>3} призов")
        
        table_content = "\n".join(rows)
        result = f"🏆 <b>ТОП-10 ПОБЕДИТЕЛЕЙ</b> 🏆\n\n<code>{table_content}</code>"
    else:
        result = "📊 Рейтинг пока пуст. Стань первым победителем!"
    
    bot.send_message(message.chat.id, result, parse_mode='HTML')

@bot.message_handler(commands=['myscore'])
def handle_my_score(message):
    user_id = message.chat.id
    
    if user_id not in manager.get_users():
        bot.reply_to(message, "❌ Вы не зарегистрированы! Используйте /start для регистрации.")
        return
    
    bot.send_message(message.chat.id, "🖼️ Создаю вашу коллекцию призов...")
    
    collage = create_collage(user_id)
    
    if collage is None:
        bot.send_message(message.chat.id, "📭 У вас еще нет призов или произошла ошибка создания коллажа.")
        return
    
    with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp_file:
        temp_filename = tmp_file.name
        cv2.imwrite(temp_filename, collage)
    
    try:
        with open(temp_filename, 'rb') as photo:
            user_prizes = manager.get_winners_img(user_id)
            prize_count = len(user_prizes) if user_prizes else 0
            
            caption = f"🎨 <b>Ваша коллекция призов</b>\n\n"
            caption += f"🏆 Выиграно призов: <b>{prize_count}</b>\n"
            caption += f"🔓 Оригинальные картинки - призы, которые вы получили\n"
            caption += f"🔒 Зашифрованные картинки - призы, которые еще можно получить\n\n"
            caption += "Продолжайте участвовать, чтобы собрать все призы! 🚀"
            
            bot.send_photo(message.chat.id, photo, caption=caption, parse_mode='HTML')
    finally:
        os.unlink(temp_filename)

@bot.callback_query_handler(func=lambda call: call.data.startswith('prize_'))
def callback_query_new(call):
    prize_id = int(call.data.split('_')[1]) 
    user_id = call.from_user.id
    
    winners_count = manager.get_winners_count(prize_id)
    
    if winners_count < 3:
        success = manager.add_winner(user_id, prize_id)
        
        if success == 1:  
            img_name = manager.get_prize_img(prize_id)
            
            if img_name:
                with open(f'img/{img_name}', 'rb') as photo:
                    bot.send_photo(
                        user_id, 
                        photo, 
                        caption="🎉 <b>Поздравляем! Ты получил приз!</b> 🎉\n"
                                "Картинка теперь твоя!",
                        parse_mode='HTML'
                    )
                
                bot.answer_callback_query(call.id, "🎁 Поздравляем с выигрышем!")
                
                bot.edit_message_reply_markup(
                    chat_id=call.message.chat.id,
                    message_id=call.message.message_id,
                    reply_markup=None
                )
                bot.edit_message_caption(
                    chat_id=call.message.chat.id,
                    message_id=call.message.message_id,
                    caption=f"✅ Приз получен пользователем!\n"
                           f"Осталось мест: {3 - winners_count - 1}/3"
                )
                
            else:
                bot.answer_callback_query(call.id, "❌ Ошибка: приз не найден")
                
        else: 
            bot.answer_callback_query(call.id, "⚠️ Ты уже получал этот приз!")
            bot.send_message(
                user_id, 
                "📦 Ты уже получал этот приз ранее!\n"
                "Попробуй получить другие призы!"
            )
            
    else:  
        bot.answer_callback_query(call.id, "⏳ Все призы уже разыграны!")
        bot.send_message(
            user_id, 
            "😔 <b>К сожалению, все призы этого типа уже разобрали!</b>\n"
            "Не расстраивайся, попробуй получить другие призы! 🍀",
            parse_mode='HTML'
        )

def polling_thread():
    bot.polling(none_stop=True)

if __name__ == '__main__':
    if not os.path.exists('hidden_img'):
        os.makedirs('hidden_img')
    
    manager = DatabaseManager(DATABASE)
    manager.create_tables()
    
    prizes_img = os.listdir('img')
    if prizes_img:
        existing_prizes = manager.get_all_prizes()
        if not existing_prizes:
            data = [(x,) for x in prizes_img]
            manager.add_prize(data)
        
        for img in prizes_img:
            hidden_path = f'hidden_img/{img}'
            if not os.path.exists(hidden_path):
                hide_img(img)
    
    polling_thread = threading.Thread(target=polling_thread)
    polling_shedule = threading.Thread(target=shedule_thread)
    
    polling_thread.start()
    polling_shedule.start()