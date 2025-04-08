import telebot
import sqlite3
import time

API_TOKEN = "7847051026:AAG9_R6fkmcUiOyBcC4t29MAxeh7kq74XsI"
CHANNEL_ID = -1002580904282  # Kanal ID (manfiy belgili)
ADMIN_ID = 6870812534 

bot = telebot.TeleBot(API_TOKEN)

# Ma'lumotlar bazasiga ulanish va jadval yaratish
conn = sqlite3.connect('KINO.db', check_same_thread=False)
cursor = conn.cursor()
cursor.execute('''CREATE TABLE IF NOT EXISTS movies (
    code TEXT PRIMARY KEY,
    message_id INTEGER,
    title TEXT,
    file_id TEXT
)''')

conn.commit()
@bot.message_handler(content_types=['video'], func=lambda message: message.from_user.id == ADMIN_ID)
def upload_video(message):
    try:
        file_id = message.video.file_id
        sent_message = bot.send_video(CHANNEL_ID, file_id)
        bot.reply_to(message, "Video yuklandi!\nIltimos, kino kodini kiriting:")
        bot.register_next_step_handler(message, get_code_step, sent_message.message_id, file_id)
    except Exception as e:
        bot.reply_to(message, f"Xatolik yuz berdi: {e}")
def get_code_step(message, message_id, file_id):
    code = message.text
    cursor.execute("SELECT code FROM movies WHERE code = ?", (code,))
    if cursor.fetchone():
        return bot.reply_to(message, "Bu kod allaqachon mavjud.")
    msg = bot.reply_to(message, "Endi kino nomini (izohini) kiriting:")
    bot.register_next_step_handler(msg, save_movie_info, message_id, code, file_id)
def save_movie_info(message, message_id, code, file_id):
    title = message.text
    try:
        cursor.execute("INSERT INTO movies (code, message_id, title, file_id) VALUES (?, ?, ?, ?)",
                       (code, message_id, title, file_id))
        conn.commit()
        bot.reply_to(message, "Kino kodi, nomi va fayl ID saqlandi!")
    except Exception as e:
        bot.reply_to(message, f"Xatolik yuz berdi: {e}")
try:
    cursor.execute("ALTER TABLE movies ADD COLUMN file_id TEXT")
    conn.commit()
except sqlite3.OperationalError:
    pass  # allaqachon mavjud bo'lsa xatolik chiqmasin


# Kino tahrirlash
@bot.message_handler(commands=['edit'])
def edit_movie_start(message):
    if message.from_user.id != ADMIN_ID:
        return
    msg = bot.reply_to(message, "Tahrirlamoqchi bo‘lgan kino kodini kiriting:")
    bot.register_next_step_handler(msg, choose_edit_action)

def choose_edit_action(message):
    old_code = message.text
    cursor.execute("SELECT title FROM movies WHERE code = ?", (old_code,))
    result = cursor.fetchone()
    if not result:
        return bot.reply_to(message, "Bunday kod topilmadi.")
    
    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(telebot.types.InlineKeyboardButton("Kodini o‘zgartirish", callback_data=f"edit_code:{old_code}"))
    markup.add(telebot.types.InlineKeyboardButton("Nomi (izoh)ni o‘zgartirish", callback_data=f"edit_title:{old_code}"))
    bot.send_message(message.chat.id, "Qaysi qismini tahrirlaysiz?", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("edit_code:") or call.data.startswith("edit_title:"))
def edit_field_handler(call):
    action, old_code = call.data.split(":")
    if action == "edit_code":
        msg = bot.send_message(call.message.chat.id, f"Yangi kodni kiriting (eski: {old_code}):")
        bot.register_next_step_handler(msg, update_code, old_code)
    else:
        msg = bot.send_message(call.message.chat.id, f"Yangi nom (izoh) ni kiriting (kod: {old_code}):")
        bot.register_next_step_handler(msg, update_title, old_code)

def update_code(message, old_code):
    new_code = message.text
    try:
        cursor.execute("UPDATE movies SET code = ? WHERE code = ?", (new_code, old_code))
        conn.commit()
        bot.reply_to(message, "Kod yangilandi.")
    except:
        bot.reply_to(message, "Xatolik yuz berdi.")

def update_title(message, code):
    new_title = message.text
    try:
        cursor.execute("UPDATE movies SET title = ? WHERE code = ?", (new_title, code))
        conn.commit()
        bot.reply_to(message, "Kino nomi yangilandi.")
    except:
        bot.reply_to(message, "Xatolik yuz berdi.")

# Admin tomonidan kino o'chirish
@bot.message_handler(commands=['delete'])
def delete_movie_start(message):
    if message.from_user.id != ADMIN_ID:
        return
    msg = bot.reply_to(message, "O'chirmoqchi bo‘lgan kino kodini kiriting:")
    bot.register_next_step_handler(msg, delete_movie_step)

def delete_movie_step(message):
    code = message.text
    cursor.execute("SELECT message_id FROM movies WHERE code = ?", (code,))
    result = cursor.fetchone()
    if result:
        message_id = result[0]
        try:
            bot.delete_message(CHANNEL_ID, message_id)
        except:
            pass
        cursor.execute("DELETE FROM movies WHERE code = ?", (code,))
        conn.commit()
        bot.reply_to(message, "Kino o‘chirildi.")
    else:
        bot.reply_to(message, "Bunday kod mavjud emas.")

# Foydalanuvchiga kino kodlarini ko'rsatish
@bot.message_handler(commands=['kino_list'])
def list_all_movies(message):
    cursor.execute("SELECT code, title FROM movies")
    movies = cursor.fetchall()
    if movies:
        text = "\n".join([f"🎞️ *{title}* — Kod:` {code}`" for code, title in movies])
        bot.send_message(message.chat.id, f"*Kinolar ro'yxati:*\n{text}", parse_mode="Markdown")
    else:
        bot.send_message(message.chat.id, "Hech qanday kino mavjud emas.")

# Foydalanuvchi tomonidan kod yuborilganda
@bot.message_handler(func=lambda message: message.text.isdigit())
def send_movie_with_caption(message):
    movie_code = message.text

    # Kino kodini topish
    cursor.execute('SELECT title, file_id FROM movies WHERE code = ?', (movie_code,))
    result = cursor.fetchone()

    if result:
        title, file_id = result
        try:
            # Foydalanuvchiga izoh bilan video yuborish
            bot.send_video(chat_id=message.chat.id, video=file_id, caption=f"🎬 {title}")
        except Exception as e:
            bot.reply_to(message, "Kino yuborishda xatolik yuz berdi.")
    else:
        bot.reply_to(message, "Kino kodi noto‘g‘ri yoki topilmadi.")

#start handler        
@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "Salom! Kino kodini yuboring:")

#command handler
# Admin komandasi
@bot.message_handler(commands=['admin'])
def admin(message):
    if message.from_user.id == ADMIN_ID:
        admin_text = """
        Salom admin! Quyidagi komandalarni ishlatishingiz mumkin:

        /kino_list - Kino ro'yxatini ko'rish
        /edit - Kino tahrirlash (faqat adminlar uchun)
        /delete - Kino o'chirish (faqat adminlar uchun)
        """
        bot.reply_to(message, admin_text)
    else:
        bot.reply_to(message, "Siz admin emassiz.")

# Foydalanuvchiga yordam (help) komandasi
@bot.message_handler(commands=['help'])
def send_help(message):
    help_text = """
    Salom! Quyidagi komandalarni ishlatishingiz mumkin:

    /start - Botni ishga tushurish
    /help - Yordam olish
    /kino_list - Kino ro'yxatini ko'rish (faqat foydalanuvchilar uchun)
    /admin - Admin paneliga kirish (faqat adminlar uchun)

    Kino kodi bilan video olish uchun, kino kodini yuboring.
    """
    bot.reply_to(message, help_text)

while True:
    try:
        bot.polling(non_stop=True)
    except Exception as e:
        print(f"Xato yuz berdi: {e}")
        time.sleep(10)  # Xatolik yuz berganidan keyin 10 soniya kutish

