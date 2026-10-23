# SlothPlant server: catches readings from the Arduino, asks a local
# open-weight model (Ollama) whether the plant needs anything, and sends
# a plant message to your phone through ntfy.
# Run with: python server.py

import csv
import threading
import time
from datetime import datetime
from pathlib import Path

import ollama
import requests
from flask import Flask, jsonify, request

# ---------------- SETTINGS (change these) ----------------
NTFY_TOPIC = "sloth_plantss"        # your ntfy topic
MODEL = "gemma3:1b"                 # local open-weight model

# Placeholder calibration numbers. Replace with your own readings later!
# On this sensor, HIGHER number = DRIER soil.
DRY_THRESHOLD = 400                 # above this = needs water
WET_EXAMPLE = 250                   # roughly what freshly watered soil reads

CHECK_EVERY_SECONDS = 3600           
READINGS_TO_LOOK_AT = 12            # how many recent readings the model sees
COOLDOWN_SECONDS = 600              # minimum gap between messages (10 min)
# ---------------------------------------------------------

app = Flask(__name__)
DATA_FILE = Path("readings.csv")
last_sent = 0.0


def save_reading(soil):
    is_new = not DATA_FILE.exists()
    with DATA_FILE.open("a", newline="") as f:
        writer = csv.writer(f)
        if is_new:
            writer.writerow(["timestamp", "soil"])
        writer.writerow([datetime.now().isoformat(timespec="seconds"), soil])


def recent_readings(n):
    if not DATA_FILE.exists():
        return []
    with DATA_FILE.open() as f:
        rows = list(csv.DictReader(f))
    return [int(r["soil"]) for r in rows[-n:]]


def ask_model(values, must_notify):
    latest = values[-1]
    avg = sum(values) // len(values)
    trend = "drying out" if values[-1] > values[0] + 10 else (
        "getting wetter" if values[-1] < values[0] - 10 else "steady")

    system = (
        "You are a sleepy, sweet houseplant with a calm sloth-like pace. "
        "You hate nagging."
    )
    facts = (
        f"Soil sensor facts: HIGHER number means DRIER soil. "
        f"Above {DRY_THRESHOLD} means the plant needs water. "
        f"About {WET_EXAMPLE} means freshly watered.\n"
        f"Latest reading: {latest}. Recent average: {avg}. Trend: {trend}.\n\n"
    )
    if must_notify:
        prompt = facts + (
            "The plant needs water now. Reply with ONLY a message of two "
            "short lines in your sleepy plant voice, with one emoji."
        )
    else:
        prompt = facts + (
            "The soil is in the in-between zone. Decide if the human needs "
            "a gentle heads-up, based on the trend.\n"
            "If no, reply with exactly: QUIET\n"
            "If yes, reply with: NOTIFY: then two short lines in your "
            "sleepy plant voice, with one emoji."
        )
    resp = ollama.chat(
        model=MODEL,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
    )
    return resp["message"]["content"].strip()


def send_ntfy(message):
    requests.post(
        f"https://ntfy.sh/{NTFY_TOPIC}",
        data=message.encode("utf-8"),
        headers={"Title": "SlothPlant"},
        timeout=10,
    )


def check_plant():
    """Look at recent readings, ask the model, notify if needed."""
    global last_sent
    values = recent_readings(READINGS_TO_LOOK_AT)
    if not values:
        return "no readings yet"

    avg = sum(values) / len(values)

    # Clear cases are decided by simple rules (small models are unreliable
    # at this). The model writes the message, and decides the gray zone.
    if avg > DRY_THRESHOLD:
        must_notify = True
    elif avg < DRY_THRESHOLD - 80:
        return "quiet (soil is clearly fine)"
    else:
        must_notify = False

    answer = ask_model(values, must_notify)
    print(f"Model said: {answer!r}")

    if must_notify or answer.upper().startswith("NOTIFY"):
        if time.time() - last_sent < COOLDOWN_SECONDS:
            return "wanted to notify, but cooldown is active"
        message = answer.split(":", 1)[-1].strip() if answer.upper().startswith("NOTIFY") else answer
        send_ntfy(message)
        last_sent = time.time()
        return f"sent: {message}"
    return "quiet (plant is fine)"


def background_loop():
    while True:
        time.sleep(CHECK_EVERY_SECONDS)
        try:
            print("Check:", check_plant())
        except Exception as e:
            print("Check failed:", e)


@app.route("/reading", methods=["POST"])
def reading():
    data = request.get_json(silent=True) or {}
    soil = data.get("soil")
    if soil is None:
        return jsonify({"error": "missing 'soil'"}), 400
    save_reading(soil)
    print(f"Got reading: soil={soil}")
    return jsonify({"ok": True})


@app.route("/check")
def manual_check():
    # Visit http://localhost:5000/check to test without waiting
    return check_plant()


@app.route("/")
def home():
    return "SlothPlant server is awake (slowly)."


if __name__ == "__main__":
    threading.Thread(target=background_loop, daemon=True).start()
    app.run(host="0.0.0.0", port=5000)