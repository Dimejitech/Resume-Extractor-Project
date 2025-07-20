from app.file_reader import read_pdf, read_docx
from app.extractor import extract_resume_data

def main():
    # Provide the path to a sample resume file
    filepath = "sample_resume.pdf"  # Change to .docx if testing DOCX files

    # Determine file type
    if filepath.lower().endswith(".pdf"):
        with open(filepath, "rb") as f:
            text = read_pdf(f)
    elif filepath.lower().endswith(".docx"):
        with open(filepath, "rb") as f:
            text = read_docx(f)
    else:
        print("Unsupported file format.")
        return

    # Extract data
    extracted = extract_resume_data(text)

    # Display in terminal
    print("\n📋 Extracted Resume Information:")
    for section, content in extracted.items():
        print(f"\n{section.upper()}:")
        if isinstance(content, list):
            for item in content:
                print(f" - {item}")
        else:
            print(f" {content}")

if __name__ == "__main__":
    main()
