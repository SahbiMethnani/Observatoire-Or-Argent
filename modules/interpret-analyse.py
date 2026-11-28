from docx import Document

file_path = r"C:\Users\hp\Bureau\Gold-analyser\rapport_or_argent.docx"

doc = Document(file_path)

liste_rapport = []

for paragraph in doc.paragraphs:
    #print(paragraph.text)
    liste_rapport.append(paragraph.text)

