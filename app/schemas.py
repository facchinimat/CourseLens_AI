from pydantic import BaseModel  # handles data validation ( checks right fields and types )

# creates a course ( name is required and description is optional) - user sends
class CourseCreate(BaseModel):
    name: str
    description: str | None = None   # "None" means description can be optional 

# API returns after a course is created. Same as CourseCreate but with ID field 
class Course(BaseModel):
    id: str
    name: str
    description: str | None = None

# what the API returns when a PDF is uploaded
class Document(BaseModel):
    id: str
    course_id: str
    filename: str
    page_count: int
    message: list[str]    #extract text, one string per page