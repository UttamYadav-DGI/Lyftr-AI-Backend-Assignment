from app.models import get_db
from datetime import datetime

def insert_message(data):
    conn = get_db()
    cur = conn.cursor()
    try:
        cur.execute("""
        INSERT INTO messages VALUES (?, ?, ?, ?, ?, ?)
        """, (
            data["message_id"],
            data["from"],
            data["to"],
            data["ts"],
            data.get("text"),
            datetime.utcnow().isoformat() + "Z"
        ))
        conn.commit()
        return "created"
    except Exception:
        return "duplicate"
    finally:
        conn.close()
