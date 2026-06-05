from pydantic import BaseModel  # handles data validation ( checks right fields and types )

# schemas.py defines the exact shape (fields + types) of data going IN and OUT of the API.
# FastAPI uses these schemas as "response_model" to:
#   1. Filter the output — only fields listed in the schema are returned, nothing extra.
#   2. Validate the output — values are coerced/checked against the declared types.
#   3. Generate API docs — the /docs page shows the exact JSON format callers can expect.
#
# Usage pattern:
#   - Input schema  (e.g. CourseCreate): what the caller sends in the request body.
#   - Output schema (e.g. Course):       what the API returns — set via response_model=Course.

# Input: what the caller sends when creating a course (name is required, description is optional)
class CourseCreate(BaseModel):
    name: str
    description: str | None = None   # "None" means description can be optional 

# Output: what the API returns after a course is created — same fields plus the server-assigned ID
class Course(BaseModel):
    id: str
    name: str
    description: str | None = None