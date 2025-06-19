import os
import sqlite3
from datetime import datetime
from flask import Flask, render_template, jsonify, send_from_directory
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import asyncio
import threading
from waitress import serve

# تهيئة تطبيق Flask
app = Flask(__name__, template_folder='templates', static_folder='static')

# إعدادات البوت
GROUP_ID = -1002445433249
ADMIN_ID = 6243639789
BOT_TOKEN = os.getenv('BOT_TOKEN', '6037757983:AAG5qtoMZrIuUMpI8-Mta3KtjW1Qu2Y2iO8')

# تهيئة قاعدة البيانات
def init_db():
    with sqlite3.connect('interactions.db') as conn:
        conn.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            message_count INTEGER DEFAULT 0,
            last_interaction TEXT
        )
        ''')

# ======== مسارات الويب ========

@app.route('/')
def dashboard():
    return render_template('dashboard.html')

@app.route('/api/top_members')
def api_top_members():
    try:
        with sqlite3.connect('interactions.db') as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('''
            SELECT user_id, username, first_name, last_name, message_count 
            FROM users 
            ORDER BY message_count DESC 
            LIMIT 20
            ''')
            members = [dict(row) for row in cursor.fetchall()]
        return jsonify(members)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

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

# خدمة الملفات الثابتة (CSS, JS, images)
@app.route('/static/<path:filename>')
def static_files(filename):
    return send_from_directory(app.static_folder, filename)

# معالجة الأخطاء لصفحات غير موجودة
@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

# ======== معالجات البوت ========

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id == GROUP_ID:
        await update.message.reply_text('مرحباً بكم في بوت تفاعل SM 1%!')

async def track_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != GROUP_ID:
        return

    user = update.effective_user
    now = datetime.now().isoformat()

    with sqlite3.connect('interactions.db') as conn:
        conn.execute('''
        INSERT OR IGNORE INTO users 
        (user_id, username, first_name, last_name, message_count, last_interaction)
        VALUES (?, ?, ?, ?, 0, ?)
        ''', (user.id, user.username, user.first_name, user.last_name, now))
        
        conn.execute('''
        UPDATE users SET 
            message_count = message_count + 1,
            username = ?,
            first_name = ?,
            last_name = ?,
            last_interaction = ?
        WHERE user_id = ?
        ''', (user.username, user.first_name, user.last_name, now, user.id))

async def top_members(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != GROUP_ID:
        return

    with sqlite3.connect('interactions.db') as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute('''
        SELECT username, first_name, last_name, message_count 
        FROM users 
        ORDER BY message_count DESC 
        LIMIT 10
        ''')
        
        response = "🏆 أفضل 10 أعضاء متفاعلين:\n\n"
        for idx, row in enumerate(cursor.fetchall(), 1):
            name = f"@{row['username']}" if row['username'] else f"{row['first_name']} {row['last_name']}".strip()
            response += f"{idx}. {name} - {row['message_count']} رسالة\n"
    
    await update.message.reply_text(response)

async def my_rank(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
        
    await update.message.reply_text(f"📊 ترتيبك: {rank}\n✉️ عدد الرسائل: {user_data[0]}")

# ======== نظام التشغيل الرئيسي ========

def run_flask():
    port = int(os.getenv('PORT', 5000))
    print(f"🌐 بدء خادم الويب على المنفذ {port}")
    serve(app, host="0.0.0.0", port=port)

async def run_bot():
    init_db()
    application = Application.builder().token(BOT_TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("top", top_members))
    application.add_handler(CommandHandler("my", my_rank))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, track_message))
    
    print("🤖 بدء تشغيل بوت التليجرام...")
    await application.initialize()
    await application.start()
    await application.updater.start_polling()
    
    try:
        while True:
            await asyncio.sleep(1)
    except asyncio.CancelledError:
        await application.updater.stop()
        await application.stop()
        await application.shutdown()

def main():
    # تشغيل Flask في thread منفصل
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    
    # تشغيل البوت
    try:
        asyncio.run(run_bot())
    except KeyboardInterrupt:
        print("🛑 تم إيقاف البوت")
    except Exception as e:
        print(f"🔥 خطأ غير متوقع: {str(e)}")

if __name__ == '__main__':
    main()
