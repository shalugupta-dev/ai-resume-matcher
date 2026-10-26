
import re
from functools import lru_cache

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

SKILL_CATEGORIES = {
    "Programming": [
        "python", "java", "javascript", "typescript", "c++", "c#",
    ],
    "Web Development": [
        "flask", "django", "fastapi", "html", "css", "react",
        "node.js", "rest api", "api development",
    ],
    "Databases": [
        "sql", "mysql", "postgresql", "sqlite", "mongodb", "redis",
    ],
    "Tools & Cloud": [
        "git", "github", "docker", "kubernetes", "linux",
        "aws", "azure", "jenkins", "ci/cd",
    ],
    "Data & AI": [
        "machine learning", "deep learning", "pandas", "numpy",
        "scikit-learn", "data analysis", "power bi", "excel",
    ],
    "Core Concepts & Testing": [
        "oop", "data structures", "algorithms", "unit testing",
        "pytest", "problem solving", "communication",
    ],
}


def normalize(text):
    return re.sub(r"\s+", " ", text.lower()).strip()


def extract_skills(text):
    normalized = normalize(text)
    found = set()

    all_skills = {
        skill
        for skills in SKILL_CATEGORIES.values()
        for skill in skills
    }

    for skill in all_skills:
        pattern = (
            r"(?<![a-z0-9+#.])"
            + re.escape(skill)
            + r"(?![a-z0-9+#.])"
        )
        if re.search(pattern, normalized):
            found.add(skill)

    return sorted(found)


@lru_cache(maxsize=1)
def load_semantic_model():
    """Load the sentence embedding model only when needed."""
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer("all-MiniLM-L6-v2")


def calculate_similarity(resume_text, job_description):
    """
    Return similarity score and method.
    Sentence embeddings are preferred; TF-IDF is the fallback.
    """
    resume_text = resume_text.strip()
    job_description = job_description.strip()

    try:
        model = load_semantic_model()
        embeddings = model.encode(
            [resume_text, job_description],
            normalize_embeddings=True,
        )
        similarity = float(embeddings[0] @ embeddings[1])

        return round(max(0, min(100, similarity * 100))), "Semantic NLP"

    except Exception:
        # Lightweight fallback if the model cannot load.
        try:
            vectorizer = TfidfVectorizer(
                stop_words="english",
                ngram_range=(1, 2),
            )
            matrix = vectorizer.fit_transform(
                [resume_text, job_description]
            )
            similarity = cosine_similarity(matrix[0:1], matrix[1:2])[0][0]

            return round(similarity * 100), "TF-IDF fallback"

        except ValueError:
            return 0, "TF-IDF fallback"


def analyze_resume(resume_data, job_description):
    if isinstance(resume_data, dict):
        resume_text = resume_data.get("text", "")
        sections = resume_data.get("sections", {})
    else:
        resume_text = resume_data
        sections = {}

    if not resume_text.strip():
        raise ValueError("Resume text is empty.")

    if not job_description.strip():
        raise ValueError("Please enter a job description.")

    resume_skills = extract_skills(resume_text)
    required_skills = extract_skills(job_description)

    if not required_skills:
        raise ValueError(
            "No supported technical skills were detected in the job "
            "description. Please add a more detailed job description."
        )

    matched_skills = sorted(
        set(resume_skills) & set(required_skills)
    )
    missing_skills = sorted(
        set(required_skills) - set(resume_skills)
    )

    keyword_score = round(
        len(matched_skills) / len(required_skills) * 100
    )

    semantic_score, matching_method = calculate_similarity(
        resume_text,
        job_description,
    )

    # Combined score: explicit skill coverage matters most.
    final_score = round(
        keyword_score * 0.65 + semantic_score * 0.35
    )

    categories = {}

    for category, skills in SKILL_CATEGORIES.items():
        required = sorted(set(skills) & set(required_skills))
        matched = sorted(set(required) & set(matched_skills))
        missing = sorted(set(required) - set(matched))

        if required:
            categories[category] = {
                "required": required,
                "matched": matched,
                "missing": missing,
            }

    suggestions = []

    if missing_skills:
        suggestions.append(
            "Review the missing skills and learn those relevant "
            "to your target role before adding them to your resume."
        )

    if not sections.get("projects"):
        suggestions.append(
            "Add relevant projects, your role, technology stack "
            "and measurable outcomes."
        )

    if not sections.get("experience"):
        suggestions.append(
            "If applicable, include internships, practical training "
            "or relevant experience."
        )

    if not sections.get("education"):
        suggestions.append(
            "Make sure your education and qualifications are clearly listed."
        )

    if not suggestions:
        suggestions.append(
            "Tailor your resume to the role and support your skills "
            "with relevant project examples."
        )

    return {
        "score": final_score,
        "keyword_score": keyword_score,
        "semantic_score": semantic_score,
        "matching_method": matching_method,
        "resume_skills": resume_skills,
        "required_skills": required_skills,
        "matched_skills": matched_skills,
        "missing_skills": missing_skills,
        "categories": categories,
        "suggestions": suggestions,
        "total_required": len(required_skills),
        "total_matched": len(matched_skills),
    }
