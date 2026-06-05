import fitz  # PyMuPDF imports as "fitz"

def extract_text_by_page(file_path: str) -> list[str]:
    pdf = fitz.open(file_path)          # open the PDF file
    pages = []
    for page in pdf:                    # loop over every page
        text = page.get_text()          # extract all text from that page
        pages.append(text)              # add it to the list
    pdf.close()
    return pages                        # returns ["page 1 text", "page 2 text", ...]