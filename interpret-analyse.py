<<<<<<< HEAD
from docx import Document
import datetime

file_path = f"rapport_or_argent.docx"
=======

from docx import Document
import datetime
import requests
import tomllib

with open("config.toml", "rb") as config_file:
    config = tomllib.load(config_file)

API_KEY = config["gemini"]["api_key"]
MODEL = config["gemini"]["model"]


file_path = "rapport_or_argent.docx"
>>>>>>> d522091 (ajout-verif-gemini)

doc = Document(file_path)

liste_rapport = []

for paragraph in doc.paragraphs:
<<<<<<< HEAD
    #print(paragraph.text)
    liste_rapport.append(paragraph.text)
demmande_modele="""
"faute un interpretation d'exertise dans le
" marché de l'or et l'argente """+str(liste_rapport)+"""l'interpratation 
jusqu'a"""+ str(datetime.datetime.now())
print(demmande_modele)
=======
    if paragraph.text.strip():
        liste_rapport.append(paragraph.text)

for table in doc.tables:
    for row in table.rows:
        for cell in row.cells:
            if cell.text.strip():
                liste_rapport.append(cell.text)

texte_rapport = "\n".join(liste_rapport)
demande_modele = f"""
Tu es un analyste financier expert spécialisé
dans les marchés de l'or et de l'argent.

Analyse le rapport suivant :

{texte_rapport}

Date de l'analyse :
{datetime.datetime.now().strftime("%d/%m/%Y %H:%M")}

Fournis une analyse professionnelle structurée :

1. Résumé général du marché.
2. Analyse de l'évolution du prix de l'or.
3. Analyse de l'évolution du prix de l'argent.
4. Tendances et indicateurs importants.
5. Facteurs économiques et géopolitiques.
6. Opportunités et risques.
7. Perspectives à court et moyen terme.
8. Conclusion et recommandations.

Important :
- Utilise uniquement les données disponibles dans le rapport.
- Ne fabrique aucune donnée ni aucun prix.
- Distingue les faits des hypothèses.
- Signale les informations manquantes.
- Présente une analyse claire et détaillée.
"""


url = (
    f"https://generativelanguage.googleapis.com/v1beta/"
    f"models/{MODEL}:generateContent"
)

headers = {
    "Content-Type": "application/json",
    "x-goog-api-key": API_KEY
}

payload = {
    "contents": [
        {
            "parts": [
                {
                    "text": demande_modele
                }
            ]
        }
    ],
    "generationConfig": {
        "temperature": 0.4,
        "maxOutputTokens": 4000
    }
}

try:
    response = requests.post(
        url,
        headers=headers,
        json=payload,
        timeout=120
    )

    response.raise_for_status()

    resultat = response.json()



    texte_reponse = resultat["candidates"][0]["content"]["parts"][0]["text"]

    print("\n========== ANALYSE GEMINI ==========\n")
    print(texte_reponse)

except requests.exceptions.HTTPError:
    print("Erreur HTTP :", response.status_code)
    print(response.text)

except requests.exceptions.RequestException as e:
    print("Erreur de connexion :", e)

except (KeyError, IndexError, TypeError):
    print("Réponse Gemini inattendue :")
    print(resultat)
>>>>>>> d522091 (ajout-verif-gemini)
