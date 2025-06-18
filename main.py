import os
import sqlite3
from datetime import datetime
from flask import Flask, render_template, jsonify, request
from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext
import threading

# تهيئة تطبيق Flask
app = Flask(__name__)

# إعدادات البوت
GROUP_ID = -1002445433249
ADMIN_ID = 6243639789
BOT_TOKEN = "6037757983:AAG5qtoMZrIuUMpI8-Mta3KtjW1Qu2Y2iO8"

# تهيئة قاعدة البيانات
def init_db():
    conn = sqlite3.connect('interactions.db')
    cursor = conn.cursor()

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        first_name TEXT,
        last_name TEXT,
        message_count INTEGER DEFAULT 0,
        last_interaction TEXT
    )
    ''')

    conn.commit()
    conn.close()

init_db()

# ============== مسارات Flask ==============

@app.route('/')
def dashboard():
    return render_template('dashboard.html')

@app.route('/api/top_members')
def api_top_members():
    conn = sqlite3.connect('interactions.db')
    cursor = conn.cursor()

    cursor.execute('''
    SELECT user_id, username, first_name, last_name, message_count 
    FROM users 
    ORDER BY message_count DESC 
    LIMIT 20
    ''')

    members = []
    for row in cursor.fetchall():
        members.append({
            'user_id': row[0],
            'username': row[1],
            'first_name': row[2] or "",
            'last_name': row[3] or "",
            'message_count': row[4]
        })

    conn.close()
    return jsonify(members)
    
@app.route('/index')
def index():
    return render_template('index.html')
    
@app.route('/store')
def store():
    return render_template('store.html')

@app.route('/contests')
def contests():
    return render_template('contests.html')

@app.route('/report')
def report():
    return render_template('report.html')

@app.route('/support')
def support():
    return render_template('support.html')

@app.route('/law')
def law():
    return render_template('law.html')

# ============== أوامر التليجرام ==============

def start(update: Update, context: CallbackContext):
    if update.effective_chat.id == GROUP_ID:
        update.message.reply_text('مرحباً بكم في بوت تفاعل SM 1%! استخدم /top لرؤية الأكثر تفاعلاً')

def track_message(update: Update, context: CallbackContext):
    if update.effective_chat.id != GROUP_ID:
        return

    user = update.effective_user
    now = datetime.now().isoformat()

    conn = sqlite3.connect('interactions.db')
    cursor = conn.cursor()

    # إدخال أو تحديث بيانات المستخدم
    cursor.execute('''
    INSERT OR IGNORE INTO users (user_id, username, first_name, last_name, message_count, last_interaction)
    VALUES (?, ?, ?, ?, 0, ?)
    ''', (user.id, user.username, user.first_name, user.last_name, now))

    cursor.execute('''
    UPDATE users 
    SET message_count = message_count + 1,
        username = ?,
        first_name = ?,
        last_name = ?,
        last_interaction = ?
    WHERE user_id = ?
    ''', (user.username, user.first_name, user.last_name, now, user.id))

    conn.commit()
    conn.close()

def top_members(update: Update, context: CallbackContext):
    if update.effective_chat.id != GROUP_ID:
        return

    conn = sqlite3.connect('interactions.db')
    cursor = conn.cursor()

    cursor.execute('''
    SELECT username, first_name, last_name, message_count 
    FROM users 
    ORDER BY message_count DESC 
    LIMIT 10
    ''')

    response = "🏆 أفضل 10 أعضاء متفاعلين:\n\n"
    for i, (username, first_name, last_name, count) in enumerate(cursor.fetchall(), 1):
        name = f"@{username}" if username else f"{first_name} {last_name}".strip()
        response += f"{i}. {name} - {count} رسالة\n"

    update.message.reply_text(response)
    conn.close()

def my_rank(update: Update, context: CallbackContext):
    if update.effective_chat.id != GROUP_ID:
        return

    user = update.effective_user
    conn = sqlite3.connect('interactions.db')
    cursor = conn.cursor()

    # الحصول على عدد رسائل المستخدم
    cursor.execute('SELECT message_count FROM users WHERE user_id = ?', (user.id,))
    user_data = cursor.fetchone()

    if not user_data:
        update.message.reply_text("لم يتم العثور على بيانات تفاعل لك.")
        conn.close()
        return

    # الحصول على ترتيب المستخدم
    cursor.execute('''
    SELECT COUNT(*) FROM users 
    WHERE message_count > ?
    ''', (user_data[0],))

    rank = cursor.fetchone()[0] + 1
    message_count = user_data[0]

    conn.close()

    name = f"@{user.username}" if user.username else user.first_name
    response = f"📊 إحصائياتك في SM 1%:\n\n"
    response += f"🔹 الترتيب: {rank}\n"
    response += f"🔹 عدد الرسائل: {message_count}\n"
    response += f"🔹 تفاعلك يساهم في نمو المجتمع!"

    update.message.reply_text(response)

# ============== تشغيل الخادم ==============

def run_flask():
    app.run(host='0.0.0.0', port=8080)

def run_bot():
    init_db()
    updater = Updater(BOT_TOKEN)
    dp = updater.dispatcher

    # إضافة معالجات الأوامر
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("top", top_members))
    dp.add_handler(CommandHandler("my", my_rank))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, track_message))

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    # تشغيل Flask في thread منفصل
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()

    # تشغيل بوت التليجرام
    run_bot()