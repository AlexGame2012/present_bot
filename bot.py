from telebot import TeleBot, types
from logic import *
import schedule
import threading
import time
from config import *
import os
import cv2
import tempfile
import json
from datetime import datetime

bot = TeleBot(API_TOKEN)
manager = DatabaseManager(DATABASE)

def gen_markup(prize_id):
    markup = types.InlineKeyboardMarkup()
    markup.row_width = 1
    markup.add(types.InlineKeyboardButton("🎁 Получить!", callback_data=f"prize_{prize_id}"))
    return markup

def gen_buy_markup(prize_id, price):
    markup = types.InlineKeyboardMarkup()
    markup.row_width = 2
    markup.add(
        types.InlineKeyboardButton(f"🛒 Купить за {price} монет", callback_data=f"buy_{prize_id}"),
        types.InlineKeyboardButton("❌ Отмена", callback_data="cancel")
    )
    return markup

def gen_admin_markup():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("📊 Статистика", "🎨 Добавить приз")
    markup.row("⚙️ Настройки", "👥 Пользователи")
    markup.row("💰 Бонусы", "🔄 Повторная отправка")
    markup.row("❌ Закрыть админ-панель")
    return markup

def send_message():
    result = manager.get_random_prize()
    if result:
        prize_id, img = result[:2]
        manager.mark_prize_used(prize_id)
        hide_img(img)
        
        users = manager.get_users()
        for user in users:
            try:
                with open(f'hidden_img/{img}', 'rb') as photo:
                    sent_msg = bot.send_photo(
                        user, 
                        photo, 
                        caption=f"🎯 Новый приз доступен!\nТолько 3 первых получат его!\n",
                        reply_markup=gen_markup(prize_id)
                    )
                    
                    if bonus_time_active():
                        bot.send_message(
                            user,
                            f"🌟 БОНУСНОЕ ВРЕМЯ! 🌟\n"
                            f"Сейчас {datetime.now().hour}:00 - время для повторной попытки!\n"
                            f"Проверь /failedprizes чтобы получить второй шанс!"
                        )
                    
            except Exception as e:
                print(f"Ошибка отправки пользователю {user}: {e}")
                manager.add_failed_prize(user, prize_id)

def bonus_time_active():
    try:
        hour = int(manager.get_setting('bonus_time_hour', '22'))
        return manager.get_setting('bonus_time_enabled', 'true').lower() == 'true' and datetime.now().hour == hour
    except:
        return False

def shedule_thread():
    interval = int(manager.get_setting('send_interval_hours', '1'))
    schedule.every(interval).hours.do(send_message)
    
    while True:
        schedule.run_pending()
        time.sleep(1)

@bot.message_handler(commands=['help'])
def handle_help(message):
    help_text = """
*🆘 СПРАВКА ПО КОМАНДАМ:*

*🎯 Основные команды:*
`/start` - главное меню и регистрация
`/help` - эта справка
`/coins` - проверить баланс монет
`/rating` - посмотреть рейтинг игроков
`/myscore` - твоя коллекция призов
`/get_my_score` - твоя коллекция призов (официальная)

*🛒 Магазин:*
`/shop` - открыть магазин призов
`/buy_X` - купить приз с номером X (пример: `/buy_3`)
`/failedprizes` - пропущенные призы со скидкой

*❓ Частые вопросы:*
• *Как получить приз?* - Будь в первых 3 нажавших на кнопку
• *Как получить монеты?* - Побеждай в розыгрышах
• *Что делать если пропустил приз?* - Используй `/failedprizes`
• *Как увидеть все призы?* - Используй `/myscore` или `/get_my_score`

*⏰ Автоматическая рассылка:* каждые несколько часов
*🎯 Лимит победителей:* 3 человека за приз
*💰 Монеты за победу:* 10 монет

*📞 Поддержка:* обратитесь к администратору
"""
    
    bot.send_message(message.chat.id, help_text, parse_mode='Markdown', disable_web_page_preview=True)

@bot.message_handler(commands=['start'])
def handle_start(message):
    user_id = message.chat.id
    username = message.from_user.username or message.from_user.first_name
    
    manager.add_user(user_id, username)
    
    interval = manager.get_setting('send_interval_hours', '1')
    coins_per_win = manager.get_setting('coins_per_win', '10')
    
    welcome_text = f"""
🎮 *Добро пожаловать в PRIZE BOT, {username}!* 🎮

*✨ ОСНОВНАЯ МЕХАНИКА:*
• Каждые *{interval} часа* ты получаешь новый зашифрованный приз
• *Только 3 первых* человека получают его!
• *За победу получаешь {coins_per_win} монет* 🪙
• Монетами можно покупать призы в магазине

*🏆 ВСЕ КОМАНДЫ БОТА:*

*🎯 Основные:*
`/start` - это сообщение
`/help` - справка по командам
`/coins` - твой баланс монет
`/rating` - топ-10 игроков
`/myscore` - твоя коллекция призов
`/get_my_score` - коллекция призов (официальная)

*🛒 Магазин и бонусы:*
`/shop` - магазин призов за монеты
`/failedprizes` - пропущенные призы (ВТОРОЙ ШАНС!)
`/buy_X` - купить приз (например `/buy_1`)

*🎁 Как получить призы:*
1. Жди автоматическую рассылку каждые {interval} часа
2. Будь в первых 3 нажавших "Получить!"
3. Или купи в магазине `/shop` за монеты

*💰 Зарабатывай монеты:*
• Побеждай в розыгрышах: *+{coins_per_win} монет*
• В бонусное время (обычно 22:00) - скидки!
• Пропущенные призы дешевле на 40%!

*🔄 Повторный шанс:*
Используй `/failedprizes` чтобы увидеть призы, которые ты пропустил!
Их можно купить со скидкой!

*🎯 Советы:*
• Включай уведомления, чтобы не пропустить призы!
• Накопи монеты и купи редкий приз!
• Собирай коллекцию через `/myscore` или `/get_my_score`

*💬 Что дальше?*
Просто жди первого приза! Он придет автоматически в течение {interval} часа.

*Удачи в охоте за призами!* 🚀
"""
    
    bot.send_message(user_id, welcome_text, parse_mode='Markdown', disable_web_page_preview=True)

    coins = manager.get_coins(user_id)
    if coins == 0:
        manager.add_coins(user_id, 20)
        bot.send_message(
            user_id,
            f"🎁 *БОНУС НОВИЧКА!*\nТы получил *20 стартовых монет*!\n"
            f"Проверь баланс: `/coins`",
            parse_mode='Markdown'
        )

@bot.message_handler(commands=['coins'])
def handle_coins(message):
    user_id = message.chat.id
    coins = manager.get_coins(user_id)
    bot.send_message(user_id, f"💰 Твой баланс: {coins} монет\n\n🏆 Зарабатывай монеты побеждая в розыгрышах!")

@bot.message_handler(commands=['shop'])
def handle_shop(message):
    user_id = message.chat.id
    prizes = manager.get_available_prizes()
    
    if not prizes:
        bot.send_message(user_id, "🛒 Магазин пуст. Новые призы скоро появятся!")
        return
    
    coins = manager.get_coins(user_id)
    text = f"🛒 МАГАЗИН ПРИЗОВ\n💰 Твой баланс: {coins} монет\n\n"
    
    for prize_id, image, price in prizes:
        text += f"🎁 Приз #{prize_id}\n💵 Цена: {price} монет\n/image_{prize_id} - посмотреть\n/buy_{prize_id} - купить\n\n"
    
    bot.send_message(user_id, text)

@bot.message_handler(commands=['buy_'])
def handle_buy_command(message):
    try:
        prize_id = int(message.text.split('_')[1])
        user_id = message.chat.id
        
        success, result_msg = manager.buy_prize(user_id, prize_id)
        
        if success:
            img_name = manager.get_prize_img(prize_id)
            with open(f'img/{img_name}', 'rb') as photo:
                bot.send_photo(
                    user_id,
                    photo,
                    caption=f"🎉 Поздравляем с покупкой!\n{result_msg}",
                    parse_mode='HTML'
                )
        else:
            bot.send_message(user_id, f"❌ {result_msg}")
    except Exception as e:
        bot.send_message(message.chat.id, "❌ Ошибка при покупке")

@bot.message_handler(commands=['failedprizes'])
def handle_failed_prizes(message):
    user_id = message.chat.id
    failed_prizes = manager.get_user_failed_prizes(user_id)
    
    if not failed_prizes:
        bot.send_message(
            user_id,
            "✅ *У тебя нет пропущенных призов!*\n\n"
            "Отлично! Ты не пропускаешь розыгрыши!\n"
            "Продолжай в том же духе! 🚀",
            parse_mode='Markdown'
        )
        return
    
    coins = manager.get_coins(user_id)
    
    text = f"""
🔄 *ПРОПУЩЕННЫЕ ПРИЗЫ - ВТОРОЙ ШАНС!* 🔄

💰 *Твой баланс:* `{coins} монет`

🎯 *Это твой второй шанс получить призы, которые ты пропустил!*
🛒 *Скидка 40% на все пропущенные призы!*

*Доступные призы:*
"""
    
    for prize_id, img_name in failed_prizes[:5]:
        discount_price = 30
        text += f"\n🎁 *Приз #{prize_id}*\n"
        text += f"💵 Цена: ~~50~~ → *{discount_price} монет* (скидка 40%!)\n"
        text += f"🛒 Купить: `/buy_{prize_id}`\n"
    
    if len(failed_prizes) > 5:
        text += f"\n*...и еще {len(failed_prizes)-5} призов*\n"
    
    text += """
*💡 Как купить:*
Просто используй команду `/buy_номер`
Например: `/buy_3`

*🎁 Что дают монеты?*
• Покупай пропущенные призы
• Выбирай любимые картинки
• Пополняй коллекцию

*Не упусти второй шанс!* 🚀
"""
    
    bot.send_message(user_id, text, parse_mode='Markdown')

@bot.message_handler(commands=['rating'])
def handle_rating(message):
    rating_data = manager.get_rating()
    
    if rating_data:
        text = "🏆 ТОП-10 ИГРОКОВ 🏆\n\n"
        for i, (username, count) in enumerate(rating_data, 1):
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
            text += f"{medal} {username:<15} - {count:>3} призов\n"
    else:
        text = "📊 Рейтинг пока пуст. Стань первым!"
    
    bot.send_message(message.chat.id, text)

@bot.message_handler(commands=['myscore'])
def handle_my_score(message):
    user_id = message.chat.id
    
    if user_id not in manager.get_users():
        bot.reply_to(message, "❌ Сначала зарегистрируйтесь /start")
        return
    
    bot.send_message(message.chat.id, "🖼️ Создаю твою коллекцию...")
    
    collage = create_collage_for_user(user_id)
    
    if collage is None:
        bot.send_message(message.chat.id, "📭 У тебя еще нет призов!")
        return
    
    with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp_file:
        temp_filename = tmp_file.name
        cv2.imwrite(temp_filename, collage)
    
    try:
        with open(temp_filename, 'rb') as photo:
            user_prizes = manager.get_winners_img(user_id)
            prize_count = len(user_prizes) if user_prizes else 0
            coins = manager.get_coins(user_id)
            
            caption = f"🎨 ТВОЯ КОЛЛЕКЦИЯ\n\n"
            caption += f"🏆 Призов: {prize_count}\n"
            caption += f"💰 Монет: {coins}\n"
            caption += f"🔓 Оригинал - твои призы\n"
            caption += f"🔒 Зашифровано - еще можно получить!"
            
            bot.send_photo(message.chat.id, photo, caption=caption)
    finally:
        os.unlink(temp_filename)

@bot.message_handler(commands=['get_my_score'])
def handle_get_my_score(message):
    user_id = message.chat.id
    
    if user_id not in manager.get_users():
        bot.send_message(user_id, "❌ Сначала зарегистрируйтесь: /start")
        return
    
    info = manager.get_winners_img(user_id)
    prizes = [x[0] for x in info] if info else []
    
    all_images = os.listdir('img')
    
    image_paths = []
    for img in all_images:
        if img in prizes:
            path = f'img/{img}'
        else:
            path = f'hidden_img/{img}'
        
        if os.path.exists(path):
            image_paths.append(path)
    
    if not image_paths:
        bot.send_message(user_id, "❌ Нет доступных изображений для создания коллажа.")
        return
    
    bot.send_message(user_id, "🖼️ Создаю ваш коллаж...")
    
    collage = create_collage(image_paths)
    
    if collage is not None:
        temp_filename = f"temp_collage_{user_id}.jpg"
        cv2.imwrite(temp_filename, collage)
        
        with open(temp_filename, 'rb') as photo:
            user_prizes = manager.get_winners_img(user_id)
            prize_count = len(user_prizes) if user_prizes else 0
            
            caption = f"🎯 ВАША КОЛЛЕКЦИЯ ПРИЗОВ\n\n"
            caption += f"🏆 Получено призов: {prize_count}\n"
            caption += f"📊 Всего доступно призов: {len(all_images)}\n"
            caption += f"🔓 Четкие изображения - ваши призы\n"
            caption += f"🔒 Зашифрованные - еще можно получить!"
            
            bot.send_photo(user_id, photo, caption=caption)
        
        os.remove(temp_filename)
    else:
        bot.send_message(user_id, "❌ Не удалось создать коллаж.")

def create_collage_for_user(user_id):
    info = manager.get_winners_img(user_id)
    prizes = [x[0] for x in info] if info else []
    
    all_images = os.listdir('img')
    
    image_paths = []
    for img in all_images:
        if img in prizes:
            path = f'img/{img}'
        else:
            path = f'hidden_img/{img}'
        
        if os.path.exists(path):
            image_paths.append(path)
    
    if not image_paths:
        return None
    
    return create_collage(image_paths)

@bot.message_handler(commands=['admin'])
def handle_admin(message):
    user_id = message.chat.id
    
    if not manager.is_admin(user_id):
        bot.send_message(user_id, "❌ У вас нет прав администратора!")
        return
    
    markup = gen_admin_markup()
    bot.send_message(user_id, "👑 ПАНЕЛЬ АДМИНИСТРАТОРА", reply_markup=markup)

@bot.message_handler(func=lambda message: message.text == "❌ Закрыть админ-панель")
def handle_close_admin(message):
    remove_markup = types.ReplyKeyboardRemove()
    bot.send_message(message.chat.id, "✅ Админ-панель закрыта", reply_markup=remove_markup)

@bot.message_handler(func=lambda message: message.text == "📊 Статистика")
def handle_stats(message):
    if not manager.is_admin(message.chat.id):
        return
    
    users_count = len(manager.get_users())
    prizes_count = len(manager.get_all_prizes())
    unused_prizes = manager.get_unused_prizes_count()
    settings = manager.get_all_settings()
    
    text = "📊 СТАТИСТИКА БОТА\n\n"
    text += f"👥 Пользователей: {users_count}\n"
    text += f"🎁 Всего призов: {prizes_count}\n"
    text += f"📦 Осталось призов: {unused_prizes}\n"
    text += f"⏰ Интервал рассылки: {settings.get('send_interval_hours', '1')} ч.\n"
    text += f"🏆 Победителей за приз: {settings.get('max_winners_per_prize', '3')}\n"
    text += f"💰 Монет за победу: {settings.get('coins_per_win', '10')}\n"
    
    bot.send_message(message.chat.id, text)

@bot.message_handler(func=lambda message: message.text == "🎨 Добавить приз")
def handle_add_prize(message):
    if not manager.is_admin(message.chat.id):
        return
    
    bot.send_message(message.chat.id, "📤 Отправьте изображение для добавления в качестве приза\nУкажите цену в монетах в подписи к фото")

@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    user_id = message.chat.id
    
    if manager.is_admin(user_id) and message.caption:
        try:
            file_id = message.photo[-1].file_id
            file_info = bot.get_file(file_id)
            downloaded_file = bot.download_file(file_info.file_path)
            
            filename = f"prize_{int(time.time())}.jpg"
            filepath = f"img/{filename}"
            
            with open(filepath, 'wb') as new_file:
                new_file.write(downloaded_file)
            
            try:
                price = int(message.caption)
            except:
                price = 50
            
            prize_id = manager.add_prize(filename, user_id, price)
            hide_img(filename)
            
            bot.reply_to(message, f"✅ Приз #{prize_id} добавлен!\nЦена: {price} монет\nФайл: {filename}")
        except Exception as e:
            bot.reply_to(message, f"❌ Ошибка: {e}")
    else:
        bot.reply_to(message, "📸 Отличное фото! Но добавлять призы могут только админы.")

@bot.message_handler(func=lambda message: message.text == "⚙️ Настройки")
def handle_settings(message):
    if not manager.is_admin(message.chat.id):
        return
    
    settings = manager.get_all_settings()
    
    text = "⚙️ НАСТРОЙКИ БОТА\n\n"
    for key, value in settings.items():
        text += f"{key}: {value}\n"
    
    text += "\n📝 Изменить настройку:\n/set_ключ_значение"
    
    bot.send_message(message.chat.id, text)

@bot.message_handler(commands=['set_'])
def handle_set_setting(message):
    if not manager.is_admin(message.chat.id):
        return
    
    try:
        parts = message.text[5:].split('_', 1)
        if len(parts) == 2:
            key, value = parts
            manager.set_setting(key, value)
            bot.reply_to(message, f"✅ Настройка '{key}' изменена на '{value}'")
        else:
            bot.reply_to(message, "❌ Формат: /set_ключ_значение")
    except Exception as e:
        bot.reply_to(message, f"❌ Ошибка: {e}")

@bot.message_handler(func=lambda message: message.text == "👥 Пользователи")
def handle_users(message):
    if not manager.is_admin(message.chat.id):
        return
    
    users = manager.get_all_users()
    
    text = "👥 ПОЛЬЗОВАТЕЛИ\n\n"
    for user_id, username, coins in users[:20]:
        text += f"👤 {username or user_id}\n💰 {coins} монет\nID: {user_id}\n\n"
    
    if len(users) > 20:
        text += f"\n... и еще {len(users)-20} пользователей"
    
    bot.send_message(message.chat.id, text)

@bot.message_handler(func=lambda message: message.text == "💰 Бонусы")
def handle_bonuses(message):
    if not manager.is_admin(message.chat.id):
        return
    
    markup = types.InlineKeyboardMarkup()
    markup.row(
        types.InlineKeyboardButton("➕ 10 монет", callback_data="bonus_add_10"),
        types.InlineKeyboardButton("➕ 50 монет", callback_data="bonus_add_50")
    )
    markup.row(
        types.InlineKeyboardButton("➕ 100 монет", callback_data="bonus_add_100"),
        types.InlineKeyboardButton("🎁 Всем по 10", callback_data="bonus_all_10")
    )
    
    bot.send_message(message.chat.id, "💰 УПРАВЛЕНИЕ БОНУСАМИ\nВыберите действие:", reply_markup=markup)

@bot.message_handler(func=lambda message: message.text == "🔄 Повторная отправка")
def handle_resend(message):
    if not manager.is_admin(message.chat.id):
        return
    
    markup = types.InlineKeyboardMarkup()
    markup.row(
        types.InlineKeyboardButton("📤 Отправить всем", callback_data="resend_all"),
        types.InlineKeyboardButton("🎯 Выбрать приз", callback_data="resend_select")
    )
    
    bot.send_message(message.chat.id, "🔄 ПОВТОРНАЯ ОТПРАВКА\nВыберите действие:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('prize_'))
def callback_prize(call):
    prize_id = int(call.data.split('_')[1])
    user_id = call.from_user.id
    
    winners_count = manager.get_winners_count(prize_id)
    max_winners = int(manager.get_setting('max_winners_per_prize', '3'))
    
    if winners_count < max_winners:
        success = manager.add_winner(user_id, prize_id)
        
        if success == 1:
            img_name = manager.get_prize_img(prize_id)
            
            if img_name:
                with open(f'img/{img_name}', 'rb') as photo:
                    bot.send_photo(
                        user_id,
                        photo,
                        caption="🎉 *ПОЗДРАВЛЯЕМ С ВЫИГРЫШЕМ!*\n\n"
                               f"🏆 Ты получил приз #{prize_id}\n"
                               f"💰 *+10 монет* добавлены к твоему балансу!\n\n"
                               f"*Что дальше?*\n"
                               f"• Проверь баланс: `/coins`\n"
                               f"• Посмотри коллекцию: `/myscore` или `/get_my_score`\n"
                               f"• Магазин призов: `/shop`",
                        parse_mode='Markdown'
                    )
                
                bot.answer_callback_query(call.id, "🎁 Поздравляем с выигрышем!")
                
                try:
                    bot.edit_message_reply_markup(
                        chat_id=call.message.chat.id,
                        message_id=call.message.message_id,
                        reply_markup=None
                    )
                    bot.edit_message_caption(
                        chat_id=call.message.chat.id,
                        message_id=call.message.message_id,
                        caption=f"✅ *Приз получен!*\n"
                               f"Осталось мест: *{max_winners - winners_count - 1}/{max_winners}*",
                        parse_mode='Markdown'
                    )
                except:
                    pass
            else:
                bot.answer_callback_query(call.id, "❌ Ошибка: приз не найден")
        else:
            bot.answer_callback_query(call.id, "⚠️ Ты уже получал этот приз!")
            bot.send_message(
                user_id,
                "ℹ️ *Ты уже получал этот приз!*\n\n"
                "Но не расстраивайся!\n"
                "• Жди следующий приз через несколько часов\n"
                "• Или купи другие призы в `/shop`",
                parse_mode='Markdown'
            )
    else:
        bot.answer_callback_query(call.id, "⏳ Все призы уже разыграны!")
        bot.send_message(
            user_id,
            "😔 *Все призы этого розыгрыша уже разобрали!*\n\n"
            "*Не унывай!*\n"
            "• Следующий приз будет через несколько часов\n"
            "• Посмотри пропущенные призы: `/failedprizes`\n"
            "• Или магазин: `/shop`",
            parse_mode='Markdown'
        )

@bot.callback_query_handler(func=lambda call: call.data.startswith('buy_'))
def callback_buy(call):
    prize_id = int(call.data.split('_')[1])
    user_id = call.from_user.id
    
    success, result_msg = manager.buy_prize(user_id, prize_id)
    
    if success:
        img_name = manager.get_prize_img(prize_id)
        with open(f'img/{img_name}', 'rb') as photo:
            bot.send_photo(
                user_id,
                photo,
                caption=f"🎉 Поздравляем с покупкой!\n{result_msg}",
                parse_mode='HTML'
            )
        bot.answer_callback_query(call.id, "✅ Приз куплен!")
    else:
        bot.answer_callback_query(call.id, f"❌ {result_msg}")

@bot.callback_query_handler(func=lambda call: call.data.startswith('bonus_'))
def callback_bonus(call):
    if not manager.is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "❌ Нет прав!")
        return
    
    action = call.data
    
    if action == "bonus_all_10":
        users = manager.get_users()
        for user in users:
            manager.add_coins(user, 10)
        bot.answer_callback_query(call.id, f"✅ Все {len(users)} пользователей получили по 10 монет!")
    elif "bonus_add_" in action:
        amount = int(action.split('_')[2])
        bot.send_message(call.from_user.id, f"Введите ID пользователя для начисления {amount} монет:")
        bot.register_next_step_handler(call.message, lambda m: process_bonus_add(m, amount))
        bot.answer_callback_query(call.id, "✏️ Введите ID пользователя")

def process_bonus_add(message, amount):
    try:
        user_id = int(message.text)
        manager.add_coins(user_id, amount)
        bot.reply_to(message, f"✅ Пользователю {user_id} начислено {amount} монет")
    except:
        bot.reply_to(message, "❌ Ошибка. Введите корректный ID")

@bot.callback_query_handler(func=lambda call: call.data.startswith('resend_'))
def callback_resend(call):
    if not manager.is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "❌ Нет прав!")
        return
    
    action = call.data
    
    if action == "resend_all":
        prizes = manager.get_all_prizes()
        for prize_id, img_name, used, price in prizes:
            if not used:
                hide_img(img_name)
                users = manager.get_users()
                for user in users:
                    try:
                        with open(f'hidden_img/{img_name}', 'rb') as photo:
                            bot.send_photo(
                                user,
                                photo,
                                caption=f"🔄 ПОВТОРНАЯ ОТПРАВКА\nПриз #{prize_id}",
                                reply_markup=gen_markup(prize_id)
                            )
                    except:
                        pass
        bot.answer_callback_query(call.id, "✅ Все призы повторно отправлены!")
    elif action == "resend_select":
        bot.send_message(call.from_user.id, "Введите ID приза для повторной отправки:")
        bot.register_next_step_handler(call.message, process_resend_select)
        bot.answer_callback_query(call.id, "✏️ Введите ID приза")

def process_resend_select(message):
    try:
        prize_id = int(message.text)
        img_name = manager.get_prize_img(prize_id)
        
        if img_name:
            hide_img(img_name)
            users = manager.get_users()
            for user in users:
                try:
                    with open(f'hidden_img/{img_name}', 'rb') as photo:
                        bot.send_photo(
                            user,
                            photo,
                            caption=f"🔄 ПОВТОРНАЯ ОТПРАВКА\nПриз #{prize_id}",
                            reply_markup=gen_markup(prize_id)
                        )
                except:
                    pass
            bot.reply_to(message, f"✅ Приз #{prize_id} повторно отправлен {len(users)} пользователям")
        else:
            bot.reply_to(message, "❌ Приз не найден")
    except:
        bot.reply_to(message, "❌ Ошибка. Введите корректный ID приза")

def polling_thread():
    bot.polling(none_stop=True)

if __name__ == '__main__':
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
    
    admin_id = input("Введите ваш Telegram ID для назначения администратором: ")
    if admin_id.isdigit():
        manager.add_admin(int(admin_id))
        print(f"✅ Пользователь {admin_id} назначен администратором")
    
    polling_thread = threading.Thread(target=polling_thread)
    polling_schedule = threading.Thread(target=shedule_thread)
    
    polling_thread.start()
    polling_schedule.start()
    
    print("🤖 Бот запущен!")