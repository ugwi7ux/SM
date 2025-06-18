from flask import Flask, render_template
from threading import Thread

app = Flask(__name__, template_folder="templates")

@app.route('/index')
def home():
    return render_template("index.html")

@app.route('/store')
def store():
    return render_template("store.html")

@app.route('/support')
def support():
    return render_template("support.html")

@app.route('/law')
def law():
    return render_template("law.html")

@app.route('/dashboard')
def dashboard():
    return render_template("dashboard.html")

@app.route('/contests')
def contests():
    return render_template("contests.html")

@app.route('/report')
def report():
    return render_template("report.html")

@app.errorhandler(404)
def not_found(e):
    return "الصفحة غير موجودة", 404

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()