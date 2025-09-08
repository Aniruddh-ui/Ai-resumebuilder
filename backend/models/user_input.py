from pydantic import BaseModel
from typing import Optional, List

class UserInput(BaseModel):
    name: str
    email: str
    phone: str
    linkedin: Optional[str] = None
    summary: Optional[str] = None
    skills: Optional[List[str]] = []
    languages: Optional[List[str]] = []
    experience: Optional[str] = None
    education: Optional[str] = None
    projects: Optional[str] = None
    certifications: Optional[str] = None
    extracurriculars: Optional[str] = None
