import math
import random
import time

import requests

SERVER = "http://127.0.0.1:8000"
URL = f"{SERVER}/api/positions"

# Change these to simulate different tags.
TAGS = [
    ("TAG001", 0.0),
    ("TAG002", 2.2),
    ("TAG003", 4.4),
]

print("UWB simulator started.")
print("Sending simulated UWB positions to:", URL)
print("Press Ctrl+C to stop.")

t = 0.0

while True:
    for tag_id, phase in TAGS:
        # Indoor coordinate system:
        # x = 0..10 meters
        # y = 0..10 meters
        #
        # TAG001 moves around the centre.
        # TAG002 follows another path.
        # TAG003 moves through different areas.
        if tag_id == "TAG001":
            x = 5 + 3.7 * math.cos(t + phase)
            y = 5 + 3.7 * math.sin(t + phase)
        elif tag_id == "TAG002":
            x = 1.5 + 7.0 * ((math.sin(t * 0.45 + phase) + 1) / 2)
            y = 5 + 2.5 * math.sin(t * 0.9 + phase)
        else:
            x = 5 + 4.0 * math.cos(t * 0.55 + phase)
            y = 5 + 4.0 * math.sin(t * 0.55 + phase)

        # Small measurement noise to make it look more like sensor data.
        x += random.gauss(0, 0.04)
        y += random.gauss(0, 0.04)

        payload = {
            "tag_id": tag_id,
            "x": round(x, 3),
            "y": round(y, 3),
            "z": 1.2,
            "accuracy": round(random.uniform(0.07, 0.15), 3),
            "source": "simulator"
        }

        try:
            response = requests.post(URL, json=payload, timeout=2)
            response.raise_for_status()
            print(payload)
        except requests.RequestException as exc:
            print("Server error:", exc)

    t += 0.25
    time.sleep(1)
