import sqlite3
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs


def get_db():
    return sqlite3.connect("app.db")


class UserHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        params = parse_qs(urlparse(self.path).query)
        user_id = params.get("id", [""])[0]

        conn = get_db()
        cursor = conn.cursor()
        query = "SELECT name, email FROM users WHERE id = ?"
        cursor.execute(query, (user_id,))
        row = cursor.fetchone()
        conn.close()

        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        if row:
            self.wfile.write(f"{row[0]} <{row[1]}>".encode())
        else:
            self.wfile.write(b"not found")
