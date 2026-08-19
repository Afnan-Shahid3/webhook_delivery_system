import requests

url = "http://127.0.0.1:8000/api/animal/"

cat = {
    "name" : "cat"
}

response = requests.post(url, json=cat)

if response.status_code == 200:
    print("You selected an animal in the list")
else:
    print("this is not an animal")