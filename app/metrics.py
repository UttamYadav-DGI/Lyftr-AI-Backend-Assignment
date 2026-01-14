from prometheus_client import Counter, generate_latest

http_requests_total = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["path", "status"]
)

webhook_requests_total = Counter(
    "webhook_requests_total",
    "Webhook results",
    ["result"]
)
