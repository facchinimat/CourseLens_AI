from fastapi import FastAPI, HTTPException, UploadFile, File
import os
from dotenv import load_dotenv
from openai import OpenAI
import chromadb
from uuid import uuid4
import json
from pathlib import Path

from app.schemas import CourseCreate, Course, Document, Chunk, SearchResult, SearchRequest, ChunkCreationResponse, AskRequest, Source, AskResponse 

from app.pdf_utils import extract_text_by_page

app = FastAPI(title="CourseLens AI")


# In-memory storage. Data resets every time the server restarts.
courses: dict[str, Course] = {}
documents: dict[str, list[Document]] = {}


# Local data folders
RAW_DATA_DIR = Path("data/raw")
PROCESSED_DATA_DIR = Path("data/processed")
CHUNKS_DATA_DIR = Path("data/chunks")
CHROMA_DATA_DIR = Path("data/chroma")

RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
PROCESSED_DATA_DIR.mkdir(parents=True, exist_ok=True)
CHUNKS_DATA_DIR.mkdir(parents=True, exist_ok=True)
CHROMA_DATA_DIR.mkdir(parents=True, exist_ok=True)


# Load environment variables from .env
load_dotenv()

if not os.getenv("OPENAI_API_KEY"):
    raise RuntimeError("OPENAI_API_KEY is missing. Add it to your .env file.")


# OpenAI client used for creating embeddings
openai_client = OpenAI()


# Chroma vector database setup
chroma_client = chromadb.PersistentClient(path=str(CHROMA_DATA_DIR))

chunks_collection = chroma_client.get_or_create_collection(
    name="courselens_chunks"
)


# OpenAI embedding model used to turn chunk text into vectors
EMBEDDING_MODEL = "text-embedding-3-small"

# ENDPOINTS

@app.get("/")
def root():
    return {"message": "Welcome to CourseLens AI"}

# check if server is running
@app.get("/health")
def health_check():
    return {"status": "ok"}

# allow user or admin to add a new course 
@app.post("/courses", response_model=Course)
def create_course(course_data: CourseCreate):
    course_id = str(uuid4())         # generate a unique ID

    course = Course(          #build the full course
        id=course_id,
        name=course_data.name,
        description=course_data.description
    )

    courses[course_id] = course   #save the course in memory ( local )
    return course           # return the new course ( with ID )

# retrieves all courses currently stored
@app.get("/courses", response_model = list[Course])
def get_courses():
    return list(courses.values())   # get all course objects from the dictionary ( converts into JSON array )

# fetches single course by its ID
@app.get("/courses/{course_id}", response_model=Course)
def get_course(course_id: str):
    if course_id not in courses:
        raise HTTPException(status_code=404, detail="Course not found")

    return courses[course_id]

@app.post("/courses/{course_id}/documents", response_model=Document)
async def upload_document(course_id: str, file: UploadFile = File(...)):
        if course_id not in courses:
            raise HTTPException(status_code=404, detail="Course not found")
        if not file.filename.endswith(".pdf"):   #checks if file is PDF format
            raise HTTPException(status_code=400, detail="Only PDF files are allowed")    #rejects non PDF uploads
        doc_id = str(uuid4()) # generate a unique ID for this document

        file_path = RAW_DATA_DIR / f"{doc_id}_{file.filename}" #builds a path for the raw PDF to be saved ( prevents overwriting )

        #reads all bytes from the uploaded file and saves PDF into raw folder
        contents = await file.read()
        with open(file_path, "wb") as f:
            f.write(contents)

        pages = extract_text_by_page(file_path)


        processed_data = {
             "document_id": doc_id,
             "course_id": course_id,
             "filename": file.filename,
             "page_count":len(pages),
             "pages": pages
        }

        processed_file_path = PROCESSED_DATA_DIR / f"{doc_id}.json"

        with open(processed_file_path, "w", encoding = "utf-8") as f:
             json.dump(processed_data,f, indent = 4, ensure_ascii = False)  #add python dict ( document content ) into a JSON file for later chunking - function

        # builds the Document object using schema
        document = Document(
        id = doc_id,
        course_id = course_id,
        filename = file.filename,
        page_count = len(pages),    #counts the pages
        message = "PDF uploaded and text extracted successfully"
        )

        #documents is a dict that maps each course id to a list of its documents. If course doesnt have any uploads yet, initialize its list first then append.
        if course_id not in documents:
            documents[course_id] = []
        documents[course_id].append(document)
        return document   # return document as the response

#retrievies documents uploaded using course ID
@app.get("/courses/{course_id}/documents", response_model=list[Document])
def get_documents(course_id: str):  #take course ID from URL
        if course_id not in courses:
            raise HTTPException(status_code=404, detail="Course not found")
        return documents.get(course_id, [])  # returns list of documents for specific course, if none return an empty list


#Creates a POST endpoint that generates chunks for a specific document inside a specific course
@app.post("/courses/{course_id}/documents/{document_id}/chunks",  response_model=ChunkCreationResponse)
def create_document_chunks(course_id: str, document_id: str):   # FastAPI gets course_id and document_id from the URL as strings
    if course_id not in courses:
        raise HTTPException(status_code=404, detail="Course not found")  #checks if course ID is in dictionary of courses

    # extract documents from a course ( in list ), if none return empty list ( prevents errors )
    course_documents = documents.get(course_id, [])
    document_exists = any(doc.id == document_id for doc in course_documents) # Check whether any document in this course has the matching document_id

    if not document_exists:
        raise HTTPException(status_code=404, detail="Document not found for this course")  #if document doesnt exist raise and error

    chunks = create_chunks_from_processed_file(document_id)  # Load the processed JSON file for this document, split each page's text into chunks, and return a list of Chunk objects

    if not chunks:
        raise HTTPException(status_code=400, detail="No chunks could be created from this document")   #if chunks list empty, then raise an error

    if chunks[0].course_id != course_id:
        raise HTTPException(status_code=400, detail="Document does not belong to this course") #extra safety measure to make sure the chunks were created from a document belonging to this course

    #creates a path to store chunks data, file is JSON format using document ID
    chunks_file_path = CHUNKS_DATA_DIR / f"{document_id}_chunks.json"

    #creates a chunks data dictionary. includes chunks and metadata
    chunks_data = {
        "document_id": document_id,              #metadata
        "course_id": course_id,                  #metadata
        "filename": chunks[0].filename,          #metadata
        "chunk_count": len(chunks),              #metadata
        "chunks": [chunk.model_dump() for chunk in chunks]  #Convert each Chunk Pydantic object into a normal Python dictionary so it can be saved into JSON.
        #Create a list of dictionaries, where each dictionary is one chunk.
    }

    #Save the chunks_data Python dictionary into a JSON file inside data/chunks/
    with open(chunks_file_path, "w", encoding="utf-8") as f:
        json.dump(chunks_data, f, indent=4, ensure_ascii=False)

    #return response to API for user to see. matches schemas.py 
    return {
        "document_id": document_id,
        "course_id": course_id,
        "filename": chunks[0].filename,
        "chunk_count": len(chunks),
        "message": "Chunks created successfully"
    }

#creates a endpoint for user to access chunks from PDF
@app.get("/courses/{course_id}/documents/{document_id}/chunks", response_model=list[Chunk])
def get_document_chunks(course_id: str, document_id: str): #API uses course id and document ID from URL as input

    #checks if course is in courses dictionary
    if course_id not in courses:
        raise HTTPException(status_code=404, detail="Course not found")

    #creates a file path to chunks folder for data, file is JSON 
    chunks_file_path = CHUNKS_DATA_DIR / f"{document_id}_chunks.json"

    if not chunks_file_path.exists():
        raise HTTPException(status_code=404, detail="Chunks not found for this document")  #checks if specific chunks JSON file exists in folder

    with open(chunks_file_path, "r", encoding="utf-8") as f:
        chunks_data = json.load(f)   #open JSON file chunks and load it into a python dictionary

    if chunks_data["course_id"] != course_id:
        raise HTTPException(status_code=400, detail="Document does not belong to this course")

    return chunks_data["chunks"]   #return the list of chunks from PDF file as python dictionary. ( FastAPI checks that each chunk matches Chunk schema )

# function helper to chunk large text
def chunk_text(text: str, chunk_size: int = 800, overlap: int = 100) -> list[str]:    # text is the extracted text from one page. chunk_size = maximum number of characters per chunk, needed to make sure context is preserved. Returns a list of text chunks 

    #checks that we can advance each text properly and no errors
    if overlap >= chunk_size:
        raise ValueError("overlap must be smaller than chunk_size")

    #creates a chunks list to save all chunks from a text
    chunks = []

    #if there is not text, return empty chunks list
    if not text:
        return chunks

    #start of page, first letter. Index of first character in page starts at 0
    start = 0

    #continue chunking the text while there is text
    while start < len(text):
        end = start + chunk_size   #end = upper limit, start = lower limit for text chunk ( overlap of 100 characters )

        chunk = text[start:end].strip()  #removes extra space and newlines ( only beginning and end of text )

        #if the chunk is not empty, then append chunk to chunks list
        if chunk:
            chunks.append(chunk)

        start += chunk_size - overlap  #increment to next characters in page 

    return chunks   # return list of chunks for this page


#function to create chunks from a processed JSON PDF file.
#input is document ID. Returns a list of chunks from a PDF file
def create_chunks_from_processed_file(document_id: str) -> list[Chunk]:

    #creates file path to processed data folder to get specific document JSON file
    processed_file_path = PROCESSED_DATA_DIR / f"{document_id}.json"


    #if the file doesnt exist raise an error
    if not processed_file_path.exists():
        raise HTTPException(status_code=404, detail="Processed document file not found")

    #open the processed JSON file and load it into python dictionary 
    with open(processed_file_path, "r", encoding="utf-8") as f:
        processed_data = json.load(f)

    #extract course ID, filename and text ( pages ) from processed JSON dictionary
    course_id = processed_data["course_id"]
    filename = processed_data["filename"]
    pages = processed_data["pages"]

    #creates a chunks list to save all chunks from PDF
    all_chunks = []

    #iterates through each page in pages dictionary file
    for page in pages:

        page_number = page["page_number"]   #save page number from specific file page
        page_text = page["text"] #save all text from page

        #split this page's text into smaller text chunks
        text_chunks = chunk_text(page_text)

        #Loop through each text chunk from this page and give it an index
        for chunk_index, chunk in enumerate(text_chunks):

            #generates a unique id for one chunk in a page
            chunk_id = f"{document_id}_p{page_number}_c{chunk_index}"

            #creates one chunk object that contains text chunk and metadata. Matches chunk schemas. Contains unique chunk ID for Chroma DB
            chunk_obj = Chunk(
                chunk_id=chunk_id,
                course_id=course_id,
                document_id=document_id,
                filename=filename,
                page_number=page_number,
                chunk_index=chunk_index,
                text=chunk
            )

            all_chunks.append(chunk_obj)  #append chunk to chunks list

    return all_chunks     #return all chunks from a processed JSON file


#Sematic Search for documents 


@app.post("/courses/{course_id}/documents/{document_id}/index")
def index_document_chunks(course_id: str, document_id: str):
    # Check if the course exists in memory
    if course_id not in courses:
        raise HTTPException(status_code=404, detail="Course not found")

    # Get all documents for this course
    course_documents = documents.get(course_id, [])

    # Check if this document belongs to this course
    document_exists = any(doc.id == document_id for doc in course_documents)

    if not document_exists:
        raise HTTPException(status_code=404, detail="Document not found for this course")

    # Build the path to the chunks JSON file
    chunks_file_path = CHUNKS_DATA_DIR / f"{document_id}_chunks.json"

    # Make sure chunks were already created
    if not chunks_file_path.exists():
        raise HTTPException(
            status_code=404,
            detail="Chunks file not found. Create chunks before indexing."
        )

    # Load chunks JSON file into a Python dictionary
    with open(chunks_file_path, "r", encoding="utf-8") as f:
        chunks_data = json.load(f)

    # Safety check: make sure this chunks file belongs to the course in the URL
    if chunks_data["course_id"] != course_id:
        raise HTTPException(status_code=400, detail="Chunks do not belong to this course")

    # Get the list of chunk dictionaries
    chunks = chunks_data["chunks"]

    if not chunks:
        raise HTTPException(status_code=400, detail="No chunks found to index")

    # Extract only the text from each chunk
    texts = [chunk["text"] for chunk in chunks]

    # Create embeddings for every chunk text
    embeddings = create_embeddings(texts)

    # Create list of unique IDs for Chroma
    ids = [chunk["chunk_id"] for chunk in chunks]

    # Create metadata for each chunk
    metadatas = [
        {
            "course_id": chunk["course_id"],
            "document_id": chunk["document_id"],
            "filename": chunk["filename"],
            "page_number": chunk["page_number"],
            "chunk_index": chunk["chunk_index"]
        }
        for chunk in chunks
    ]

    # Store everything in Chroma
    chunks_collection.upsert(
        ids=ids,
        embeddings=embeddings,
        documents=texts,
        metadatas=metadatas
    )

    return {
        "course_id": course_id,
        "document_id": document_id,
        "indexed_count": len(chunks),
        "message": "Chunks indexed successfully"
    }


@app.post("/courses/{course_id}/search", response_model=list[SearchResult])
def search_course_chunks(course_id: str, search_request: SearchRequest):
    return retrieve_course_chunks(
        course_id=course_id,
        query=search_request.query,
        top_k=search_request.top_k
    )


#sends text chunks to openai to return vectors of text 
def create_embeddings(texts: list[str]) -> list[list[float]]: #takes texts ( list of strings ). And function returns a list of lists of floats. each page could have more than 1 text chunk, so it has to return a list of list of floats to represents vectors of each text chunk in each page. 

    #checks if texts is empty 
    if not texts:
        return []
    
    #sends list of text chunks to openai embedding model
    response = openai_client.embeddings.create(  #openai_client is how python code communicates with OpenAI
        model = EMBEDDING_MODEL,
        input = texts
    )

    embeddings = []

    # takes each chunk vector and appends it to embedding list
    for item in response.data:
        embeddings.append(item.embedding)

    return embeddings


# retrieves most relevant chunks for user's question
def retrieve_course_chunks(course_id: str, query: str, top_k: int = 5) -> list[SearchResult]:
    # Check if the course exists in memory
    if course_id not in courses:
        raise HTTPException(status_code=404, detail="Course not found")

    # Clean the user's query
    question = query.strip()

    # Make sure the query is not empty
    if not question:
        raise HTTPException(status_code=400, detail="Search query cannot be empty")

    # Limit results to 1 - 10 only
    top_k = max(1, min(top_k, 10))

    # convert the user's question into an embedding vector
    query_embedding = create_embeddings([question])[0]

    # Search Chroma for the most similar chunks in this course
    results = chunks_collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
        where={"course_id": course_id},
        include=["documents", "metadatas", "distances"]
    )

    # Chroma returns nested lists because it supports multiple queries at once.
    # Since we only searched one query, we use index [0].
    ids = results["ids"][0]
    documents_found = results["documents"][0]
    metadatas = results["metadatas"][0]
    distances = results["distances"][0]

    search_results = []

    for i, chunk_id in enumerate(ids):
        metadata = metadatas[i]

        search_result = SearchResult(
            chunk_id=chunk_id,
            document_id=metadata["document_id"],
            filename=metadata["filename"],
            page_number=metadata["page_number"],
            chunk_index=metadata["chunk_index"],
            text=documents_found[i],
            distance=distances[i]
        )

        search_results.append(search_result)

    return search_results

#convert retrieved chunks into a clean text context for LLM
#The LLM receives readable source text, not embedding vectors
#Each chunk includes filename and page number so the model can answer with source awareness
def format_chunks_prompt(chunks: list[SearchResult]) -> str:
    context = []

    for i, chunk in enumerate(chunks, start = 1):
        context.append(
            f"source {i}:\n"
            f"filename: {chunk.filename}\n"
            f"page: {chunk.page_number}\n"
            f"text: {chunk.text}\n"
        )
    
    return "\n\n".join(context)

# OpenAI model used to generate final answers from retrieved context
ANSWER_MODEL = "gpt-4.1-mini"

#Generate a final answer using the user's question and retrieved source chunks
#The prompt tells the model to only use the provided sources. This reduces hallucinations (generation part of RAG ). Sends users question and sources for answer
def generate_answer(question: str, context: str) -> str:
    response = openai_client.responses.create(
        model = ANSWER_MODEL,
        input = f"""
You are CourseLens AI, a course document assistant.

Answer the student's question using only the provided sources.
Do not use outside knowledge.
If the sources do not contain enough information, say:
"The uploaded documents do not provide enough information to answer this."

When possible, mention the filename and page number from the sources.

Question:
{question}

Sources:
{context}
"""

    )

    return response.output_text  #reposnse has metadata and text, only return LLM text 


# Creates the main RAG question-answering endpoint for a specific course.
# This endpoint retrieves relevant document chunks, generates an answer, and returns source metadata.
@app.post("/courses/{course_id}/ask", response_model = AskResponse)
def ask_course_question(course_id: str, ask_request: AskRequest):
    # Retrieve the most relevant chunks from Chroma based on the user's question.
    # The course_id filters the search to documents belonging to the selected course.
    retrieved_chunks = retrieve_course_chunks(
        course_id = course_id,
        query = ask_request.question,
        top_k = ask_request.top_k
        
    )

    # If no relevant chunks are found, stop the request and return a clear error response.
    if not retrieved_chunks:
        raise HTTPException(status_code = 404, detail = "No relevant chunks found")
    
    # Convert the retrieved chunks into a formatted text context for the LLM.
    # This context includes source text, filenames, and page numbers.
    context = format_chunks_prompt(retrieved_chunks)

    # Generate a final answer using the user's question and the retrieved document context.
    answer = generate_answer(
        question = ask_request.question,
        context = context
    )

    # Build a list of source metadata from the retrieved chunks.
    # These sources show where the answer came from without returning full chunk text again.
    sources = [
        Source(
            chunk_id = chunk.chunk_id,
            document_id= chunk.document_id,
            filename = chunk.filename,
            page_number = chunk.page_number,
            chunk_index = chunk.chunk_index
        )
        for chunk in retrieved_chunks
    ]

    # Return the generated answer along with the source metadata.
    return AskResponse(
        answer = answer,
        sources = sources
    )
