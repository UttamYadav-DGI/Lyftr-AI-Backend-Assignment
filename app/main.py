from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field, validator
from prometheus_client import generate_latest
import hmac, hashlib, re
from app.config import WEBHOOK_SECRET
from app.models import init_db, get_db
from app.storage import insert_message
import time
import uuid
from fastapi import Request
from app.logging_utils import json_log

from app.metrics import (
    http_requests_total,
    webhook_requests_total
)

app = FastAPI()

@app.on_event("startup")
def startup():
    init_db()

@app.get("/health/live")
def live():
    return {"status": "live"}

@app.get("/health/ready")
def ready():
    if not WEBHOOK_SECRET:
        raise HTTPException(503)
    try:
        get_db()
        return {"status": "ready"}
    except:
        raise HTTPException(503)

# /message endpoint 
@app.get("/messages")
def get_messages(
    limit: int = 50,
    offset: int = 0,
    from_: str | None = None,
    since: str | None = None,
    q: str | None = None
):
    conn = get_db()
    cur = conn.cursor()

    query = "SELECT message_id, from_msisdn, to_msisdn, ts, text FROM messages WHERE 1=1"
    params = []

    if from_:
        query += " AND from_msisdn=?"
        params.append(from_)

    if since:
        query += " AND ts>=?"
        params.append(since)

    if q:
        query += " AND LOWER(text) LIKE ?"
        params.append(f"%{q.lower()}%")

    # total count
    total = cur.execute(
        f"SELECT COUNT(*) FROM ({query})", params
    ).fetchone()[0]

    query += " ORDER BY ts ASC, message_id ASC LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    rows = cur.execute(query, params).fetchall()
    conn.close()

    return {
        "data": [
            {
                "message_id": r[0],
                "from": r[1],
                "to": r[2],
                "ts": r[3],
                "text": r[4],
            } for r in rows
        ],
        "total": total,
        "limit": limit,
        "offset": offset
    }

#. /stats EndPoint

@app.get("/stats")
def stats():
    conn = get_db()
    cur = conn.cursor()

    total = cur.execute("SELECT COUNT(*) FROM messages").fetchone()[0]
    senders = cur.execute("""
    SELECT from_msisdn, COUNT(*) 
    FROM messages GROUP BY from_msisdn
    ORDER BY COUNT(*) DESC LIMIT 10
    """).fetchall()

    first = cur.execute("SELECT MIN(ts) FROM messages").fetchone()[0]
    last = cur.execute("SELECT MAX(ts) FROM messages").fetchone()[0]

    conn.close()

    return {
        "total_messages": total,
        "senders_count": len(senders),
        "messages_per_sender": [
            {"from": s[0], "count": s[1]} for s in senders
        ],
        "first_message_ts": first,
        "last_message_ts": last
    }


@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type="text/plain")



class WebhookPayload(BaseModel):
    message_id: str = Field(min_length=1)
    from_: str = Field(alias="from")
    to: str
    ts: str
    text: str | None = Field(default=None, max_length=4096)

    @validator("from_", "to")
    def validate_phone(cls, v):
        if not re.match(r"^\+\d+$", v):
            raise ValueError("Invalid phone number format")
        return v

    
def verify_signature(secret: str, body: bytes, signature: str) -> bool:
    computed = hmac.new(
        secret.encode(),
        body,
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(computed, signature)


@app.middleware("http")
async def logging_middleware(request: Request, call_next):
    request_id = str(uuid.uuid4())
    start_time = time.time()

    # attach request_id to request.state
    request.state.request_id = request_id

    response = await call_next(request)

    latency_ms = int((time.time() - start_time) * 1000)

    # basic log for every request
    json_log(
        level="INFO",
        request_id=request_id,
        method=request.method,
        path=request.url.path,
        status=response.status_code,
        latency_ms=latency_ms
    )

    return response


@app.post("/webhook")
async def webhook(req: Request):
    body = await req.body()
    sig = req.headers.get("X-Signature")

    if not sig or not verify_signature(WEBHOOK_SECRET, body, sig):
        json_log(
            level="ERROR",
            request_id=req.state.request_id,
            method="POST",
            path="/webhook",
            status=401,
            result="invalid_signature"
        )
        webhook_requests_total.labels("invalid_signature").inc()
        raise HTTPException(401, detail="invalid signature")

    payload = WebhookPayload.parse_raw(body)

    result = insert_message(payload.dict(by_alias=True))
    dup = True if result == "duplicate" else False

    json_log(
        level="INFO",
        request_id=req.state.request_id,
        method="POST",
        path="/webhook",
        status=200,
        latency_ms=0,  # already captured in middleware
        message_id=payload.message_id,
        dup=dup,
        result=result
    )

    webhook_requests_total.labels(result).inc()
    return {"status": "ok"}
