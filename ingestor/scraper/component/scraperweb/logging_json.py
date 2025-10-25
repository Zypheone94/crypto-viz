import json
import sys
from datetime import datetime, timezone
from typing import Any, Dict


def log_json(level: str, message: str, **fields: Dict[str, Any]) -> None:
    payload = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "level": level,
        "msg": message,
    }
    payload.update(fields)
    sys.stdout.write(json.dumps(payload, separators=(",", ":")) + "\n")
    sys.stdout.flush()


