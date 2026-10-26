# AI Resume Analyzer & Job Matcher

An intelligent web application built with Python and Flask that analyzes resumes, compares them with job descriptions, and helps candidates identify skill gaps to improve their job readiness.

## 🚀 Features

- **Resume Upload:** Upload resumes in PDF format.
- **Resume Parsing:** Extract resume text and identify sections such as education, experience, projects, skills, and certifications.
- **Skill Extraction:** Detect technical skills from resumes and job descriptions.
- **AI-Powered Matching:** Calculate resume-job similarity using semantic NLP with Sentence Transformers.
- **Keyword Matching:** Identify matched and missing skills using a predefined skill library.
- **Match Score:** Display an overall compatibility score, keyword score, and semantic similarity.
- **Personal Dashboard:** Track previous analyses, average match score, best score, and skill gaps.
- **User Authentication:** Register, log in, and access your personal analysis history.
- **Input Validation:** Validate uploaded PDFs and handle invalid files.

## 🛠️ Tech Stack

- **Backend:** Python, Flask
- **Database:** SQLite, Flask-SQLAlchemy
- **Authentication:** Flask-Login
- **PDF Processing:** PyMuPDF
- **NLP & Machine Learning:** Sentence Transformers, scikit-learn, TF-IDF, cosine similarity
- **Frontend:** HTML, CSS, JavaScript, Bootstrap or custom styling (depending on the templates)
- **Charts:** Chart.js

## 📂 Project Structure

```text
ai-resume-matcher/
├── app.py
├── requirements.txt
├── services/
│   ├── __init__.py
│   ├── pdf_parser.py
│   └── matcher.py
├── templates/
│   ├── base.html
│   ├── index.html
│   ├── login.html
│   ├── register.html
│   ├── results.html
│   └── dashboard.html
├── static/
│   └── css/
│       └── style.css
├── .gitignore
└── README.md
```

## ⚙️ Installation and Setup

### 1. Clone the repository

```bash
git clone https://github.com/shalugupta-dev/ai-resume-matcher.git
cd ai-resume-matcher
```


### 2. Create a virtual environment

**Windows:**

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```powershell
python -m pip install -r requirements.txt
```

### 4. Configure environment variables

For local development, the application may use a development secret key. Before deployment, set a strong, private secret key using the `SECRET_KEY` environment variable.

**PowerShell:**

```powershell
$env:SECRET_KEY = "replace-with-a-strong-random-secret"
```

Do not commit real secrets, passwords, or your local database to GitHub.

### 5. Run the application

```powershell
python app.py
```

Open your browser and visit:

```text
http://127.0.0.1:5000
```

## 🧠 How It Works

1. A user uploads a PDF resume.
2. The application extracts readable text and relevant resume sections.
3. The user enters a target job title and job description.
4. The system extracts supported skills from both texts.
5. It calculates keyword overlap and semantic similarity.
6. The application displays the match score, matched skills, missing skills, and improvement suggestions.
7. Analysis history and performance summaries are available on the personal dashboard.

## 📊 Matching Method

The application combines two matching approaches:

- **Keyword Matching:** Measures the overlap between detected resume skills and job-description skills.
- **Semantic Similarity:** Uses the `all-MiniLM-L6-v2` Sentence Transformer model to compare text embeddings. If semantic model loading fails, the application can fall back to TF-IDF similarity.

The displayed score is an estimate for resume improvement, not a guarantee of selection or employment.

## 🔒 Security Notes

- Keep secret keys and credentials private.
- Do not upload `.env` files or your local SQLite database.
- Validate uploaded files and limit their size.
- Use HTTPS and production-ready settings when deploying.
- Review debug settings and allowed hosts before public deployment.

## 🔮 Future Improvements

- Expand the technical skills database.
- Add downloadable analysis reports.
- Support more resume formats.
- Improve skill categorization and recommendations.
- Add job-role-specific resume suggestions.

## 👩‍💻 Author

**Shalu Gupta**

 https://github.com/shalugupta-dev/ai-resume-matcher.git
---

⭐ If you find this project useful, consider giving the repository a star.
