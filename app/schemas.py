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

# what the API returns when a PDF is uploaded and requested
class Document(BaseModel):
    id: str
    course_id: str
    filename: str
    page_count: int
    message: str    #extract text, one string per page

#definition on how chunck should look like / represent for objects
class Chunk(BaseModel):
    chunk_id: str
    course_id: str
    document_id:str
    filename: str
    page_number: int
    chunk_index: int
    text: str

#response model for API when chunks for PDF are created
class ChunkCreationResponse(BaseModel):
    document_id: str
    course_id: str
    filename: str
    chunk_count: int
    message: str

#What the user sends 
class SearchRequest(BaseModel):
    query: str
    top_k: int = 5

#what the API returns 
class SearchResult(BaseModel):
    chunk_id: str
    document_id: str
    filename: str
    page_number: int
    chunk_index: int
    text: str
    distance: float | None = None  #helps with debugging for relevance. Lower distance = more similar ( based on Chroma metrics )

#query 
class AskRequest(BaseModel):
    question: str
    top_k: int = 5

#citations for response
class Source(BaseModel):
    chunk_id: str
    document_id: str
    filename: str
    page_number: int
    chunk_index: int

#LLM answer 
class AskResponse(BaseModel):
    answer: str
    sources: list[Source]