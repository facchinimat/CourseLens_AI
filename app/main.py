from fastapi import FastAPI, HTTPException #framework, HTTPException handles error responses

from pydantic import BaseModel  #handles data validation ( checks right fields and types )

from uuid import uuid4   # generates a random unique ID for each course 

app = FastAPI(title="CourseStudy AI")   # name of app


# creates a course ( name is required and description is optional) - user sends
class CourseCreate(BaseModel):
    name: str
    description: str | None = None   # "None" means description can be optional 


# API returns after a course is created. Same as CourseCreate but with ID field 
class Course(BaseModel):
    id: str
    name: str
    description: str | None = None

# memory that maps course ID to course obejects 
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

# retrivies all courses currently stored
@app.get("/courses")
def get_courses():
    return list(courses.values())   # get all course objects from the dictionary ( converts into JSON array )

# fetches single course by its ID
@app.get("/courses/{course_id}", response_model=Course)
def get_course(course_id: str):
    if course_id not in courses:
        raise HTTPException(status_code=404, detail="Course not found")

    return courses[course_id]