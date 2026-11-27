from docx import Document

file_path = r"C:\Users\hp\Bureau\Gold-analyser\rapport.docx"
doc = Document(file_path)
for paragraph in doc.paragraphs:
    print(paragraph.text)