# Lyftr AI — Backend Assignment

## Overview

This project is a **production-style FastAPI service** built as part of the Lyftr AI Backend Assignment. The service ingests WhatsApp-like webhook messages **exactly once**, validates requests using **HMAC-SHA256**, stores data in **SQLite**, and exposes APIs for querying messages, analytics, health checks, and metrics. The entire application is **containerized using Docker Compose**.

---

## Tech Stack

* **Language:** Python 3.11
* **Framework:** FastAPI
* **Database:** SQLite
* **Containerization:** Docker & Docker Compose
* **Metrics:** Prometheus-style exposition

---

## How to Run

### Prerequisites

* Docker Desktop installed and running

### Start the service

```bash
docker compose up --build
```

The API will be available at:

```
http://localhost:8000
```

### Stop the service

```bash
docker compose down
```

---

## Environment Variables

All configuration is provided via environment variables (12-factor style), set in `docker-compose.yml`.

| Variable         | Description                                         |
| ---------------- | --------------------------------------------------- |
| `DATABASE_URL`   | SQLite database location (`sqlite:////data/app.db`) |
| `WEBHOOK_SECRET` | Secret used for HMAC signature validation           |
| `LOG_LEVEL`      | Logging level (default: INFO)                       |

---

## API Endpoints

### Health Checks

* **GET `/health/live`**
  Returns 200 when the app is running.

* **GET `/health/ready`**
  Returns 200 only if the database is reachable and `WEBHOOK_SECRET` is set.

---

### Webhook

* **POST `/webhook`**
  Ingests inbound messages exactly once.

**Headers**

```
Content-Type: application/json
X-Signature: <hex hmac sha256>
```

**Behavior**

* Invalid or missing signature → `401 Unauthorized`
* Valid signature:

  * First request inserts the message
  * Duplicate `message_id` is ignored (idempotent)
  * Always returns `200 {"status": "ok"}`

---

### Messages

* **GET `/messages`**
  Lists stored messages with pagination and filters.

**Query Parameters**

* `limit` (default 50, max 100)
* `offset` (default 0)
* `from` (filter by sender)
* `since` (ISO-8601 timestamp)
* `q` (case-insensitive text search)

---

### Stats

* **GET `/stats`**
  Returns message analytics:

  * Total messages
  * Unique senders count
  * Top senders
  * First and last message timestamps

---

### Metrics

* **GET `/metrics`**
  Exposes Prometheus-style metrics, including:

  * `http_requests_total`
  * `webhook_requests_total`

---

## Data Model

```sql
CREATE TABLE IF NOT EXISTS messages (
  message_id TEXT PRIMARY KEY,
  from_msisdn TEXT NOT NULL,
  to_msisdn TEXT NOT NULL,
  ts TEXT NOT NULL,
  text TEXT,
  created_at TEXT NOT NULL
);
```

---

## Design Decisions

### HMAC Verification

The `/webhook` endpoint validates requests using **HMAC-SHA256**. The server computes a hexadecimal HMAC over the **raw request body bytes** using the shared secret provided via the `WEBHOOK_SECRET` environment variable. The computed signature is then compared with the value sent in the `X-Signature` header using a constant-time comparison to prevent timing attacks. Requests with missing or invalid signatures are rejected with `401 Unauthorized` and are not persisted.

### Pagination Contract (`/messages`)

The `/messages` endpoint implements offset-based pagination using `limit` and `offset` query parameters. Results are ordered deterministically by `ts ASC, message_id ASC` to ensure stable pagination. The response always includes a `total` field representing the total number of records matching the filters **before** pagination is applied, along with the echoed `limit` and `offset` values. This makes pagination predictable and client-friendly.

### Stats and Metrics

The `/stats` endpoint provides lightweight analytics computed from the messages table. It returns the total number of messages, the number of unique senders, the top senders (up to 10) sorted by message count, and the first and last message timestamps using SQL aggregation queries.

The `/metrics` endpoint exposes Prometheus-style metrics, including counters for total HTTP requests and webhook processing outcomes (created, duplicate, invalid signature, validation errors). These metrics enable basic observability and are formatted to be compatible with Prometheus scraping.

---

## Repository Structure

```
app/
 ├── main.py           # FastAPI app, middleware, routes
 ├── config.py         # Environment variable loading
 ├── models.py         # SQLite database initialization
 ├── storage.py        # Database operations (insert, query)
 ├── logging_utils.py  # Structured JSON logging helpers
 ├── metrics.py        # Prometheus metrics helpers

tests/                 # Optional pytest-based integration tests
 ├── test_webhook.py   # Webhook signature & idempotency tests
 ├── test_messages.py  # /messages pagination & filters tests
 ├── test_stats.py     # /stats correctness tests

Dockerfile              # Docker image definition
docker-compose.yml      # Service orchestration
requirements.txt        # Python dependencies
README.md               # Project documentation

```

---

## Setup Used

VS Code, Docker Desktop, and occasional ChatGPT assistance.

---

## Submission

This repository is submitted as part of the **Lyftr AI Backend Assignment**.
