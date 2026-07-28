import uuid 
from pydantic import BaseModel 

class Contact(BaseModel):
    id: uuid.UUID
    name: str
    ip: str

