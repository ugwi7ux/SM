import os
import sqlite3
from datetime import datetime
from flask import Flask, render_template, jsonify
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import asyncio
import threading
import requests
import time

# تهيئة تطبيق Flask
app = Flask(__name__)

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

# ======== نظام التشغيل المستمر المعدل ========
def ping_server():
    while True:
        try:
            # استخدام رابط المشروع الحالي
            domain = os.getenv('RAILWAY_STATIC_URL', 'http://localhost:8080')
            response = requests.get(f'{domain}/ping', timeout=5)
            print(f"✅ Ping successful - Status: {response.status_code}")
        except Exception as e:
            print(f"⚠️ Ping failed: {str(e)}")
        time.sleep(300)  # كل 5 دقائق

# ======== مسارات الويب ========
@app.route('/')
def home():
    return render_template('dashboard.html')

@app.route('/ping')
def ping():
    return jsonify({"status": "active", "time": datetime.now().isoformat()}), 200

# ... (بقية مسارات Flask كما هي) ...

# ======== معالجات البوت المعدلة ========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id == GROUP_ID:
        await update.message.reply_text('مرحباً بكم في بوت تفاعل SM 1%!')

# ... (بقية معالجات البوت كما هي مع استبدال CallbackContext بـ ContextTypes.DEFAULT_TYPE) ...

# ======== نظام التشغيل الرئيسي المعدل ========
async def run_bot():
    init_db()
    application = Application.builder().token(BOT_TOKEN).build()
    
    # تسجيل معالجات الأوامر
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
        pass
    finally:
        await application.updater.stop()
        await application.stop()
        await application.shutdown()

def run_flask():
    from waitress import serve
    port = int(os.getenv('PORT', '8080'))
    print(f"🌐 بدء تشغيل خادم الويب على المنفذ {port}")
    serve(app, host="0.0.0.0", port=port)

async def main():
    # بدء خدمة ping في thread منفصل
    threading.Thread(target=ping_server, daemon=True).start()
    
    # تشغيل Flask في thread منفصل
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()
    
    # تشغيل البوت
    await run_bot()

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("🛑 إيقاف البوت...")
    except Exception as e:
        print(f"🔥 خطأ غير متوقع: {str(e)}")
    finally:
        print("✅ تم إيقاف النظام بشكل نظيف")
