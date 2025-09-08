from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from models.user_input import UserInput
from services.llm_service import generate_resume_text
from services.pdf_service import save_resume_pdf
from services.docx_service import save_resume_docx
from pathlib import Path
import traceback
import logging

app = FastAPI()

logger = logging.getLogger("uvicorn.error")

# Allow frontend requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Frontend directory
frontend_dir = Path(__file__).resolve().parent / "frontend"
if not frontend_dir.exists():
    frontend_dir.mkdir(parents=True, exist_ok=True)

# Serve frontend static assets
app.mount("/static", StaticFiles(directory=str(frontend_dir), html=True), name="frontend")

@app.get("/")
async def root():
    index_file = frontend_dir / "index.html"
    return FileResponse(str(index_file))

@app.post("/generate")
async def generate_resume(data: UserInput):
    """
    Generate a professional resume using LLaMA.
    Returns resume text, user description, and download links.
    """
    try:
        # Call LLM service
        result = await generate_resume_text(data)
        resume_text = result["resume_text"]
        user_description = result["user_description"]

        structured_data = {
            "name": data.name,
            "email": data.email,
            "phone": data.phone,
            "linkedin": data.linkedin,
            "summary": data.summary,
            "skills": data.skills,
            "languages": getattr(data, "languages", None),
            "experience": data.experience,
            "education": data.education,
            "projects": data.projects,
            "certifications": data.certifications,
            "extracurriculars": getattr(data, "extracurriculars", None),
            "generated_text": resume_text,
        }

        # Save resume files
        pdf_path = save_resume_pdf(structured_data)
        docx_path = save_resume_docx(structured_data)

        return JSONResponse({
            "resume_text": resume_text,
            "user_description": user_description,
            "pdf_file": "/download/pdf",
            "docx_file": "/download/docx"
        })

    except Exception as e:
        tb = traceback.format_exc()
        logger.error("Error in /generate: %s", tb)
        return JSONResponse({"error": "Failed to generate resume", "detail": str(e), "trace": tb}, status_code=500)

@app.get("/download/pdf")
async def download_pdf():
    pdf_path = Path(__file__).resolve().parent / "resume.pdf"
    if not pdf_path.exists():
        raise HTTPException(status_code=404, detail="PDF not found. Generate a resume first.")
    return FileResponse(str(pdf_path), media_type="application/pdf", filename="resume.pdf")

@app.get("/download/docx")
async def download_docx():
    docx_path = Path(__file__).resolve().parent / "resume.docx"
    if not docx_path.exists():
        raise HTTPException(status_code=404, detail="DOCX not found. Generate a resume first.")
    return FileResponse(
        str(docx_path),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename="resume.docx"
    )
