# Present Bot - Telegram Bot для розыгрыша подарков

![Python](https://img.shields.io/badge/Python-3.8%2B-blue)
![Telegram Bot](https://img.shields.io/badge/Telegram-Bot-blue)
![SQLite](https://img.shields.io/badge/Database-SQLite-green)
![License](https://img.shields.io/badge/License-MIT-yellow)

Telegram-бот для автоматического розыгрыша подарков с функцией скрытия изображений и автоматической раздачей призов.

## 📋 Основные возможности

- 🤖 Автоматическая раздача подарков пользователям Telegram
- 🎁 Система управления призами (добавление, скрытие, раздача)
- ⏰ Автоматическая раздача подарков каждую минуту
- 🖼️ Функция скрытия изображений призов (пикселизаци
- ```я)
- 📊 Ведение базы данных пользователей и победителей
- 🎯 Случайный выбор победителей
- 🔒 Защита от повторного получения приза одним пользователем

## 🚀 Установка и запуск

### 1. Клонирование репозитория
```bash
git clone https://github.com/AlexGame2012/present_bot.git
cd present_bot 

### 2. Создание виртуального окружения
```bash
python -m venv venv
source venv/bin/activate   # Для Linux/Mac
# или
```bash
venv\Scripts\activate      # Для Windows

### 3. Установка зависимостей

``` pip install -r requirements.txt ```

### 4. Настройка конфигурации
Создайте файл config.py в корневой директории:
```python
# config.py
BOT_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"  # Получите у @BotFather
DATABASE = "database.db"  # Название файла базы данных
```

### 5. Подготовка изображений

Создайте папку img/ и поместите туда изображения призов
Папка hidden_img/ будет создана автоматически для скрытых изображений

### 6. Запуск бота

 ``` python main.py ```

## 🗂️ Структура проекта

``` present_bot/
├── main.py              # Основной файл бота
├── database.py          # Модуль работы с базой данных
├── config.py           # Конфигурационный файл (создается вручную)
├── requirements.txt    # Зависимости проекта
├── database.db        # Файл базы данных (создается автоматически)
├── img/               # Папка с изображениями призов
├── hidden_img/       # Папка со скрытыми изображениями
└── README.md         # Этот файл
```

## 📦 Зависимости
 ```
python-telegram-bot==20.3
opencv-python==4.8.1.78
schedule==1.2.0
APScheduler==3.10.4
```

## 📝 Лицензия
Этот проект распространяется под лицензией MIT. Подробнее см. в файле [LICENSE](https://github.com/AlexGame2012/present_bot/new/main/LICENSE).

## 👨‍💻 Автор AlexStudio Code

Site: alexstudiocode.ru

Email: info@alexstudiocode.ru
       support@alexstudiocode.ru
