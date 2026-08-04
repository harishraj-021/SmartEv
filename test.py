import requests

API_KEY = "PASTE_YOUR_OPENROUTESERVICE_KEY_HERE"

headers = {
    "Authorization": API_KEY,
    "Content-Type": "application/json"
}

body = {
    "coordinates": [
        [80.2707, 13.0827],   # Chennai
        [77.5946, 12.9716]    # Bangalore
    ]
}

response = requests.post(
    "https://api.openrouteservice.org/v2/directions/driving-car",
    headers=headers,
    json=body
)

print(response.status_code)
print(response.text)
python test.py
