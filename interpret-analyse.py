from docx import Document
import datetime

file_path = f"rapport_or_argent.docx"

doc = Document(file_path)

liste_rapport = []

for paragraph in doc.paragraphs:
    #print(paragraph.text)
    liste_rapport.append(paragraph.text)
demmande_modele="""
"faute un interpretation d'exertise dans le
" marché de l'or et l'argente """+str(liste_rapport)+"""l'interpratation 
jusqu'a"""+ str(datetime.datetime.now())
print(demmande_modele)
