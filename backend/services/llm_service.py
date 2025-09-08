import os
from dotenv import load_dotenv
import httpx
import re
import difflib
import textwrap
import asyncio
import random
from models.user_input import UserInput

load_dotenv()
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"


def _clean_resume_text(text: str) -> str:
    text = re.sub(r"\*+|_+|`+|~+", "", text)
    text = re.sub(r"^[\s]*[•\*\-\u2022]+[\s]*", "- ", text, flags=re.M)
    text = re.sub(r"-{2,}", "-", text)
    text = re.sub(r"(?m)^[\s\-_=~`#]{1,}$", "", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"(?m)^[ \t]*([A-Za-z ]{3,}:?)\s*$",
                  lambda m: m.group(1).strip().upper() + "\n", text)
    text = text.strip()
    text = re.sub(r"(?m)([A-Z ]{3,})\n(- )",
                  lambda m: m.group(1) + "\n\n" + m.group(2), text)
    return text


def _local_fallback_text(data: UserInput) -> str:
    parts = []
    if data.name:
        parts.append(data.name.upper())
    contact = []
    if data.email: contact.append(data.email)
    if data.phone: contact.append(data.phone)
    if data.linkedin: contact.append(data.linkedin)
    if contact:
        parts.append(" | ".join(contact))

    def add_section(title, content, as_bullets=False):
        if not content:
            return
        parts.append(title)
        if isinstance(content, (list, tuple)):
            for item in content:
                parts.append(f"- {item}" if as_bullets else item)
        else:
            text = str(content).strip()
            if as_bullets:
                lines = [l.strip() for l in re.split(r"\n|\.|;", text) if l.strip()]
                for l in lines:
                    parts.append(f"- {l}")
            else:
                wrapped = textwrap.fill(text, width=90)
                parts.extend([l for l in wrapped.splitlines() if l.strip()])

    add_section("PROFESSIONAL SUMMARY", data.summary)
    add_section("SKILLS", data.skills, as_bullets=True)
    add_section("LANGUAGES", getattr(data, "languages", None), as_bullets=True)
    add_section("WORK EXPERIENCE", data.experience, as_bullets=True)
    add_section("PROJECTS", data.projects, as_bullets=True)
    add_section("EDUCATION", data.education)
    add_section("CERTIFICATIONS", data.certifications)
    add_section("EXTRACURRICULARS", getattr(data, "extracurriculars", None), as_bullets=True)
    return "\n\n".join(parts)


async def generate_resume_text(data: UserInput) -> dict:
    if not OPENROUTER_API_KEY:
        raise RuntimeError("OPENROUTER_API_KEY is not set. Please add it to your .env file.")

    details = []
    if data.name: details.append(f"Name: {data.name}")
    if data.email: details.append(f"Email: {data.email}")
    if data.phone: details.append(f"Phone: {data.phone}")
    if data.linkedin: details.append(f"LinkedIn: {data.linkedin}")
    if data.education: details.append(f"Education:\n{data.education}")
    if data.certifications: details.append(f"Certifications:\n{data.certifications}")

    enhance_details = []
    if data.summary: enhance_details.append(f"Professional Summary:\n{data.summary}")
    if data.experience: enhance_details.append(f"Work Experience:\n{data.experience}")
    if data.projects: enhance_details.append(f"Projects:\n{data.projects}")

    prompt = f"""
You are an expert professional resume writer. 
Generate a clean, ATS-friendly professional resume in plain text.

Enhance and refine ONLY these sections:
- Professional Summary
- Work Experience
- Projects

Do NOT rewrite personal details (name, email, phone, LinkedIn, education, certifications).
Keep them exactly as given.

Rules:
- OUTPUT ONLY PLAIN TEXT.
- Use ALL CAPS for section headings.
- Use '-' for bullet points.
- Keep sentences concise and professional.

User details:
{chr(10).join(details)}

Sections to enhance:
{chr(10).join(enhance_details)}

Produce the resume now as plain text.
At the end, add this line exactly once:
SHORT USER DESCRIPTION: <2–3 sentence summary of the person>
"""

    headers = {"Authorization": f"Bearer {OPENROUTER_API_KEY}", "Content-Type": "application/json"}
    payload = {"model": "meta-llama/llama-3.1-8b-instruct",
               "messages": [{"role": "system", "content": "You are an expert resume writer who outputs plain text only."},
                            {"role": "user", "content": prompt}],
               "max_tokens": 1600, "temperature": 0.2}

    max_attempts = 3
    async with httpx.AsyncClient(timeout=httpx.Timeout(60.0, connect=15.0)) as client:
        for attempt in range(max_attempts):
            try:
                resp = await client.post(OPENROUTER_URL, headers=headers, json=payload)
                if resp.status_code in (408, 429) or 500 <= resp.status_code < 600:
                    await asyncio.sleep(1 * (2 ** attempt) + random.random())
                    continue
                resp.raise_for_status()
                result = resp.json()
                output_text = result["choices"][0]["message"]["content"].strip()

                if "SHORT USER DESCRIPTION:" in output_text:
                    resume_text, user_desc = output_text.split("SHORT USER DESCRIPTION:", 1)
                    return {"resume_text": _clean_resume_text(resume_text.strip()), "user_description": user_desc.strip()}
                else:
                    return {"resume_text": _clean_resume_text(output_text),
                            "user_description": f"{data.name} is skilled in {', '.join(data.skills or [])}."}
            except Exception:
                continue

    fb_resume = _clean_resume_text(_local_fallback_text(data))
    fb_desc = f"{data.name} is skilled in {', '.join(data.skills or [])}."
    return {"resume_text": fb_resume, "user_description": fb_desc}
