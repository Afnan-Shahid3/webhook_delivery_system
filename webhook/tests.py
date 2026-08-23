import requests

url = "http://127.0.0.1:8000/api/animal/"

cat = [
    "cat",
    "dog", 
    "elephant", 
    "lion", 
    "tiger", 
    "monkey", 
    "giraffe",
]
for name in cat:
    payload = {"name": name}
    response = requests.post(url, json=payload, timeout = 5)

    if response.status_code == 200:
        print("You selected an animal in the list")
    else:
        print("this is not an animal")