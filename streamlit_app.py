import streamlit as st
import requests

API_URL = "http://127.0.0.1:8000"

st.set_page_config(page_title="CourseLens AI", page_icon="📚")

st.title("📚 CourseLens AI")
st.write("Upload course PDFs, index them, and search your course material.")

# Keep IDs in session state so Streamlit remembers them during reruns
if "course_id" not in st.session_state:
    st.session_state.course_id = None

if "document_id" not in st.session_state:
    st.session_state.document_id = None


st.header("1. Create a Course")

course_name = st.text_input("Course name", placeholder="CSE 220")
course_description = st.text_input("Course description", placeholder="Systems Fundamentals I")

if st.button("Create Course"):
    response = requests.post(
        f"{API_URL}/courses",
        json={
            "name": course_name,
            "description": course_description
        }
    )

    if response.status_code == 200:
        course = response.json()
        st.session_state.course_id = course["id"]
        st.success("Course created successfully")
        st.json(course)
    else:
        st.error(response.text)


st.header("2. Upload a PDF")

uploaded_file = st.file_uploader("Upload course PDF", type=["pdf"])

if st.button("Upload PDF"):
    if not st.session_state.course_id:
        st.error("Create a course first.")
    elif uploaded_file is None:
        st.error("Upload a PDF first.")
    else:
        files = {
            "file": (
                uploaded_file.name,
                uploaded_file.getvalue(),
                "application/pdf"
            )
        }

        response = requests.post(
            f"{API_URL}/courses/{st.session_state.course_id}/documents",
            files=files
        )

        if response.status_code == 200:
            document = response.json()
            st.session_state.document_id = document["id"]
            st.success("PDF uploaded and text extracted")
            st.json(document)
        else:
            st.error(response.text)


st.header("3. Create Chunks")

if st.button("Create Chunks"):
    if not st.session_state.course_id or not st.session_state.document_id:
        st.error("Create a course and upload a PDF first.")
    else:
        response = requests.post(
            f"{API_URL}/courses/{st.session_state.course_id}/documents/{st.session_state.document_id}/chunks"
        )

        if response.status_code == 200:
            st.success("Chunks created successfully")
            st.json(response.json())
        else:
            st.error(response.text)


st.header("4. Index Document")

if st.button("Index Document"):
    if not st.session_state.course_id or not st.session_state.document_id:
        st.error("Create a course and upload a PDF first.")
    else:
        response = requests.post(
            f"{API_URL}/courses/{st.session_state.course_id}/documents/{st.session_state.document_id}/index"
        )

        if response.status_code == 200:
            st.success("Document indexed successfully")
            st.json(response.json())
        else:
            st.error(response.text)


st.header("5. Search Course Material")

query = st.text_input("Ask/search something", placeholder="When are midterms?")
top_k = st.slider("Number of chunks to retrieve", min_value=1, max_value=10, value=5)

if st.button("Search"):
    if not st.session_state.course_id:
        st.error("Create a course first.")
    elif not query.strip():
        st.error("Enter a search question.")
    else:
        response = requests.post(
            f"{API_URL}/courses/{st.session_state.course_id}/search",
            json={
                "query": query,
                "top_k": top_k
            }
        )

        if response.status_code == 200:
            results = response.json()
            st.success(f"Found {len(results)} relevant chunks")

            for result in results:
                st.subheader(f"{result['filename']} — Page {result['page_number']}")
                st.write(result["text"])
                st.caption(f"Distance: {result['distance']}")
        else:
            st.error(response.text)