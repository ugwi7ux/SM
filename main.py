import os
import sqlite3
from datetime import datetime
from flask import Flask, render_template, jsonify
from telegram import Update
from telegram.ext import (
    Updater,
    CommandHandler,
    MessageHandler,
    filters,
    CallbackContext,
    Application
)
import threading
import requests
import time
from keep_alive import keep_alive

# تهيئة تطبيق Flask
app = Flask(__name__)

# إعدادات البوت (استخدم متغيرات البيئة)
GROUP_ID = -1002445433249
ADMIN_ID = 6243639789
BOT_TOKEN = os.environ.get('BOT_TOKEN')
REPL_URL = os.environ.get('REPL_URL', 'http://localhost:8080')

# تهيئة قاعدة البيانات
def init_db():
    with sqlite3.connect('interactions.db') as conn:
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

# ======== جزء التشغيل المستمر ========
def ping_server():
    while True:
        try:
            requests.get(f"{REPL_URL}/ping", timeout=10)
            time.sleep(240)
        except Exception as e:
            print(f"Keep-alive error: {e}")

@app.route('/ping')
def ping():
    return "Bot is alive!", 200

# ============== مسارات Flask ==============
@app.route('/')
def dashboard():
    return render_template('dashboard.html')

@app.route('/api/top_members')
def api_top_members():
    with sqlite3.connect('interactions.db') as conn:
        cursor = conn.cursor()
        cursor.execute('''
        SELECT user_id, username, first_name, last_name, message_count 
        FROM users 
        ORDER BY message_count DESC 
        LIMIT 20
        ''')
        members = [{
            'user_id': row[0],
            'username': row[1],
            'first_name': row[2] or "",
            'last_name': row[3] or "",
            'message_count': row[4]
        } for row in cursor.fetchall()]
    return jsonify(members)

# ============== معالجات البوت ==============
async def start(update: Update, context: CallbackContext):
    if update.effective_chat.id == GROUP_ID:
        await update.message.reply_text('مرحباً بكم في بوت تفاعل SM 1%! استخدم /top لرؤية الأكثر تفاعلاً')

async def track_message(update: Update, context: CallbackContext):
    if update.effective_chat.id != GROUP_ID:
        return

    user = update.effective_user
    now = datetime.now().isoformat()

    with sqlite3.connect('interactions.db') as conn:
        cursor = conn.cursor()
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

async def top_members(update: Update, context: CallbackContext):
    if update.effective_chat.id != GROUP_ID:
        return

    with sqlite3.connect('interactions.db') as conn:
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

        await update.message.reply_text(response)

async def my_rank(update: Update, context: CallbackContext):
    if update.effective_chat.id != GROUP_ID:
        return

    user = update.effective_user
    with sqlite3.connect('interactions.db') as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT message_count FROM users WHERE user_id = ?', (user.id,))
        user_data = cursor.fetchone()

        if not user_data:
            await update.message.reply_text("لم يتم العثور على بيانات تفاعل لك.")
            return

        cursor.execute('SELECT COUNT(*) FROM users WHERE message_count > ?', (user_data[0],))
        rank = cursor.fetchone()[0] + 1
        message_count = user_data[0]

        name = f"@{user.username}" if user.username else user.first_name
        response = f"📊 إحصائياتك في SM 1%:\n\n"
        response += f"🔹 الترتيب: {rank}\n"
        response += f"🔹 عدد الرسائل: {message_count}\n"
        response += f"🔹 تفاعلك يساهم في نمو المجتمع!"

        await update.message.reply_text(response)

# ============== تشغيل التطبيق ==============
def run_flask():
    from waitress import serve
    serve(app, host="0.0.0.0", port=8080)

async def run_bot():
    init_db()
    application = Application.builder().token(BOT_TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("top", top_members))
    application.add_handler(CommandHandler("my", my_rank))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, track_message))
    
    await application.run_polling()

def main():
    # بدء خدمة keep-alive
    threading.Thread(target=ping_server, daemon=True).start()
    
    # تشغيل Flask
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()
    
    # تشغيل البوت
    asyncio.run(run_bot())

if __name__ == '__main__':
    keep_alive()  # من ملف keep_alive.py
    main()
