
import re
from pathlib import Path

import pymupdf


SECTION_PATTERNS = {
    "education": r"\b(education|academic background|qualifications)\b",
    "experience": r"\b(work experience|professional experience|employment history|internship|experience)\b",
    "projects": r"\b(projects|personal projects|academic projects)\b",
    "skills": r"\b(technical skills|skills|core competencies|technologies)\b",
    "certifications": r"\b(certifications|certificates|courses)\b",
}


def extract_text_from_pdf(file_path):
    """Extract readable text from a PDF resume."""
    if Path(file_path).suffix.lower() != ".pdf":
        raise ValueError("Only PDF files are supported.")

    try:
        with pymupdf.open(file_path) as pdf:
            if len(pdf) == 0:
                raise ValueError("The PDF file is empty.")

            if len(pdf) > 30:
                raise ValueError("The resume cannot exceed 30 pages.")

            text = "\n".join(page.get_text() for page in pdf).strip()

    except ValueError:
        raise
    except Exception as exc:
        raise ValueError(
            "Unable to read this PDF. Please upload a valid PDF file."
        ) from exc

    if not text:
        raise ValueError(
            "No readable text was found. Please upload a text-based PDF."
        )

    if len(text) > 200_000:
        raise ValueError("The extracted resume text is too long.")

    return text


def extract_resume_sections(text):
    """Identify common resume sections using heading heuristics."""
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    sections = {
        "education": [],
        "experience": [],
        "projects": [],
        "skills": [],
        "certifications": [],
    }

    current_section = None

    for line in lines:
        normalized = re.sub(r"[:\s]+$", "", line.lower()).strip()
        matched_section = None

        for section, pattern in SECTION_PATTERNS.items():
            if re.fullmatch(pattern, normalized, flags=re.IGNORECASE):
                matched_section = section
                break

        if matched_section:
            current_section = matched_section
            continue

        if current_section:
            # Avoid assigning an entire long resume to one section.
            sections[current_section].append(line)

    return {
        section: "\n".join(items).strip()
        for section, items in sections.items()
    }


def parse_resume(file_path):
    """Return extracted text and basic resume insights."""
    text = extract_text_from_pdf(file_path)
    sections = extract_resume_sections(text)

    email_match = re.search(
        r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b",
        text,
        re.IGNORECASE,
    )

    phone_match = re.search(
        r"(?<!\w)(?:\+?\d[\d\s().-]{7,}\d)(?!\w)",
        text,
    )

    word_count = len(text.split())

    return {
        "text": text,
        "sections": sections,
        "email_found": bool(email_match),
        "phone_found": bool(phone_match),
        "word_count": word_count,
        "education_found": bool(sections["education"]),
        "experience_found": bool(sections["experience"]),
        "projects_found": bool(sections["projects"]),
        "skills_section_found": bool(sections["skills"]),
        "certifications_found": bool(sections["certifications"]),
    }
