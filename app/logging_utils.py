# app/logging_utils.py
import json
import uuid
import time
from datetime import datetime

def json_log(**kwargs):
    log_entry = {
        "ts": datetime.utcnow().isoformat() + "Z",
        **kwargs
    }
    print(json.dumps(log_entry))
