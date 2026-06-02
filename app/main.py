from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from uuid import uuid4

app = FastAPI(title="CourseLens AI")

class CourseCreate(BaseModel):
    name: str
    description: str | None = None

class Course(BaseModel):
    id: str
    name: str
    description: str | None = None

courses: dict[str, Course] = {}

@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.post("/courses", response_model=Course)
def create_course(course_data: CourseCreate):
    course_id = str(uuid4())

    course = Course(
        id=course_id,
        name=course_data.name,
        description=course_data.description
    )

    courses[course_id] = course
    return course

@app.get("/courses")
def get_courses():
    return list(courses.values())

@app.get("/courses/{course_id}", response_model=Course)
def get_course(course_id: str):
    if course_id not in courses:
        raise HTTPException(status_code=404, detail="Course not found")

    return courses[course_id]