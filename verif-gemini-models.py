
import requests
import tomllib

with open("config.toml", "rb") as f:
    config = tomllib.load(f)

API_KEY = config["gemini"]["api_key"]

url = "https://generativelanguage.googleapis.com/v1beta/models"

headers = {
    "x-goog-api-key": API_KEY
}

try:
    response = requests.get(
        url,
        headers=headers,
        params={"pageSize": 1000},
        timeout=30
    )

    response.raise_for_status()

    data = response.json()

    print("\n===== MODELES GEMINI DISPONIBLES =====\n")

    for model in data.get("models", []):

        print("Nom :", model.get("name"))
        print("Description :", model.get("description"))
        print("Input tokens :", model.get("inputTokenLimit"))
        print("Output tokens :", model.get("outputTokenLimit"))
        print("Actions :", model.get("supportedGenerationMethods"))
        print("-" * 60)

except requests.exceptions.RequestException as e:
    print("Erreur API :", e)

for model in data.get("models", []):

    actions = model.get("supportedGenerationMethods", [])

    if "generateContent" in actions:
        print(model["name"])