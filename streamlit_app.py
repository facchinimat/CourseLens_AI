import requests
import streamlit as st


# -----------------------------
# CONFIG
# -----------------------------

API_BASE_URL = "http://127.0.0.1:8000"

st.set_page_config(
    page_title="CourseLens AI",
    page_icon="📚",
    layout="wide"
)


# -----------------------------
# CUSTOM STYLING
# -----------------------------

st.markdown(
    """
    <style>
        .main {
            background-color: #0f172a;
        }

        .block-container {
            max-width: 1100px;
            padding-top: 2rem;
            padding-bottom: 2rem;
        }

        .hero-title {
            font-size: 2.6rem;
            font-weight: 800;
            margin-bottom: 0.25rem;
        }

        .hero-subtitle {
            font-size: 1.05rem;
            color: #94a3b8;
            margin-bottom: 1.5rem;
        }

        .source-card {
            border: 1px solid rgba(148, 163, 184, 0.25);
            border-radius: 12px;
            padding: 0.75rem 1rem;
            margin-bottom: 0.5rem;
            background: rgba(15, 23, 42, 0.45);
        }

        .source-title {
            font-weight: 700;
            color: #e2e8f0;
        }

        .source-meta {
            color: #94a3b8;
            font-size: 0.9rem;
        }

        .small-muted {
            color: #94a3b8;
            font-size: 0.9rem;
        }
    </style>
    """,
    unsafe_allow_html=True
)


# -----------------------------
# API HELPERS
# -----------------------------

def api_url(path: str) -> str:
    """Build a full backend URL from an endpoint path."""
    return f"{API_BASE_URL}{path}"


def handle_response(response: requests.Response):
    """Return JSON data if successful, otherwise return a readable error."""
    try:
        data = response.json()
    except Exception:
        data = None

    if response.ok:
        return data, None

    if isinstance(data, dict) and "detail" in data:
        return None, data["detail"]

    return None, f"Request failed with status code {response.status_code}"


def backend_is_online() -> bool:
    """Check whether the FastAPI backend is running."""
    try:
        response = requests.get(api_url("/health"), timeout=5)
        return response.ok
    except requests.RequestException:
        return False


def get_courses():
    """Fetch all courses from the backend."""
    try:
        response = requests.get(api_url("/courses"), timeout=10)
        return handle_response(response)
    except requests.RequestException as e:
        return None, str(e)


def create_course(name: str, description: str | None = None):
    """Create a new course."""
    payload = {
        "name": name,
        "description": description if description else None
    }

    try:
        response = requests.post(api_url("/courses"), json=payload, timeout=10)
        return handle_response(response)
    except requests.RequestException as e:
        return None, str(e)


def get_documents(course_id: str):
    """Fetch uploaded documents for a course."""
    try:
        response = requests.get(api_url(f"/courses/{course_id}/documents"), timeout=10)
        return handle_response(response)
    except requests.RequestException as e:
        return None, str(e)


def upload_document(course_id: str, uploaded_file):
    """Upload a PDF to the backend."""
    files = {
        "file": (
            uploaded_file.name,
            uploaded_file.getvalue(),
            "application/pdf"
        )
    }

    try:
        response = requests.post(
            api_url(f"/courses/{course_id}/documents"),
            files=files,
            timeout=90
        )
        return handle_response(response)
    except requests.RequestException as e:
        return None, str(e)


def create_chunks(course_id: str, document_id: str):
    """Create chunks for an uploaded document."""
    try:
        response = requests.post(
            api_url(f"/courses/{course_id}/documents/{document_id}/chunks"),
            timeout=90
        )
        return handle_response(response)
    except requests.RequestException as e:
        return None, str(e)


def index_document(course_id: str, document_id: str):
    """Index document chunks into ChromaDB."""
    try:
        response = requests.post(
            api_url(f"/courses/{course_id}/documents/{document_id}/index"),
            timeout=180
        )
        return handle_response(response)
    except requests.RequestException as e:
        return None, str(e)


def ask_question(course_id: str, question: str, top_k: int = 5):
    """Ask a question using the selected course documents."""
    payload = {
        "question": question,
        "top_k": top_k
    }

    try:
        response = requests.post(
            api_url(f"/courses/{course_id}/ask"),
            json=payload,
            timeout=180
        )
        return handle_response(response)
    except requests.RequestException as e:
        return None, str(e)


def process_pdf(course_id: str, uploaded_file):
    """
    Full hidden document pipeline.

    The user only sees one upload action, but behind the scenes this:
    1. Uploads the PDF.
    2. Creates chunks.
    3. Indexes the chunks into Chroma.
    """

    document, error = upload_document(course_id, uploaded_file)

    if error:
        return None, f"Upload failed: {error}"

    document_id = document["id"]

    chunks_result, error = create_chunks(course_id, document_id)

    if error:
        return None, f"Chunking failed: {error}"

    index_result, error = index_document(course_id, document_id)

    if error:
        return None, f"Indexing failed: {error}"

    return document, None


def format_sources(sources: list[dict]) -> list[dict]:
    """
    Deduplicate and format source metadata for display.

    The UI does not show internal IDs. It only shows filename and page number.
    """

    seen = set()
    clean_sources = []

    for source in sources:
        filename = source.get("filename", "Unknown file")
        page_number = source.get("page_number", "Unknown page")

        key = (filename, page_number)

        if key in seen:
            continue

        seen.add(key)

        clean_sources.append({
            "filename": filename,
            "page_number": page_number
        })

    return clean_sources


# -----------------------------
# SESSION STATE
# -----------------------------

if "messages" not in st.session_state:
    st.session_state.messages = []

if "selected_course_id" not in st.session_state:
    st.session_state.selected_course_id = None

if "selected_course_name" not in st.session_state:
    st.session_state.selected_course_name = None

if "processed_files" not in st.session_state:
    st.session_state.processed_files = set()


# -----------------------------
# BACKEND CHECK
# -----------------------------

if not backend_is_online():
    st.error("FastAPI backend is not running.")
    st.code("python -m uvicorn app.main:app --reload", language="bash")
    st.stop()


# -----------------------------
# SIDEBAR
# -----------------------------

with st.sidebar:
    st.title("📚 CourseLens AI")
    st.caption("Chat with your course PDFs.")

    st.success("Backend connected")

    st.divider()

    courses, error = get_courses()

    if error:
        st.error(error)
        courses = []

    st.subheader("Course")

    if courses:
        course_options = {
            course["name"]: course["id"]
            for course in courses
        }

        selected_course_name = st.selectbox(
            "Choose a course",
            options=list(course_options.keys())
        )

        st.session_state.selected_course_name = selected_course_name
        st.session_state.selected_course_id = course_options[selected_course_name]

    with st.expander("Create a new course", expanded=not bool(courses)):
        new_course_name = st.text_input(
            "Course name",
            placeholder="Example: CSE 220"
        )

        new_course_description = st.text_area(
            "Description",
            placeholder="Example: Systems Fundamentals I",
            height=80
        )

        if st.button("Create Course", use_container_width=True):
            if not new_course_name.strip():
                st.warning("Enter a course name.")
            else:
                course, error = create_course(
                    name=new_course_name.strip(),
                    description=new_course_description.strip()
                )

                if error:
                    st.error(error)
                else:
                    st.success("Course created.")
                    st.session_state.selected_course_id = course["id"]
                    st.session_state.selected_course_name = course["name"]
                    st.rerun()

    st.divider()

    if st.session_state.selected_course_id:
        st.subheader("Upload PDFs")

        uploaded_files = st.file_uploader(
            "Add course documents",
            type=["pdf"],
            accept_multiple_files=True,
            label_visibility="collapsed"
        )

        if uploaded_files:
            if st.button("Add PDFs to CourseLens", use_container_width=True):
                for uploaded_file in uploaded_files:
                    file_key = f"{st.session_state.selected_course_id}:{uploaded_file.name}"

                    if file_key in st.session_state.processed_files:
                        st.info(f"{uploaded_file.name} was already added in this session.")
                        continue

                    with st.spinner(f"Processing {uploaded_file.name}..."):
                        document, error = process_pdf(
                            st.session_state.selected_course_id,
                            uploaded_file
                        )

                    if error:
                        st.error(error)
                    else:
                        st.session_state.processed_files.add(file_key)
                        st.success(f"Added {uploaded_file.name}")

        documents, docs_error = get_documents(st.session_state.selected_course_id)

        if docs_error:
            st.error(docs_error)
        elif documents:
            st.markdown("### Documents")
            for doc in documents:
                st.markdown(f"- {doc['filename']}")

    st.divider()

    if st.button("Clear Chat", use_container_width=True):
        st.session_state.messages = []
        st.rerun()


# -----------------------------
# MAIN CHAT UI
# -----------------------------

st.markdown(
    """
    <div class="hero-title">Chat with your course documents</div>
    <div class="hero-subtitle">
        Upload PDFs, ask questions naturally, and get answers grounded in your course material.
    </div>
    """,
    unsafe_allow_html=True
)

if not st.session_state.selected_course_id:
    st.info("Create or select a course in the sidebar to begin.")
    st.stop()


# Empty-state starter examples
if not st.session_state.messages:
    st.info("Upload a PDF in the sidebar, then ask a question below.")

    example_cols = st.columns(3)

    with example_cols[0]:
        st.markdown("**Try:** What is the grading scheme?")

    with example_cols[1]:
        st.markdown("**Try:** When are the exams?")

    with example_cols[2]:
        st.markdown("**Try:** What are the late policies?")


# Render previous chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

        if message["role"] == "assistant" and message.get("sources"):
            clean_sources = format_sources(message["sources"])

            if clean_sources:
                st.markdown("**Sources**")

                for index, source in enumerate(clean_sources, start=1):
                    st.markdown(
                        f"""
                        <div class="source-card">
                            <div class="source-title">[{index}] {source["filename"]}</div>
                            <div class="source-meta">Page {source["page_number"]}</div>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )


# Chat input
user_question = st.chat_input("Ask a question about your course documents...")

if user_question:
    st.session_state.messages.append({
        "role": "user",
        "content": user_question
    })

    with st.chat_message("user"):
        st.markdown(user_question)

    with st.chat_message("assistant"):
        with st.spinner("Searching your course documents..."):
            result, error = ask_question(
                course_id=st.session_state.selected_course_id,
                question=user_question,
                top_k=5
            )

        if error:
            st.error(error)

            st.session_state.messages.append({
                "role": "assistant",
                "content": f"Sorry, I ran into an issue: {error}",
                "sources": []
            })

        else:
            answer = result.get("answer", "")
            sources = result.get("sources", [])

            st.markdown(answer)

            clean_sources = format_sources(sources)

            if clean_sources:
                st.markdown("**Sources**")

                for index, source in enumerate(clean_sources, start=1):
                    st.markdown(
                        f"""
                        <div class="source-card">
                            <div class="source-title">[{index}] {source["filename"]}</div>
                            <div class="source-meta">Page {source["page_number"]}</div>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )

            st.session_state.messages.append({
                "role": "assistant",
                "content": answer,
                "sources": sources
            })
