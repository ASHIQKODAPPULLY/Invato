import requests

try:
    response = requests.get('http://127.0.0.1:5000')
    print(f"Status Code: {response.status_code}")
    print("Connection successful!")
except requests.exceptions.ConnectionError:
    print("Connection failed!")
except Exception as e:
    print(f"Error: {str(e)}") 