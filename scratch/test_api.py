import requests

try:
    response = requests.get('http://localhost:8000/api/obtener-compra/146/')
    print("Status Code:", response.status_code)
    print("Response JSON/Text:", response.text)
except Exception as e:
    print("Error:", e)
