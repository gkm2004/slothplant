# SlothPlant 🦥🌱

A plant caretaker for people who forget their plants. An Arduino watches the soil all day, a small open-weight model running **locally** reads the readings, and your phone gets a sleepy two-line message only when the plant actually needs you.

Built for the Hacktoberfest Open-Source AI Challenge (Week 3: Sloth Day). It grew out of a class assignment on Arduino, and the open-source AI part was built this week.

## How it works

```
Soil sensor -> Arduino UNO R4 WiFi -> Flask server (laptop) -> Ollama (gemma3:1b) -> ntfy -> your phone
```

1. The Arduino reads the soil moisture sensor every few seconds and sends the value over WiFi.
2. A small Flask server saves each reading to `readings.csv`.
3. On a schedule, the server looks at recent readings and works out the trend.
4. A local open-weight model (`gemma3:1b` through Ollama) writes the plant's message and judges borderline cases.
5. The message arrives on your phone through [ntfy](https://ntfy.sh).

Clear cases (very dry, very wet) are decided by simple rules, because a 1B model was unreliable at yes/no decisions. The model writes every message and decides the in-between zone.

## Why open source matters here

Everything runs on your own machine. No API keys, no cloud AI, no cost, and your home data never leaves your laptop. Anyone can reproduce it with a cheap board and a free model.

## Hardware

- Arduino UNO R4 WiFi
- Soil moisture sensor (analog, on pin `A0`)
- A laptop that can run a 1B model (it works on 8 GB of RAM)

Higher readings mean drier soil on this sensor. The sensor approach is based on the SunFounder soil moisture examples.

## Setup

1. Install [Ollama](https://ollama.com) and pull the model: `ollama pull gemma3:1b`
2. Install Python packages: `python -m pip install -r requirements.txt`
3. Install the ntfy app on your phone and subscribe to a topic of your choice.
4. Edit the settings at the top of `server.py` (`NTFY_TOPIC`, `DRY_THRESHOLD`, and so on).
5. Open `slothplant.ino` in the Arduino IDE and fill in `WIFI_SSID`, `WIFI_PASS`, and `SERVER_IP` (your laptop's IPv4 address from `ipconfig`). Do not commit your real WiFi details.
6. Run the server: `python server.py`
7. Upload the sketch to the Arduino. Readings should start appearing in `readings.csv`.

The laptop and the Arduino must be on the same network. The R4 WiFi only supports 2.4 GHz, and public or guest networks often block device-to-device traffic, so a phone hotspot is a good option.

To test without waiting, open `http://localhost:5000/check`.

## Calibration

Dry, wet, and freshly watered readings differ between sensors. Measure yours (in air, in water, in watered soil) and update `DRY_THRESHOLD` and `WET_EXAMPLE` in `server.py`.

## License

MIT