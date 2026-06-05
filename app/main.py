from fastapi import FastAPI, HTTPException, UploadFile, File #framework, HTTPException handles error responses

from uuid import uuid4   # generates a random unique ID for each object 
import json
from pathlib import Path  # allows creating paths easier

from app.schemas import CourseCreate, Course, Document #import CourseCreate and Course from schemas.py file

from app.pdf_utils import extract_text_by_page

app = FastAPI(title="CourseLens AI")   # name of app



# memory that maps course ID to course objects 
courses: dict[str, Course] = {}   #*Note: data resets every time server restarts 
 # memory for documents / PDFs
documents: dict[str, list[Document]] = {}

#variables that point to /raw and /processed folders
RAW_DATA_DIR = Path("data/raw")
PROCESSED_DATA_DIR = Path("data/processed")

RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)  #creates a /data/raw folder if /data doesnt exist. if it does, then continue
PROCESSED_DATA_DIR.mkdir(parents=True, exist_ok=True)

# ENDPOINTS

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
@app.get("/courses")
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


@app.get("/courses/{course_id}/documents", response_model=list[Document])
def get_documents(course_id: str):  #take course ID from URL
        if course_id not in courses:
            raise HTTPException(status_code=404, detail="Course not found")
        return documents.get(course_id, [])  # returns list of documents for specific course, if none return an empty list