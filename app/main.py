from fastapi import FastAPI, HTTPException #framework, HTTPException handles error responses

from uuid import uuid4   # generates a random unique ID for each course 

from app.schemas import CourseCreate, Course #import CourseCreate and Course from schemas.py file

app = FastAPI(title="CourseLens AI")   # name of app



# memory that maps course ID to course objects 
courses: dict[str, Course] = {}   #*Note: data resets every time server restarts 

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