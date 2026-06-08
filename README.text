# CourseLens AI

CourseLens AI is an AI-powered course document assistant that lets students upload course PDFs, extract text, chunk the material, create vector embeddings, and semantically search course content using natural language.


## Demo Flow

1. Create a course.
2. Upload a course PDF.
3. Extract text from the PDF page by page.
4. Split extracted text into smaller chunks.
5. Generate OpenAI embeddings for each chunk.
6. Store vectors, text, and metadata in Chroma.
7. Search the course material using natural language.

Example query:

```text
When are midterms?
```

Example returned result:

```json
{
  "filename": "CSE220_Syllabus_SPR2026.pdf",
  "page_number": 6,
  "text": "Students must take three in-person, cumulative midterm exams...",
  "distance": 1.061
}
```

---

## Features

### Completed

* FastAPI backend with automatic API docs
* Course creation and retrieval
* PDF upload by course
* Raw PDF storage
* Page-level PDF text extraction using PyMuPDF
* Processed JSON storage for extracted text
* Text chunking with overlap
* Chunk metadata preservation
* Chroma vector database integration
* OpenAI embedding generation
* Semantic search over indexed course documents
* Source metadata returned with search results, including filename and page number

### In Progress / Planned

* LLM-generated answers using retrieved chunks
* Citation-based AI tutor responses
* Quiz generation from course material
* Weak-area tracking
* Streamlit frontend
* Persistent database for courses/documents
* Better error handling and test coverage
* Docker setup

---

## Tech Stack

| Layer                 | Technology         |
| --------------------- | ------------------ |
| Backend               | FastAPI            |
| Language              | Python             |
| PDF Processing        | PyMuPDF            |
| Data Validation       | Pydantic           |
| Embeddings            | OpenAI Embeddings  |
| Vector Database       | ChromaDB           |
| Environment Variables | python-dotenv      |
| API Testing           | FastAPI Swagger UI |
| Version Control       | Git / GitHub       |

---

## Architecture

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
Generate Embeddings
   ↓
Store in Chroma Vector Database
   ↓
Semantic Search
   ↓
Future: LLM Answer with Citations
```

---

## Project Structure

```text
CourseLens_AI/
│
├── app/
│   ├── main.py              # FastAPI app and API endpoints
│   ├── schemas.py           # Pydantic data models
│   └── pdf_utils.py         # PDF text extraction helper
│
├── data/
│   ├── raw/                 # Uploaded PDFs
│   ├── processed/           # Extracted page-level JSON files
│   ├── chunks/              # Chunked document JSON files
│   └── chroma/              # Local Chroma vector database
│
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
  "name": "CSE 220",
  "description": "Systems Fundamentals I"
}
```

---

### Get Courses

```http
GET /courses
```

Returns all created courses.

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

Uploads a PDF to a course, saves the raw file, extracts text, and stores page-level processed JSON.

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

### Index Chunks into Chroma

```http
POST /courses/{course_id}/documents/{document_id}/index
```

Creates embeddings for each chunk and stores them in Chroma with metadata.

---

### Semantic Search

```http
POST /courses/{course_id}/search
```

Searches indexed course chunks using a natural language query.

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
    "filename": "CSE220_Syllabus.pdf",
    "page_number": 6,
    "chunk_index": 2,
    "text": "Students must take three in-person, cumulative midterm exams...",
    "distance": 1.061
  }
]
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

Activate it:

```bash
source .venv/Scripts/activate
```

On Mac/Linux:

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

### 5. Run the Server

```bash
python -m uvicorn app.main:app --reload
```

Open the FastAPI docs:

```text
http://127.0.0.1:8000/docs
```

---

## Local Data and Privacy

This project stores local development files in the `data/` folder:

```text
data/raw/         Uploaded PDFs
data/processed/   Extracted page text
data/chunks/      Chunked document text
data/chroma/      Local vector database files
```

These files are ignored by Git to avoid uploading private course documents, extracted text, embeddings, or API-related data.

The repository tracks only `.gitkeep` files to preserve the folder structure.

---

## Current Limitations

* Course and document metadata are stored in memory, so they reset when the server restarts.
* The current system returns relevant chunks, not full AI-generated answers yet.
* Search quality depends on PDF text extraction and chunk quality.
* Chroma data is stored locally for development.
* No frontend has been added yet.
* No authentication or user accounts yet.

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
* Store chunks in Chroma
* Add semantic search endpoint

### Phase 5: RAG Answer Generation

* Retrieve top chunks
* Send chunks and user question to an LLM
* Generate answers with citations
* Handle “answer not found in source” cases

### Phase 6: Product Polish

* Streamlit frontend
* Persistent database
* Testing
* Dockerization
* Deployment
* Demo video

---

## What I Learned

Through this project, I learned how to:

* Build REST API endpoints with FastAPI
* Use Pydantic schemas for request and response validation
* Process uploaded PDF files in Python
* Store raw, processed, and chunked document data
* Design a basic RAG-style document pipeline
* Generate embeddings using OpenAI
* Store and query vectors using Chroma
* Preserve metadata for source citations
* Debug API errors, schema mismatches, and vector search issues
* Use Git and GitHub for version control

---


## Future Improvements

* Add LLM-generated tutor answers with citations
* Add quiz and flashcard generation
* Add weak-topic tracking based on student questions
* Add Streamlit frontend
* Store courses and documents in SQLite or PostgreSQL
* Add automated tests with pytest
* Add Docker support
* Deploy backend and frontend
* Add screenshots and demo video

---

## Author

Matteo Facchini
Computer Science Student, Stony Brook University
Project: CourseLens AI
