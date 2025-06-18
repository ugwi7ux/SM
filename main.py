import os
import sqlite3
from datetime import datetime
from flask import Flask, render_template, jsonify
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import asyncio
import threading
import requests
from keep_alive import keep_alive

# تهيئة تطبيق Flask
app = Flask(__name__)

# إعدادات البوت (يجب نقل التوكن لمتغيرات البيئة لزيادة الأمان)
GROUP_ID = -1002445433249
ADMIN_ID = 6243639789
BOT_TOKEN = os.getenv('BOT_TOKEN', '6037757983:AAG5qtoMZrIuUMpI8-Mta3KtjW1Qu2Y2iO8')  # التوكن الافتراضي للتجربة

# تهيئة قاعدة البيانات (نسخة محسنة)
def init_db():
    with sqlite3.connect('interactions.db') as conn:
        conn.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            message_count INTEGER DEFAULT 0,
            last_interaction TEXT,
            join_date TEXT DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        # إنشاء فهرس لتحسين الأداء
        conn.execute('CREATE INDEX IF NOT EXISTS idx_message_count ON users(message_count)')

# ======== نظام التشغيل المستمر ========
def ping_server():
    while True:
        try:
            # استخدام رابط المشروع الديناميكي
            domain = os.getenv('RAILWAY_STATIC_URL', 'http://localhost:8080')
            requests.get(f'{domain}/ping', timeout=5)
            print(f"✅ تم إرسال طلب التشغيل المستمر إلى {domain}/ping")
            time.sleep(240)  # كل 4 دقائق
        except Exception as e:
            print(f"⚠️ خطأ في التشغيل المستمر: {str(e)}")
            time.sleep(60)  # الانتظار دقيقة قبل إعادة المحاولة

# ======== مسارات الويب المعدلة ========
@app.route('/')
def dashboard():
    return render_template('dashboard.html')

@app.route('/ping')
def ping():
    return jsonify({"status": "active", "timestamp": datetime.now().isoformat()}), 200

@app.route('/api/top_members')
def api_top_members():
    with sqlite3.connect('interactions.db') as conn:
        conn.row_factory = sqlite3.Row  # للحصول على نتائج كقاموس
        cursor = conn.cursor()
        cursor.execute('''
        SELECT user_id, username, first_name, last_name, message_count 
        FROM users 
        ORDER BY message_count DESC 
        LIMIT 20
        ''')
        members = [dict(row) for row in cursor.fetchall()]
    return jsonify(members)

# ======== معالجات البوت المحسنة ========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id == GROUP_ID:
        await update.message.reply_text(
            'مرحباً بكم في بوت تفاعل SM 1%!\n'
            'الأوامر المتاحة:\n'
            '/top - عرض الأعضاء الأكثر تفاعلاً\n'
            '/my - عرض تصنيفك'
        )

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
        
        top_users = cursor.fetchall()
    
    response = "🏆 أفضل 10 أعضاء متفاعلين:\n\n"
    for idx, user in enumerate(top_users, 1):
        name = user['username'] or f"{user['first_name']} {user['last_name']}".strip()
        response += f"{idx}. {name} - {user['message_count']} رسالة\n"
    
    await update.message.reply_text(response)

async def my_rank(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != GROUP_ID:
        return

    user = update.effective_user
    with sqlite3.connect('interactions.db') as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # الحصول على بيانات المستخدم
        cursor.execute('SELECT message_count FROM users WHERE user_id = ?', (user.id,))
        user_data = cursor.fetchone()
        
        if not user_data:
            await update.message.reply_text("⚠️ لم يتم العثور على بيانات تفاعل لك.")
            return
        
        # حساب الترتيب
        cursor.execute('''
        SELECT COUNT(*) as rank FROM users 
        WHERE message_count > ?
        ''', (user_data['message_count'],))
        rank = cursor.fetchone()['rank'] + 1
        
        # الحصول على إجمالي الأعضاء
        cursor.execute('SELECT COUNT(*) as total FROM users')
        total_users = cursor.fetchone()['total']
        
        # حساب النسبة المئوية
        percentile = round((1 - (rank / total_users)) * 100, 2) if total_users > 0 else 0
    
    name = f"@{user.username}" if user.username else user.first_name
    response = (
        f"📊 إحصائيات {name}:\n\n"
        f"🏅 الترتيب: {rank} من {total_users}\n"
        f"✉️ عدد الرسائل: {user_data['message_count']}\n"
        f"📈 متفوق على {percentile}% من الأعضاء"
    )
    
    await update.message.reply_text(response)

# ======== إعدادات التشغيل الرئيسية ========
async def run_bot():
    init_db()
    application = Application.builder().token(BOT_TOKEN).build()
    
    # تسجيل معالجات الأوامر
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("top", top_members))
    application.add_handler(CommandHandler("my", my_rank))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, track_message))
    
    print("🤖 بدء تشغيل بوت التليجرام...")
    await application.run_polling()

def run_flask():
    from waitress import serve
    port = int(os.getenv('PORT', '8080'))
    print(f"🌐 بدء تشغيل خادم الويب على المنفذ {port}")
    serve(app, host="0.0.0.0", port=port)

def main():
    # بدء خدمة keep-alive
    keep_alive()
    
    # بدء نظام التشغيل المستمر في thread منفصل
    threading.Thread(target=ping_server, daemon=True).start()
    
    # تشغيل Flask في thread منفصل
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()
    
    # تشغيل البوت
    asyncio.run(run_bot())

if __name__ == '__main__':
    print("🚀 بدء تشغيل النظام...")
    main()
