from telebot import TeleBot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from logic import *
import schedule
import threading
import time
from config import *

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
    prize_id, img = manager.get_random_prize()[:2]
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
        manager.add_user(user_id, message.from_user.username)
        bot.reply_to(message, """Привет! Добро пожаловать! 
Тебя успешно зарегистрировали!
Каждый час тебе будут приходить новые картинки и у тебя будет шанс их получить!
Для этого нужно быстрее всех нажать на кнопку 'Получить!'

Только три первых пользователя получат картинку!)""")

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
    # Проверяем какое имя базы данных используется в config.py
    manager = DatabaseManager(DATABASE)
    manager.create_tables()

    polling_thread = threading.Thread(target=polling_thread)
    polling_shedule = threading.Thread(target=shedule_thread)

    polling_thread.start()
    polling_shedule.start()