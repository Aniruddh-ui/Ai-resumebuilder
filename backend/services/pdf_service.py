from reportlab.lib.pagesizes import A4
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from reportlab.lib import colors
from pathlib import Path
from typing import Union, Dict, List
import re

BASE_DIR = Path(__file__).resolve().parent.parent
PDF_FILE = str(BASE_DIR / "resume.pdf")


def _parse_text_sections(text: str) -> Dict[str, List[str]]:
    if not text:
        return {}

    lines = [line.rstrip() for line in text.splitlines()]
    sections: Dict[str, List[str]] = {}
    current = None
    heading_map = {
        "PROFESSIONAL SUMMARY": "summary",
        "SUMMARY": "summary",
        "WORK EXPERIENCE": "experience",
        "EXPERIENCE": "experience",
        "EDUCATION": "education",
        "PROJECTS": "projects",
        "CERTIFICATIONS": "certifications",
        "SKILLS": "skills",
        "LANGUAGES": "languages",
        "LANGUAGES KNOWN": "languages",
        "EXTRACURRICULARS": "extracurriculars",
        "EXTRACURRICULAR ACTIVITIES": "extracurriculars",
        "CONTACT": "contact",
        "CONTACT INFORMATION": "contact",
    }

    for line in lines:
        line_stripped = line.strip()
        if not line_stripped:
            if current:
                sections.setdefault(current, []).append("")
            continue

        if (
            re.match(r"^[A-Z0-9 \-]{2,80}$", line_stripped)
            and line_stripped.upper() == line_stripped
        ):
            key = heading_map.get(line_stripped.rstrip(":"))
            if key:
                current = key
                sections.setdefault(current, [])
                continue

        # If no current section, start with summary
        if not current:
            current = "summary"
            sections.setdefault(current, [])

        sections.setdefault(current, []).append(line_stripped)

    # Compact skills and languages into list if comma separated or newline separated
    for key in ("skills", "languages"):
        if key in sections:
            joined = " ".join(sections[key])
            if "," in joined or "\n" in joined:
                parts = re.split(r"[,|\n]", joined)
                sections[key] = [part.strip() for part in parts if part.strip()]
            else:
                sections[key] = [joined]

    # Trim leading/trailing empty lines inside sections
    for sec in sections:
        if isinstance(sections[sec], list):
            while sections[sec] and not sections[sec][0].strip():
                sections[sec].pop(0)
            while sections[sec] and not sections[sec][-1].strip():
                sections[sec].pop()
    return sections


PAGE_WIDTH, PAGE_HEIGHT = A4
LEFT_MARGIN = RIGHT_MARGIN = 40
TOP_MARGIN = BOTTOM_MARGIN = 30
CONTENT_WIDTH = PAGE_WIDTH - LEFT_MARGIN - RIGHT_MARGIN

styles = getSampleStyleSheet()
try:
    styles.add(
        ParagraphStyle(
            name="Name", fontSize=22, leading=26, alignment=TA_CENTER, spaceAfter=8
        )
    )
except:
    pass
try:
    styles.add(
        ParagraphStyle(
            name="Contact",
            fontSize=9,
            leading=11,
            alignment=TA_CENTER,
            textColor=colors.blue,
            underline=True,
            spaceAfter=0,
        )
    )
except:
    pass
try:
    styles.add(
        ParagraphStyle(
            name="SectionTitle",
            fontSize=11,
            leading=13,
            alignment=TA_LEFT,
            spaceAfter=6,
            fontName="Helvetica-Bold",
            textColor=colors.HexColor("#111111"),
        )
    )
except:
    pass
try:
    styles.add(
        ParagraphStyle(
            name="Body",
            fontSize=10,
            leading=16,
            alignment=TA_LEFT,
            spaceAfter=6,
        )
    )
except:
    pass
try:
    styles.add(
        ParagraphStyle(
            name="IndentedBody",
            fontSize=10,
            leading=16,
            alignment=TA_LEFT,
            leftIndent=12,
            spaceAfter=6,
        )
    )
except:
    pass


def _p(text: str, style="Body"):
    if not text:
        return Paragraph("", styles[style])
    clean_text = re.sub(r"\n{2,}", "\n", str(text).strip())
    return Paragraph(clean_text, styles[style])


def _boxed_section(title: str, flowables: List, box_width: float = CONTENT_WIDTH):
    elems = []
    if title:
        elems.append(Paragraph(title.upper(), styles["SectionTitle"]))
    elems.extend(flowables)
    rows = [[e] for e in elems]
    tbl = Table(rows, colWidths=[box_width])
    tbl.setStyle(
        TableStyle(
            [
                ("BOX", (0, 0), (-1, -1), 0.7, colors.HexColor("#333333")),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    return tbl


def _contact_link(url: str, display_text: str):
    # Using HTML-like link with blue underlined text
    return f'<link href="{url}"><u><font color="#1155cc">{display_text}</font></u></link>'


def save_resume_pdf(resume: Union[str, Dict], filename: str = PDF_FILE) -> str:
    out_path = Path(filename)
    out_path.parent.mkdir(exist_ok=True, parents=True)

    if isinstance(resume, dict):
        try:
            gen = resume.get("generated_text")
            if gen and isinstance(gen, str) and gen.strip():
                clean_gen = gen
                clean_gen = re.sub(
                    r"^HERE IS THE ENHANCED RESUME IN PLAIN TEXT FORMAT:\s*",
                    "",
                    clean_gen,
                    flags=re.I,
                )
                clean_gen = re.sub(
                    r"^PROFESSIONAL RESUME\n*", "", clean_gen, flags=re.I
                )
                parsed = _parse_text_sections(clean_gen)
                if parsed:
                    if parsed.get("summary"):
                        summary_text = "\n".join(parsed["summary"])
                        # Remove contact duplicates
                        summary_text = re.sub(
                            r"[^\.]*@[^\.]*|https?://\S+|\b\d{7,}\b", "", summary_text
                        )
                        summary_text = re.sub(r"\s{2,}", " ", summary_text).strip()
                        resume["summary"] = summary_text
                    if parsed.get("skills"):
                        resume["skills"] = parsed["skills"]
                    if parsed.get("languages"):
                        resume["languages"] = parsed["languages"]
                    for sec in [
                        "experience",
                        "projects",
                        "education",
                        "certifications",
                        "extracurriculars",
                    ]:
                        if parsed.get(sec):
                            resume[sec] = "\n".join(parsed[sec])
        except Exception:
            pass

        doc = SimpleDocTemplate(
            str(out_path),
            pagesize=A4,
            leftMargin=LEFT_MARGIN,
            rightMargin=RIGHT_MARGIN,
            topMargin=TOP_MARGIN,
            bottomMargin=BOTTOM_MARGIN,
        )
        story: List = []

        # Name
        if resume.get("name"):
            story.append(Paragraph(resume["name"], styles["Name"]))

        # Contact info line, center aligned with "|" separator and clickable links
        contact_items = []
        if resume.get("phone"):
            contact_items.append(
                _contact_link(f"tel:{resume['phone']}", resume["phone"])
            )
        if resume.get("email"):
            contact_items.append(
                _contact_link(f"mailto:{resume['email']}", resume["email"])
            )
        if resume.get("linkedin"):
            link = resume["linkedin"]
            if not link.lower().startswith("http"):
                link = "https://" + link
            contact_items.append(_contact_link(link, link))
        if contact_items:
            contact_line = " | ".join(contact_items)
            story.append(Paragraph(contact_line, styles["Contact"]))

        # Divider line and space
        hr_table = Table([[""]], colWidths=[CONTENT_WIDTH])
        hr_table.setStyle(
            TableStyle(
                [("LINEBELOW", (0, 0), (-1, -1), 1.0, colors.HexColor("#222222"))]
            )
        )
        story.append(hr_table)
        story.append(Spacer(1, 10))

        # Professional Summary
        if resume.get("summary"):
            story.append(_boxed_section("Professional Summary", [_p(resume["summary"])]))
            story.append(Spacer(1, 8))

        # Education (split if commas/newlines)
        if resume.get("education"):
            edu_parts = re.split(r"[,\n]", resume["education"], maxsplit=1)
            edu_flowables = []
            if len(edu_parts) == 2:
                edu_flowables.append(Paragraph(edu_parts[0].strip(), styles["Body"]))
                edu_flowables.append(Paragraph(edu_parts[1].strip(), styles["Body"]))
            else:
                edu_flowables.append(Paragraph(resume["education"].strip(), styles["Body"]))
            story.append(_boxed_section("Education", edu_flowables))
            story.append(Spacer(1, 8))

        # Technical Skills
        if resume.get("skills"):
            skills_text = (
                ", ".join(resume["skills"])
                if isinstance(resume["skills"], (list, tuple))
                else str(resume["skills"])
            )
            story.append(_boxed_section("Technical Skills", [_p(skills_text)]))
            story.append(Spacer(1, 8))

        # Languages
        if resume.get("languages"):
            lang_text = (
                ", ".join(resume["languages"])
                if isinstance(resume["languages"], (list, tuple))
                else str(resume["languages"])
            )
            story.append(_boxed_section("Languages Known", [_p(lang_text)]))
            story.append(Spacer(1, 8))

        # Experience (role and company together)
        if resume.get("experience"):
            lines = resume["experience"].split("\n")
            exp_flowables = []
            if lines:
                # Assume first line has both role and company, put it together as title
                first_line = lines[0].strip()
                exp_flowables.append(
                    Paragraph(
                        first_line,
                        ParagraphStyle(
                            "TitleBold",
                            parent=styles["Body"],
                            fontName="Helvetica-Bold",
                            spaceAfter=4,
                        ),
                    )
                )
                for line in lines[1:]:
                    clean_line = line.strip()
                    if clean_line:
                        exp_flowables.append(Paragraph(clean_line, styles["IndentedBody"]))
            story.append(_boxed_section("Work Experience", exp_flowables))
            story.append(Spacer(1, 8))

        # Projects (similar formatting)
        if resume.get("projects"):
            lines = resume["projects"].split("\n")
            proj_flowables = []
            if lines:
                first_line = lines[0].strip()
                proj_flowables.append(
                    Paragraph(
                        first_line,
                        ParagraphStyle(
                            "TitleBold",
                            parent=styles["Body"],
                            fontName="Helvetica-Bold",
                            spaceAfter=4,
                        ),
                    )
                )
                for line in lines[1:]:
                    clean_line = line.strip()
                    if clean_line:
                        proj_flowables.append(Paragraph(clean_line, styles["IndentedBody"]))
            story.append(_boxed_section("Projects", proj_flowables))
            story.append(Spacer(1, 8))

        # Certifications - multiple bullet points
        if resume.get("certifications"):
            certs = re.split(r"[,;\n]+", resume["certifications"])
            cert_flowables = [
                Paragraph(f"• {cert.strip()}", styles["Body"]) for cert in certs if cert.strip()
            ]
            story.append(_boxed_section("Certifications", cert_flowables))
            story.append(Spacer(1, 8))

        # Extracurricular Activities
        if resume.get("extracurriculars"):
            story.append(
                _boxed_section("Extracurricular Activities", [_p(resume["extracurriculars"])])
            )
            story.append(Spacer(1, 8))

        doc.build(story)
        return str(out_path)

    # Fallback plain text rendering - unchanged
    doc = SimpleDocTemplate(
        str(out_path),
        pagesize=A4,
        leftMargin=LEFT_MARGIN,
        rightMargin=RIGHT_MARGIN,
        topMargin=TOP_MARGIN,
        bottomMargin=BOTTOM_MARGIN,
    )
    story = []

    lines = str(resume).splitlines()
    normal_style = ParagraphStyle(
        "Normal", parent=styles["Normal"], fontName="Helvetica", fontSize=11, spaceAfter=6
    )
    heading_style = ParagraphStyle(
        "Heading", parent=styles["Heading2"], fontName="Helvetica-Bold", spaceAfter=6
    )

    for line in lines:
        line = line.strip()
        if not line:
            story.append(Spacer(1, 6))
            continue
        if line.isupper() and len(line) < 60:
            story.append(Paragraph(line, heading_style))
        else:
            if line.startswith(("-", "*", "•")):
                line = f"• {line[1:].strip()}"
            story.append(Paragraph(line, normal_style))

    doc.build(story)
    return str(out_path)
