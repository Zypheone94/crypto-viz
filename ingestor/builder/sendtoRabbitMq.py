from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv(usecwd=True))

import os
import json
import hashlib
import pathlib
import codecs
import time
import pika

# Configuration
RAW_ROOT = pathlib.Path(os.getenv("RAW_DIR", "data/raw"))
RABBIT_HOST = os.getenv("RABBIT_HOST", "rabbitmq")
RABBIT_PORT = int(os.getenv("RABBIT_PORT", 5672))
RABBIT_USER = os.getenv("RABBIT_USER", "user")
RABBIT_PASS = os.getenv("RABBIT_PASS", "password")
QUEUE = os.getenv("RABBIT_QUEUE", "crypto-viz")

def key(a: dict) -> str:
    """Generate a unique key from url + title (optional)"""
    return hashlib.sha1(((a.get("url") or "") + (a.get("title") or "")).encode("utf-8")).hexdigest()

# --- Connexion à RabbitMQ avec retry ---
max_attempts = 10
for attempt in range(max_attempts):
    try:
        credentials = pika.PlainCredentials(RABBIT_USER, RABBIT_PASS)
        parameters = pika.ConnectionParameters(
            host=RABBIT_HOST,
            port=RABBIT_PORT,
            credentials=credentials,
        )
        connection = pika.BlockingConnection(parameters)
        channel = connection.channel()
        channel.queue_declare(queue=QUEUE, durable=True)
        print(f"[producer] Connected to RabbitMQ at {RABBIT_HOST}:{RABBIT_PORT}")
        break
    except pika.exceptions.AMQPConnectionError:
        print(f"[producer] RabbitMQ not ready, retry {attempt+1}/{max_attempts}...")
        time.sleep(2)
else:
    raise Exception(f"[producer] Cannot connect to RabbitMQ after {max_attempts} attempts")

# --- Envoi des fichiers ---
total = 0
files = sorted(RAW_ROOT.rglob("*.ndjson"))
print(f"[producer] scanning {RAW_ROOT} → {len(files)} file(s)")

for p in files:
    raw = p.read_bytes()
    if raw[:3] == codecs.BOM_UTF8:
        raw = raw[3:]
    text = raw.decode("utf-8", errors="replace")

    sent = 0
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            a = json.loads(line)
            channel.basic_publish(
                exchange='',
                routing_key=QUEUE,
                body=json.dumps(a, ensure_ascii=False).encode('utf-8'),
                properties=pika.BasicProperties(
                    delivery_mode=2,
                    headers={"key": key(a)}
                )
            )
            sent += 1
        except Exception as e:
            print(f"[producer] skip bad line in {p.name}: {e}")
    if sent:
        print(f"[producer] {p} → sent {sent} message(s)")
        total += sent

connection.close()
print(f"[producer] done: sent {total} message(s) to {RABBIT_HOST} queue {QUEUE}")
