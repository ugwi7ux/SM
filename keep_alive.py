from flask import Flask
from threading import Thread
import os

app = Flask(__name__)

@app.route('/')
def home():
    return {
        "status": "running",
        "service": "keep-alive",
        "timestamp": datetime.now().isoformat()
    }, 200

def run():
    port = int(os.getenv('KEEP_ALIVE_PORT', '8081'))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run)
    t.daemon = True
    t.start()
    print(f"🔌 خدمة Keep-Alive تعمل على المنفذ {os.getenv('KEEP_ALIVE_PORT', '8081')}")
