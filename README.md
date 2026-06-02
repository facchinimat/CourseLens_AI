# CourseLens AI

**CourseLens AI** is a Python-based AI course tutor that helps students study from uploaded lecture slides, notes, and PDFs. It uses **RAG** (Retrieval-Augmented Generation), **embeddings**, and **source citations** to answer questions, generate quizzes, and identify weak areas for more focused studying.

## Features

| Feature | Description |
|---|---|
| 📄 **Document Upload** | Upload PDFs; text is extracted page-by-page and indexed into ChromaDB |
| 💬 **Q&A with Citations** | Ask questions; get answers grounded in your materials with page-level source citations |
| 📝 **Quiz Generation** | Auto-generate multiple-choice quizzes on any topic from your uploaded content |
| 📊 **Weak Area Analysis** | Accumulate quiz results and get an AI-powered breakdown of where to study harder |

## Tech Stack

- **FastAPI** — REST API and static file serving  
- **LangChain + OpenAI** — LLM chain for Q&A, quiz generation, and analysis  
- **ChromaDB** — local persistent vector store  
- **pypdf** — PDF text extraction  
- **Bootstrap 5** — frontend UI  

## Quick Start

### 1. Clone & install

```bash
git clone https://github.com/facchinimat/CourseLens_AI.git
cd CourseLens_AI
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env and set your OPENAI_API_KEY
```

### 3. Run the server

```bash
uvicorn app.main:app --reload
```

Open **http://localhost:8000** in your browser.

## Usage

1. **Upload materials** — drag-and-drop or click the sidebar upload zone to add PDFs.
2. **Ask questions** — type in the Q&A tab; answers include clickable source citations.
3. **Take a quiz** — choose a topic and number of questions, then submit to see your score.
4. **Review analysis** — after completing quizzes the Analysis tab shows weak and strong areas with personalised study recommendations.

## API Reference

Full interactive docs are available at **http://localhost:8000/docs**.

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/documents/upload` | Upload a PDF |
| `GET` | `/api/documents` | List indexed documents |
| `DELETE` | `/api/documents/{filename}` | Remove a document |
| `POST` | `/api/qa/ask` | Ask a question (RAG) |
| `POST` | `/api/quiz/generate` | Generate a quiz |
| `POST` | `/api/quiz/submit` | Submit answers and get scored results |
| `POST` | `/api/analysis/weak-areas` | Analyse quiz history for weak areas |

## Project Structure

```
CourseLens_AI/
├── app/
│   ├── main.py                   # FastAPI application
│   ├── core/
│   │   ├── config.py             # Settings (pydantic-settings)
│   │   ├── document_processor.py # PDF extraction & chunking
│   │   ├── vector_store.py       # ChromaDB wrapper
│   │   └── rag_engine.py         # Q&A, quiz, analysis logic
│   ├── api/routes/               # FastAPI routers
│   └── models/schemas.py         # Pydantic request/response models
├── static/                       # Frontend (HTML/CSS/JS)
├── tests/                        # pytest test suite
├── data/                         # Vector DB & uploads (git-ignored)
├── requirements.txt
└── .env.example
```

## Running Tests

```bash
pytest tests/ -v
```

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `OPENAI_API_KEY` | *(required)* | Your OpenAI API key |
| `LLM_MODEL` | `gpt-4o-mini` | OpenAI chat model |
| `EMBEDDING_MODEL` | `text-embedding-3-small` | OpenAI embedding model |
| `CHUNK_SIZE` | `1000` | Characters per text chunk |
| `CHUNK_OVERLAP` | `200` | Overlap between chunks |
| `MAX_RETRIEVAL_DOCS` | `5` | Documents retrieved per query |
| `CHROMA_DB_PATH` | `data/chroma_db` | Vector store location |
| `UPLOAD_DIR` | `data/uploads` | PDF storage location |

