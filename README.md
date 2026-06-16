# CourseLens AI

CourseLens AI is an AI-powered course document assistant that lets students upload course PDFs and ask natural-language questions about their course material. The app extracts text from PDFs, chunks the content, creates vector embeddings, stores searchable document chunks in ChromaDB, retrieves the most relevant sources, and generates AI answers with source citations.

The goal of this project is to build a practical RAG-based study assistant for students.

---

## Demo Flow

### User-Facing Flow

1. Create or select a course.
2. Upload one or more course PDFs.
3. CourseLens automatically processes the PDF in the background.
4. Ask a question in the chat interface.
5. Receive an AI-generated answer grounded in the uploaded documents.
6. View source citations showing the filename and page number used.

Example question:

```text
What is the grading scheme?
```

Example answer:

```text
The grading scheme includes three midterm exams worth 54% of the final grade, homework worth 16%, programming assignments worth 15%, and a final exam worth 15%.

Sources:
[1] Class_Syllabus.pdf — Page 8
```

---

## What CourseLens AI Does

CourseLens AI follows a Retrieval-Augmented Generation pipeline:

```text
PDF Upload
   ↓
Save Raw PDF
   ↓
Extract Text Page by Page
   ↓
Save Processed JSON
   ↓
Chunk Text with Metadata
   ↓
Generate OpenAI Embeddings
   ↓
Store Text, Vectors, and Metadata in ChromaDB
   ↓
Retrieve Relevant Chunks
   ↓
Send Retrieved Context to LLM
   ↓
Generate Answer with Sources
```

---

## Tech Stack

| Layer                 | Technology         |
| --------------------- | ------------------ |
| Backend               | FastAPI            |
| Language              | Python             |
| Frontend              | Streamlit          |
| PDF Processing        | PyMuPDF            |
| Data Validation       | Pydantic           |
| Embeddings            | OpenAI Embeddings  |
| Answer Generation     | OpenAI LLM         |
| Vector Database       | ChromaDB           |
| Local Persistence     | JSON files         |
| Environment Variables | python-dotenv      |
| API Testing           | FastAPI Swagger UI |
| Version Control       | Git / GitHub       |

---

## Project Structure

```text
CourseLens_AI/
│
├── app/
│   ├── main.py              # FastAPI app, API endpoints, RAG pipeline
│   ├── schemas.py           # Pydantic request/response models
│   └── pdf_utils.py         # PDF text extraction helper
│
├── data/
│   ├── raw/                 # Uploaded PDFs
│   ├── processed/           # Extracted page-level JSON files
│   ├── chunks/              # Chunked document JSON files
│   ├── chroma/              # Local Chroma vector database
│   └── app/                 # Local JSON metadata persistence
│
├── streamlit_app.py         # Temporary Streamlit chat UI
├── .env                     # API keys, not committed to GitHub
├── .gitignore
├── requirements.txt
└── README.md
```

---

## API Endpoints

### Health Check

```http
GET /health
```

Checks if the backend is running.

---

### Create Course

```http
POST /courses
```

Creates a new course.

Example request:

```json
{
  "name": "Intro to Programming",
  "description": "Python"
}
```

---

### Get Courses

```http
GET /courses
```

Returns all saved courses.

---

### Get Course by ID

```http
GET /courses/{course_id}
```

Returns one course by its unique ID.

---

### Upload PDF Document

```http
POST /courses/{course_id}/documents
```

Uploads a PDF to a course, saves the raw file, extracts page-level text, and stores processed JSON.

---

### Get Documents for Course

```http
GET /courses/{course_id}/documents
```

Returns uploaded document metadata for a specific course.

---

### Create Chunks

```http
POST /courses/{course_id}/documents/{document_id}/chunks
```

Loads the processed JSON file, splits page text into chunks, attaches metadata, and saves the chunks.

---

### Get Chunks

```http
GET /courses/{course_id}/documents/{document_id}/chunks
```

Returns all chunks for a document.

---

### Index Chunks into ChromaDB

```http
POST /courses/{course_id}/documents/{document_id}/index
```

Creates embeddings for each chunk and stores chunk IDs, vectors, text, and metadata in ChromaDB.

---

### Semantic Search

```http
POST /courses/{course_id}/search
```

Searches indexed course chunks using a natural-language query.

Example request:

```json
{
  "query": "What are the midterm exam policies?",
  "top_k": 5
}
```

Example response:

```json
[
  {
    "chunk_id": "document123_p6_c2",
    "document_id": "document123",
    "filename": "class_Syllabus.pdf",
    "page_number": 6,
    "chunk_index": 2,
    "text": "Students must take three in-person, cumulative midterm exams...",
    "distance": 1.061
  }
]
```

---

### Ask CourseLens AI

```http
POST /courses/{course_id}/ask
```

Retrieves the most relevant chunks from ChromaDB, formats them as context, sends them to an OpenAI LLM, and returns an AI-generated answer with source metadata.

Example request:

```json
{
  "question": "What is the grading scheme?",
  "top_k": 5
}
```

Example response:

```json
{
  "answer": "The grading scheme includes three midterm exams worth 54% of the final grade, homework worth 16%, programming assignments worth 15%, and a final exam worth 15%.",
  "sources": " ... "
}
```

---

## Setup Instructions

### 1. Clone the Repository

```bash
git clone https://github.com/facchinimat/CourseLens_AI.git
cd CourseLens_AI
```

---

### 2. Create a Virtual Environment

```bash
python -m venv .venv
```

Activate it on Windows Git Bash:

```bash
source .venv/Scripts/activate
```

Activate it on Mac/Linux:

```bash
source .venv/bin/activate
```

---

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

---

### 4. Create a `.env` File

Create a `.env` file in the project root:

```env
OPENAI_API_KEY=your_openai_api_key_here
```

Do not commit this file to GitHub.

---

### 5. Run the FastAPI Backend

```bash
python -m uvicorn app.main:app --reload
```

Open the FastAPI docs:

```text
http://127.0.0.1:8000/docs
```

---

### 6. Run the Streamlit UI

In a second terminal, run:

```bash
streamlit run streamlit_app.py
```

The Streamlit app provides a temporary user interface for creating/selecting courses, uploading PDFs, and chatting with course documents.

---

## Local Data and Privacy

This project stores local development data inside the `data/` folder:

```text
data/raw/          Uploaded PDFs
data/processed/    Extracted page-level text
data/chunks/       Chunked document text
data/chroma/       Local ChromaDB vector database files
data/app/          Local course and document metadata JSON files
```

These files are ignored by Git to avoid uploading private course documents, extracted text, embeddings, metadata, or API-related data.

The repository only tracks `.gitkeep` files to preserve the folder structure.

---

## Roadmap

### Phase 1: Backend Foundation

* Create FastAPI app
* Add course endpoints
* Add document upload
* Add schema validation

### Phase 2: PDF Processing

* Save raw PDFs
* Extract page-level text
* Save processed JSON files

### Phase 3: Chunking

* Split page text into chunks
* Add metadata to each chunk
* Save chunks to JSON

### Phase 4: Embeddings and Search

* Generate OpenAI embeddings
* Store chunks in ChromaDB
* Add semantic search endpoint

### Phase 5: RAG Answer Generation

* Retrieve top chunks
* Send chunks and user question to an LLM
* Generate source-grounded answers
* Return filename and page number citations
* Handle “answer not found in source” cases

### Phase 6: Persistence and Product UI

* Persist courses and document metadata with JSON
* Add temporary Streamlit UI
* Hide backend processing steps from the user
* Build a cleaner chat-based interface

### Phase 7: Product Polish

* Add delete document and delete course functionality
* Add update course functionality
* Add quiz and flashcard generation
* Add weak-topic tracking
* Add tests
* Add Docker support
* Deploy backend and frontend
* Add screenshots and demo video

---

## What I Learned

Through this project, I learned how to:

* Build REST API endpoints with FastAPI
* Use Pydantic schemas for request and response validation
* Process uploaded PDF files in Python
* Store raw, processed, and chunked document data
* Design a RAG-style document assistant
* Generate embeddings using OpenAI
* Store and query vectors using ChromaDB
* Preserve metadata for source citations
* Build an `/ask` endpoint that retrieves relevant chunks before generating an answer
* Use prompt instructions to reduce hallucinations and keep answers grounded in uploaded documents
* Add local JSON persistence for course and document metadata
* Build a basic Streamlit interface connected to a FastAPI backend
* Debug API errors, schema mismatches, vector search issues, and LLM response issues
* Use Git and GitHub for version control

---

## Future Improvements

* Improve the Streamlit UI into a polished chat experience
* Add clickable source citations
* Add document and course deletion
* Add course update/editing
* Add quiz and flashcard generation
* Add weak-topic tracking based on student questions
* Store courses and documents in SQLite, PostgreSQL, or Supabase
* Add automated tests with pytest
* Add Docker support
* Deploy the app

---

## Author

**Matteo Facchini**  
Computer Science Student at **Stony Brook University**  
Building practical software and AI projects

- LinkedIn: [Matteo Facchini](https://www.linkedin.com/in/matteo-facchini-b14667352/)

