import fitz  # PyMuPDF imports as "fitz"

def extract_text_by_page(file_path: str) -> list[dict]:
    pdf = fitz.open(file_path)
    pages = []

    for page_index, page in enumerate(pdf, start=1):
        text = page.get_text()

        pages.append({
            "page_number": page_index,
            "text": text
        })

    pdf.close()
    return pages