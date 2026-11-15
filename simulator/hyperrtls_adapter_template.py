"""
TEMPLATE ONLY — do not assume this is a working HyperRTLS API client.

Purpose:
Convert the real output of your chosen HyperRTLS installation into the
common position format used by the FastAPI backend.

Expected backend payload:

{
    "tag_id": "TAG001",
    "x": 5.2,
    "y": 4.1,
    "z": 1.2,
    "accuracy": 0.12,
    "source": "hyperrtls"
}

Once you know exactly how your HyperRTLS setup exposes location data
(HTTP, WebSocket, MQTT, serial, etc.), replace `read_hyperrtls_position()`
with the real code.

Example structure:

    import requests

    backend = "http://127.0.0.1:8000/api/positions"

    data = read_hyperrtls_position()

    requests.post(backend, json={
        "tag_id": data["tag_id"],
        "x": data["x"],
        "y": data["y"],
        "z": data.get("z", 0),
        "accuracy": data.get("accuracy"),
        "source": "hyperrtls"
    })

Do not copy a guessed URL from an example on the internet. Confirm the
interface in the exact HyperRTLS version/repositories you install.
"""

def read_hyperrtls_position():
    raise NotImplementedError(
        "Replace this function after confirming the real HyperRTLS output interface."
    )
