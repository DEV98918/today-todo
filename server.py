"""今日待办清单 - 后端服务
功能：邮箱注册/登录（Token 鉴权）+ 待办的增删改查，数据存于服务端 SQLite。
"""
import os
import re
import sqlite3
import secrets
import hashlib
import hmac
from functools import wraps
from datetime import datetime

from flask import Flask, request, jsonify, send_from_directory, g

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "data", "todos.db")

app = Flask(__name__, static_folder="static", static_url_path="/static")


# ---------------- 数据库 ----------------
def _connect():
    """建立连接：WAL 模式 + synchronous=NORMAL，显著降低写事务的 fsync 开销。"""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    return conn


def get_db():
    """同一请求内复用同一连接，避免一次请求多次建连。"""
    try:
        if "db" not in g:
            g.db = _connect()
        return g.db
    except RuntimeError:
        # 无应用上下文（如初始化、后台任务）
        return _connect()


@app.teardown_appcontext
def close_db(exc):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    db = _connect()
    try:
        with db:
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    salt TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS tokens (
                    token TEXT PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS todos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    text TEXT NOT NULL,
                    done INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_todos_user ON todos(user_id);
                CREATE INDEX IF NOT EXISTS idx_tokens_token ON tokens(token);
                """
            )
    finally:
        db.close()


def hash_password(password: str, salt: str) -> str:
    return hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt.encode("utf-8"), 100_000
    ).hex()


# ---------------- 鉴权 ----------------
def require_auth(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        # 注意：平台的反向代理会覆盖 Authorization 头（注入平台自身 JWT），
        # 因此登录 Token 必须通过自定义头 X-Auth-Token 传输。
        token = request.headers.get("X-Auth-Token", "")
        if not token:
            return jsonify({"error": "未登录"}), 401
        with get_db() as db:
            row = db.execute(
                "SELECT user_id FROM tokens WHERE token = ?", (token,)
            ).fetchone()
        if not row:
            return jsonify({"error": "登录已过期，请重新登录"}), 401
        request.user_id = row["user_id"]
        return f(*args, **kwargs)

    return wrapper


EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")


# ---------------- 认证接口 ----------------
@app.post("/api/register")
def register():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    if not EMAIL_RE.match(email):
        return jsonify({"error": "请输入有效的邮箱地址"}), 400
    if len(password) < 6:
        return jsonify({"error": "密码至少 6 位"}), 400
    salt = secrets.token_hex(16)
    with get_db() as db:
        exists = db.execute("SELECT 1 FROM users WHERE email = ?", (email,)).fetchone()
        if exists:
            return jsonify({"error": "该邮箱已注册，请直接登录"}), 400
        cur = db.execute(
            "INSERT INTO users (email, password_hash, salt, created_at) VALUES (?,?,?,?)",
            (email, hash_password(password, salt), salt, datetime.now().isoformat()),
        )
        user_id = cur.lastrowid
        token = secrets.token_hex(32)
        db.execute(
            "INSERT INTO tokens (token, user_id, created_at) VALUES (?,?,?)",
            (token, user_id, datetime.now().isoformat()),
        )
    return jsonify({"token": token, "email": email})


@app.post("/api/login")
def login():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    with get_db() as db:
        user = db.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    if not user or not hmac.compare_digest(
        user["password_hash"], hash_password(password, user["salt"])
    ):
        return jsonify({"error": "邮箱或密码错误"}), 401
    token = secrets.token_hex(32)
    with get_db() as db:
        db.execute(
            "INSERT INTO tokens (token, user_id, created_at) VALUES (?,?,?)",
            (token, user["id"], datetime.now().isoformat()),
        )
    return jsonify({"token": token, "email": email})


@app.post("/api/logout")
@require_auth
def logout():
    auth = request.headers.get("Authorization", "")
    token = auth[7:] if auth.startswith("Bearer ") else auth
    with get_db() as db:
        db.execute("DELETE FROM tokens WHERE token = ?", (token,))
    return jsonify({"ok": True})


# ---------------- 待办接口 ----------------
def todo_row(t):
    return {"id": t["id"], "text": t["text"], "done": bool(t["done"])}


@app.get("/api/todos")
@require_auth
def list_todos():
    with get_db() as db:
        rows = db.execute(
            "SELECT * FROM todos WHERE user_id = ? ORDER BY done ASC, id DESC",
            (request.user_id,),
        ).fetchall()
    return jsonify([todo_row(r) for r in rows])


@app.post("/api/todos")
@require_auth
def add_todo():
    data = request.get_json(silent=True) or {}
    text = (data.get("text") or "").strip()
    if not text:
        return jsonify({"error": "任务内容不能为空"}), 400
    if len(text) > 200:
        return jsonify({"error": "任务内容不能超过 200 字"}), 400
    with get_db() as db:
        cur = db.execute(
            "INSERT INTO todos (user_id, text, done, created_at) VALUES (?,?,0,?)",
            (request.user_id, text, datetime.now().isoformat()),
        )
        row = db.execute("SELECT * FROM todos WHERE id = ?", (cur.lastrowid,)).fetchone()
    return jsonify(todo_row(row)), 201


@app.put("/api/todos/<int:todo_id>")
@require_auth
def toggle_todo(todo_id):
    data = request.get_json(silent=True) or {}
    with get_db() as db:
        row = db.execute(
            "SELECT * FROM todos WHERE id = ? AND user_id = ?",
            (todo_id, request.user_id),
        ).fetchone()
        if not row:
            return jsonify({"error": "任务不存在"}), 404
        done = 1 if data.get("done") is not None else (0 if row["done"] else 1)
        if data.get("done") is not None:
            done = 1 if data.get("done") else 0
        db.execute(
            "UPDATE todos SET done = ? WHERE id = ?", (done, todo_id)
        )
        row = db.execute("SELECT * FROM todos WHERE id = ?", (todo_id,)).fetchone()
    return jsonify(todo_row(row))


@app.delete("/api/todos/<int:todo_id>")
@require_auth
def delete_todo(todo_id):
    with get_db() as db:
        cur = db.execute(
            "DELETE FROM todos WHERE id = ? AND user_id = ?",
            (todo_id, request.user_id),
        )
        if cur.rowcount == 0:
            return jsonify({"error": "任务不存在"}), 404
    return jsonify({"ok": True})


# ---------------- 页面 ----------------
@app.get("/")
def index():
    return send_from_directory(os.path.join(BASE_DIR, "static"), "index.html")


init_db()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 3000))
    app.run(host="0.0.0.0", port=port)
