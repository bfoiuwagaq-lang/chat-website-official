from flask import Flask, request, jsonify
from flask_cors import CORS
import sqlite3
import datetime
import bcrypt

app = Flask(__name__)
CORS(app, origins="*")
DB_FILE = "tectonic.db"

# --- CHAT FILTER SETUP ---
# Add any words you want to block here
BANNED_WORDS = ["shit", "crap", "spam", "attack"]

def filter_text(text):
    filtered = text
    for word in BANNED_WORDS:
        # Replaces banned words with asterisks
        filtered = filtered.replace(word, "*" * len(word))
    return filtered

# --- DATABASE SETUP ---
def init_db():
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS users 
                          (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                           username TEXT UNIQUE, 
                           password_hash TEXT)''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS messages 
                          (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                           username TEXT, 
                           content TEXT, 
                           timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')
        conn.commit()

init_db()

# --- AUTH ROUTES ---

@app.route("/signup", methods=["POST"])
def signup():
    data = request.get_json()
    username = data.get("username")
    password = data.get("password")
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    print(f"Hashed Password: {hashed_password}")
    try:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO users (username, password_hash) VALUES (?, ?) ", (username, hashed_password))
            conn.commit()
        return jsonify({"message": "User created"}), 201
    except sqlite3.IntegrityError:
        return jsonify({"error": "Username taken"}), 400

@app.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    user = data.get("username")
    pw = data.get("password").encode('utf-8')
    print(pw)
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT password_hash FROM users WHERE username = ?", (user,))
        row = cursor.fetchone()
        if row is None:
            return jsonify({"error": "User not found"}), 404
        stored_hash = row[0]
        print(stored_hash)
        if bcrypt.checkpw(pw, stored_hash):
            return jsonify({"message": "login success"}), 200
    
    return jsonify({"error": "Invalid login"}), 401
    

# --- CHAT ROUTES (With Filter) ---

@app.route("/send_message", methods=["POST"])
def send_message():
    data = request.get_json()
    username = data.get("username")
    # Clean the message before saving it to SQLite
    clean_content = filter_text(data.get("message", ""))
    
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO messages (username, content) VALUES (?, ?)", (username, clean_content))
        conn.commit()
    return jsonify({"status": "sent"}), 200

@app.route("/get_messages", methods=["GET"])
def get_messages():
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT username, content FROM messages ORDER BY id DESC LIMIT 50")
        rows = cursor.fetchall()
    messages = [{"username": r[0], "text": r[1]} for r in reversed(rows)]
    return jsonify({"messages": messages})



if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)