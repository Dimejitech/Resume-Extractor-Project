# file_reader.py
import PyPDF2

import docx
from docx import Document

def read_pdf(file_obj):
    reader = PyPDF2.PdfReader(file_obj)
    text = ""
    for page in reader.pages:
        text += page.extract_text() or ""
    return text

def read_docx(file_obj):
    doc = docx.Document(file_obj)
    text = ""
    for para in doc.paragraphs:
        text += para.text + "\n"
    return text