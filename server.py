import hashlib
import hmac
import json
import os
import secrets
import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from http import HTTPStatus
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse


BASE_DIR = Path(__file__).resolve().parent
DEFAULT_DATA_DIR = BASE_DIR / "data"
DATA_DIR = Path(os.environ.get("DATA_DIR", DEFAULT_DATA_DIR)).resolve()
DB_PATH = Path(os.environ.get("DB_PATH", DATA_DIR / "habit_tracker.db")).resolve()
STATIC_FILES = {
    "/": "index.html",
    "/index.html": "index.html",
    "/login.html": "login.html",
    "/signup.html": "signup.html",
    "/styles.css": "styles.css",
    "/auth.js": "auth.js",
    "/script.js": "script.js",
}
MIME_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
}
SESSION_COOKIE = "habit_tracker_session"
SESSION_DURATION_DAYS = 7
PBKDF2_ITERATIONS = 210_000
TOTAL_DAYS = 21
COOKIE_SECURE = os.environ.get("COOKIE_SECURE", "false").lower() == "true"


def utc_now():
    return datetime.now(timezone.utc)


def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as connection:
        cursor = connection.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                password_salt TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS sessions (
                token TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                expires_at TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS tracker_states (
                user_id INTEGER PRIMARY KEY,
                habit_name TEXT NOT NULL DEFAULT '',
                selected_day INTEGER NOT NULL DEFAULT 1,
                days_json TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
            """
        )
        connection.commit()


def make_default_days():
    return [
        {"day": index + 1, "completed": False, "note": ""}
        for index in range(TOTAL_DAYS)
    ]


def default_tracker_state():
    return {
        "habitName": "",
        "selectedDay": 1,
        "days": make_default_days(),
    }


def hash_password(password, salt_hex=None):
    salt = bytes.fromhex(salt_hex) if salt_hex else secrets.token_bytes(16)
    password_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        PBKDF2_ITERATIONS,
    )
    return password_hash.hex(), salt.hex()


def verify_password(password, stored_hash, salt_hex):
    candidate_hash, _ = hash_password(password, salt_hex)
    return hmac.compare_digest(candidate_hash, stored_hash)


def parse_json(handler):
    content_length = int(handler.headers.get("Content-Length", "0"))
    raw_body = handler.rfile.read(content_length) if content_length else b"{}"
    try:
        return json.loads(raw_body.decode("utf-8"))
    except json.JSONDecodeError:
        return None


def normalize_email(email):
    return email.strip().lower()


def build_cookie(token, max_age):
    secure_part = "; Secure" if COOKIE_SECURE else ""
    return (
        f"{SESSION_COOKIE}={token}; HttpOnly; SameSite=Lax; Path=/; "
        f"Max-Age={max_age}{secure_part}"
    )


def validate_tracker_payload(payload):
    if not isinstance(payload, dict):
        return None

    habit_name = str(payload.get("habitName", "")).strip()
    selected_day = payload.get("selectedDay", 1)
    days = payload.get("days")

    if not isinstance(selected_day, int) or not 1 <= selected_day <= TOTAL_DAYS:
        return None

    if not isinstance(days, list) or len(days) != TOTAL_DAYS:
        return None

    normalized_days = []
    for index, day in enumerate(days, start=1):
        if not isinstance(day, dict):
            return None

        day_number = day.get("day")
        if day_number != index:
            return None

        normalized_days.append(
            {
                "day": index,
                "completed": bool(day.get("completed", False)),
                "note": str(day.get("note", ""))[:2000],
            }
        )

    return {
        "habitName": habit_name[:120],
        "selectedDay": selected_day,
        "days": normalized_days,
    }


class HabitTrackerHandler(BaseHTTPRequestHandler):
    server_version = "HabitTracker/1.0"

    def do_OPTIONS(self):
        self.send_response(HTTPStatus.NO_CONTENT)
        self.send_header("Access-Control-Allow-Origin", "http://127.0.0.1:8000")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, OPTIONS")
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/health":
            self.send_json(HTTPStatus.OK, {"ok": True, "database": str(DB_PATH)})
            return
        if parsed.path == "/api/session":
            self.handle_session()
            return
        if parsed.path == "/api/tracker":
            self.handle_get_tracker()
            return
        self.serve_static(parsed.path)

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/signup":
            self.handle_signup()
            return
        if parsed.path == "/api/login":
            self.handle_login()
            return
        if parsed.path == "/api/logout":
            self.handle_logout()
            return
        self.send_error(HTTPStatus.NOT_FOUND)

    def do_PUT(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/tracker":
            self.handle_update_tracker()
            return
        self.send_error(HTTPStatus.NOT_FOUND)

    def serve_static(self, path):
        relative_name = STATIC_FILES.get(path)
        if not relative_name:
            self.send_error(HTTPStatus.NOT_FOUND)
            return

        target = BASE_DIR / relative_name
        if not target.exists():
            self.send_error(HTTPStatus.NOT_FOUND)
            return

        content = target.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", MIME_TYPES.get(target.suffix, "application/octet-stream"))
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def send_json(self, status, payload, cookie=None, clear_cookie=False):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        if cookie:
            self.send_header("Set-Cookie", cookie)
        if clear_cookie:
            self.send_header(
                "Set-Cookie",
                build_cookie("", 0),
            )
        self.end_headers()
        self.wfile.write(body)

    def db(self):
        connection = sqlite3.connect(DB_PATH)
        connection.row_factory = sqlite3.Row
        return connection

    def get_session_token(self):
        cookie_header = self.headers.get("Cookie")
        if not cookie_header:
            return None

        cookies = SimpleCookie()
        cookies.load(cookie_header)
        morsel = cookies.get(SESSION_COOKIE)
        return morsel.value if morsel else None

    def current_user(self):
        session_token = self.get_session_token()
        if not session_token:
            return None

        with self.db() as connection:
            session = connection.execute(
                """
                SELECT sessions.token, sessions.expires_at, users.id, users.name, users.email
                FROM sessions
                JOIN users ON users.id = sessions.user_id
                WHERE sessions.token = ?
                """,
                (session_token,),
            ).fetchone()

            if not session:
                return None

            if datetime.fromisoformat(session["expires_at"]) <= utc_now():
                connection.execute("DELETE FROM sessions WHERE token = ?", (session_token,))
                connection.commit()
                return None

            return {
                "id": session["id"],
                "name": session["name"],
                "email": session["email"],
                "token": session["token"],
            }

    def ensure_tracker_row(self, connection, user_id):
        tracker_row = connection.execute(
            "SELECT user_id FROM tracker_states WHERE user_id = ?",
            (user_id,),
        ).fetchone()

        if tracker_row:
            return

        tracker = default_tracker_state()
        connection.execute(
            """
            INSERT INTO tracker_states (user_id, habit_name, selected_day, days_json, updated_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                user_id,
                tracker["habitName"],
                tracker["selectedDay"],
                json.dumps(tracker["days"]),
                utc_now().isoformat(),
            ),
        )
        connection.commit()

    def create_session(self, connection, user_id):
        token = secrets.token_urlsafe(32)
        expires_at = utc_now() + timedelta(days=SESSION_DURATION_DAYS)
        connection.execute(
            """
            INSERT INTO sessions (token, user_id, expires_at, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (token, user_id, expires_at.isoformat(), utc_now().isoformat()),
        )
        connection.commit()
        return build_cookie(token, SESSION_DURATION_DAYS * 24 * 60 * 60)

    def handle_signup(self):
        payload = parse_json(self)
        if payload is None:
            self.send_json(HTTPStatus.BAD_REQUEST, {"error": "Invalid JSON body."})
            return

        name = str(payload.get("name", "")).strip()
        email = normalize_email(str(payload.get("email", "")))
        password = str(payload.get("password", ""))

        if not name or "@" not in email or len(password) < 8:
            self.send_json(
                HTTPStatus.BAD_REQUEST,
                {"error": "Enter a name, valid email, and password with at least 8 characters."},
            )
            return

        password_hash, password_salt = hash_password(password)

        with self.db() as connection:
            existing_user = connection.execute(
                "SELECT id FROM users WHERE email = ?",
                (email,),
            ).fetchone()
            if existing_user:
                self.send_json(HTTPStatus.CONFLICT, {"error": "An account with that email already exists."})
                return

            cursor = connection.execute(
                """
                INSERT INTO users (name, email, password_hash, password_salt, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (name, email, password_hash, password_salt, utc_now().isoformat()),
            )
            user_id = cursor.lastrowid
            self.ensure_tracker_row(connection, user_id)
            cookie = self.create_session(connection, user_id)

        self.send_json(
            HTTPStatus.CREATED,
            {"user": {"name": name, "email": email}},
            cookie=cookie,
        )

    def handle_login(self):
        payload = parse_json(self)
        if payload is None:
            self.send_json(HTTPStatus.BAD_REQUEST, {"error": "Invalid JSON body."})
            return

        email = normalize_email(str(payload.get("email", "")))
        password = str(payload.get("password", ""))

        with self.db() as connection:
            user = connection.execute(
                """
                SELECT id, name, email, password_hash, password_salt
                FROM users
                WHERE email = ?
                """,
                (email,),
            ).fetchone()

            if not user or not verify_password(password, user["password_hash"], user["password_salt"]):
                self.send_json(HTTPStatus.UNAUTHORIZED, {"error": "Incorrect email or password."})
                return

            connection.execute("DELETE FROM sessions WHERE user_id = ?", (user["id"],))
            self.ensure_tracker_row(connection, user["id"])
            cookie = self.create_session(connection, user["id"])

        self.send_json(
            HTTPStatus.OK,
            {"user": {"name": user["name"], "email": user["email"]}},
            cookie=cookie,
        )

    def handle_logout(self):
        session_token = self.get_session_token()
        if session_token:
            with self.db() as connection:
                connection.execute("DELETE FROM sessions WHERE token = ?", (session_token,))
                connection.commit()

        self.send_json(HTTPStatus.OK, {"ok": True}, clear_cookie=True)

    def handle_session(self):
        user = self.current_user()
        if not user:
            self.send_json(HTTPStatus.OK, {"authenticated": False, "user": None})
            return

        self.send_json(
            HTTPStatus.OK,
            {
                "authenticated": True,
                "user": {"name": user["name"], "email": user["email"]},
            },
        )

    def handle_get_tracker(self):
        user = self.current_user()
        if not user:
            self.send_json(HTTPStatus.UNAUTHORIZED, {"error": "Please log in to view your tracker."}, clear_cookie=True)
            return

        with self.db() as connection:
            self.ensure_tracker_row(connection, user["id"])
            tracker = connection.execute(
                """
                SELECT habit_name, selected_day, days_json
                FROM tracker_states
                WHERE user_id = ?
                """,
                (user["id"],),
            ).fetchone()

        state = {
            "habitName": tracker["habit_name"],
            "selectedDay": tracker["selected_day"],
            "days": json.loads(tracker["days_json"]),
        }
        self.send_json(HTTPStatus.OK, state)

    def handle_update_tracker(self):
        user = self.current_user()
        if not user:
            self.send_json(HTTPStatus.UNAUTHORIZED, {"error": "Please log in to update your tracker."}, clear_cookie=True)
            return

        payload = parse_json(self)
        tracker = validate_tracker_payload(payload)
        if tracker is None:
            self.send_json(HTTPStatus.BAD_REQUEST, {"error": "Tracker data is invalid."})
            return

        with self.db() as connection:
            self.ensure_tracker_row(connection, user["id"])
            connection.execute(
                """
                UPDATE tracker_states
                SET habit_name = ?, selected_day = ?, days_json = ?, updated_at = ?
                WHERE user_id = ?
                """,
                (
                    tracker["habitName"],
                    tracker["selectedDay"],
                    json.dumps(tracker["days"]),
                    utc_now().isoformat(),
                    user["id"],
                ),
            )
            connection.commit()

        self.send_json(HTTPStatus.OK, {"ok": True})

    def log_message(self, format, *args):
        return


def run_server(host="127.0.0.1", port=8000):
    init_db()
    server = ThreadingHTTPServer((host, port), HabitTrackerHandler)
    print(f"Habit tracker running at http://{host}:{port}")
    print(f"Database path: {DB_PATH}")
    server.serve_forever()


if __name__ == "__main__":
    selected_host = os.environ.get("HOST", "0.0.0.0")
    selected_port = int(os.environ.get("PORT", "8000"))

    if len(sys.argv) > 1 and sys.argv[1]:
        selected_port = int(sys.argv[1])

    run_server(selected_host, selected_port)
