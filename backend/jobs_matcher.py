# jobs_matcher.py
# Ported from a desktop resume-job-matching script into web-friendly functions.
# No file dialogs, no CSV, no browser-opening — just pure functions that take
# resume text (already extracted from an uploaded PDF) and return matched jobs.

import os
import re
import requests
from datetime import datetime

# ============================================================
# ADZUNA SETTINGS (keys come from environment variables, never hardcoded)
# ============================================================

ADZUNA_APP_ID = os.getenv("ADZUNA_APP_ID")
ADZUNA_APP_KEY = os.getenv("ADZUNA_APP_KEY")
ADZUNA_COUNTRY_CODE = "in"
ADZUNA_RESULTS_PER_PAGE = 20
MAX_ROLE_SEARCHES = 5   # kept smaller than the original 10 to keep response times reasonable
MIN_MATCH_SCORE = 25
REQUEST_TIMEOUT = 15


# ============================================================
# SKILLS DATABASE
# ============================================================

SKILLS_LIST = [
    "python", "java", "c++", "c", "c#", "javascript", "typescript", "php", "ruby", "go", "kotlin", "swift",
    "html", "css", "react", "angular", "node.js", "flask", "django", "fastapi", "bootstrap", "next.js",
    "sql", "mysql", "postgresql", "mongodb", "oracle", "pandas", "numpy", "matplotlib", "seaborn",
    "power bi", "tableau", "excel", "data analysis", "data visualization", "statistics",
    "machine learning", "deep learning", "artificial intelligence", "data science", "tensorflow",
    "keras", "pytorch", "scikit-learn", "nlp", "computer vision", "generative ai", "llm",
    "aws", "azure", "google cloud", "docker", "kubernetes", "git", "github", "linux", "jenkins", "terraform",
    "accounting", "finance", "financial analysis", "financial modeling", "tally", "tally erp", "gst",
    "taxation", "auditing", "bookkeeping", "quickbooks", "sap", "ms office",
    "human resources", "hr", "recruitment", "talent acquisition", "payroll", "employee relations", "hr operations",
    "marketing", "digital marketing", "seo", "sem", "social media", "content marketing", "google ads",
    "facebook ads", "branding", "email marketing",
    "sales", "business development", "lead generation", "customer relationship", "crm", "inside sales",
    "autocad", "solidworks", "catia", "3d modeling", "ui design", "ux design", "figma", "photoshop",
    "communication", "leadership", "project management", "management", "research", "word", "powerpoint",
    "problem solving",
]

SKILL_ALIASES = {
    "powerbi": "power bi", "power-bi": "power bi",
    "ms excel": "excel", "microsoft excel": "excel",
    "ms word": "word", "microsoft word": "word",
    "ms powerpoint": "powerpoint", "microsoft powerpoint": "powerpoint",
    "nodejs": "node.js", "node js": "node.js", "nextjs": "next.js",
    "scikit learn": "scikit-learn", "sklearn": "scikit-learn",
    "machine-learning": "machine learning", "deep-learning": "deep learning",
    "data-science": "data science", "artificial-intelligence": "artificial intelligence",
    "ml": "machine learning", "ai": "artificial intelligence",
    "ui/ux": "ui design", "user interface": "ui design", "user experience": "ux design",
}

JOB_ROLES = {
    "python": ["Python Developer", "Backend Developer", "Software Developer"],
    "java": ["Java Developer", "Backend Developer", "Software Developer"],
    "c++": ["C++ Developer", "Software Developer"],
    "javascript": ["JavaScript Developer", "Frontend Developer"],
    "react": ["React Developer", "Frontend Developer"],
    "angular": ["Angular Developer", "Frontend Developer"],
    "node.js": ["Node.js Developer", "Backend Developer"],
    "sql": ["SQL Developer", "Database Developer", "Data Analyst"],
    "pandas": ["Data Analyst", "Python Data Analyst"],
    "numpy": ["Data Analyst", "Python Developer"],
    "data analysis": ["Data Analyst", "Business Analyst"],
    "data visualization": ["Data Analyst", "BI Analyst"],
    "data science": ["Data Scientist", "Data Analyst"],
    "machine learning": ["Machine Learning Engineer", "ML Engineer", "Data Scientist"],
    "deep learning": ["Deep Learning Engineer", "Machine Learning Engineer"],
    "artificial intelligence": ["AI Engineer", "Artificial Intelligence Engineer"],
    "tensorflow": ["Machine Learning Engineer", "AI Engineer"],
    "pytorch": ["Machine Learning Engineer", "AI Engineer"],
    "nlp": ["NLP Engineer", "AI Engineer"],
    "computer vision": ["Computer Vision Engineer", "AI Engineer"],
    "generative ai": ["Generative AI Engineer", "AI Engineer"],
    "llm": ["LLM Engineer", "Generative AI Engineer"],
    "excel": ["Data Analyst", "MIS Executive", "Business Analyst", "Finance Executive"],
    "power bi": ["Power BI Developer", "Data Analyst", "Business Intelligence Analyst"],
    "tableau": ["Tableau Developer", "Data Analyst", "Business Intelligence Analyst"],
    "accounting": ["Accountant", "Accounts Executive", "Finance Executive"],
    "tally": ["Tally Accountant", "Accountant", "Accounts Executive"],
    "tally erp": ["Tally Accountant", "Accounts Executive"],
    "gst": ["GST Executive", "Tax Executive", "Accountant"],
    "taxation": ["Tax Executive", "Tax Associate", "Accountant"],
    "auditing": ["Audit Associate", "Internal Auditor", "Audit Executive"],
    "bookkeeping": ["Bookkeeper", "Accountant", "Accounts Executive"],
    "finance": ["Finance Executive", "Financial Analyst", "Finance Associate"],
    "financial analysis": ["Financial Analyst", "Finance Analyst"],
    "financial modeling": ["Financial Analyst", "Financial Modeler"],
    "hr": ["HR Executive", "HR Associate", "HR Coordinator"],
    "human resources": ["HR Executive", "HR Associate", "HR Coordinator"],
    "recruitment": ["Recruiter", "HR Recruiter", "Talent Acquisition Executive"],
    "talent acquisition": ["Talent Acquisition Executive", "Recruiter"],
    "payroll": ["Payroll Executive", "HR Executive"],
    "hr operations": ["HR Executive", "HR Operations Executive"],
    "marketing": ["Marketing Executive", "Marketing Associate", "Brand Executive"],
    "digital marketing": ["Digital Marketing Executive", "Digital Marketing Specialist"],
    "seo": ["SEO Executive", "SEO Specialist"],
    "social media": ["Social Media Executive", "Social Media Manager"],
    "content marketing": ["Content Marketing Executive", "Content Strategist"],
    "google ads": ["Google Ads Specialist", "Digital Marketing Specialist"],
    "sales": ["Sales Executive", "Sales Associate", "Business Development Executive"],
    "business development": ["Business Development Executive", "Business Development Associate"],
    "lead generation": ["Lead Generation Executive", "Business Development Executive"],
    "crm": ["CRM Executive", "Sales Executive"],
    "autocad": ["AutoCAD Designer", "Design Engineer", "CAD Engineer"],
    "solidworks": ["Mechanical Design Engineer", "Design Engineer"],
    "catia": ["Design Engineer", "Mechanical Engineer"],
    "figma": ["UI Designer", "UX Designer", "UI/UX Designer"],
    "ui design": ["UI Designer", "UI/UX Designer"],
    "ux design": ["UX Designer", "UI/UX Designer"],
    "project management": ["Project Coordinator", "Project Manager", "Project Executive"],
    "management": ["Management Trainee", "Operations Executive", "Business Analyst"],
    "communication": ["Customer Support Executive", "Business Development Executive"],
}

EDUCATION_KEYWORDS = {
    "b.tech": "B.Tech", "btech": "B.Tech", "b.e": "B.E", "b.e.": "B.E", "be": "B.E",
    "bca": "BCA", "mca": "MCA", "b.com": "B.Com", "bcom": "B.Com", "m.com": "M.Com", "mcom": "M.Com",
    "bba": "BBA", "mba": "MBA", "b.sc": "B.Sc", "bsc": "B.Sc", "m.sc": "M.Sc", "msc": "M.Sc",
    "b.a": "B.A", "b.a.": "B.A", "ba": "B.A", "m.a": "M.A", "ma": "M.A",
    "b.pharm": "B.Pharm", "m.pharm": "M.Pharm", "llb": "LLB", "llm": "LLM",
}

EDUCATION_JOB_KEYWORDS = {
    "B.Tech": ["btech", "b.tech", "engineering"], "B.E": ["b.e", "engineering"],
    "BCA": ["bca", "computer applications"], "MCA": ["mca", "computer applications"],
    "B.Com": ["bcom", "commerce"], "M.Com": ["mcom", "commerce"],
    "BBA": ["bba", "business administration"], "MBA": ["mba", "business administration"],
    "B.Sc": ["bsc", "b.sc"], "M.Sc": ["msc", "m.sc"], "B.A": ["b.a", "arts"], "M.A": ["m.a", "arts"],
}

EDUCATION_ROLE_FALLBACK = {
    "B.Com": ["Accountant", "Finance Executive", "Accounts Executive"],
    "M.Com": ["Accountant", "Finance Analyst", "Accounts Executive"],
    "BBA": ["Business Analyst", "Marketing Executive", "HR Executive"],
    "MBA": ["Business Analyst", "Marketing Manager", "HR Executive"],
    "BCA": ["Software Developer", "Web Developer", "Data Analyst"],
    "MCA": ["Software Developer", "Backend Developer", "Data Analyst"],
    "B.Tech": ["Software Developer", "Data Analyst", "Business Analyst"],
    "B.E": ["Software Developer", "Design Engineer", "Business Analyst"],
    "B.Sc": ["Data Analyst", "Research Assistant", "Business Analyst"],
    "M.Sc": ["Data Scientist", "Data Analyst", "Research Analyst"],
}


# ============================================================
# TEXT HELPERS
# ============================================================

def normalize_text(text):
    text = str(text or "").lower()
    text = text.replace("&", " and ")
    text = re.sub(r"[^a-z0-9+#. ]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def contains_term(text, term):
    text = normalize_text(text)
    term = normalize_text(term)
    if not term:
        return False
    if any(char in term for char in ["+", "#", "."]):
        return term in text
    return bool(re.search(r"(?<![a-z0-9])" + re.escape(term) + r"(?![a-z0-9])", text))


# ============================================================
# EXTRACTION (education / experience / skills from resume text)
# ============================================================

def extract_education(resume_text):
    text = normalize_text(resume_text)
    found = []
    for keyword, degree in EDUCATION_KEYWORDS.items():
        if contains_term(text, keyword) and degree not in found:
            found.append(degree)
    return found


def extract_experience(resume_text):
    text = normalize_text(resume_text)
    if re.search(r"\bfresher\b|\bno experience\b|\bentry level\b", text):
        return 0.0

    patterns = [
        r"(\d+(?:\.\d+)?)\s*\+?\s*(?:years?|yrs?)\s*(?:of)?\s*(?:experience|exp)?",
        r"experience\s*[:\-]?\s*(\d+(?:\.\d+)?)\s*\+?\s*(?:years?|yrs?)",
    ]
    values = []
    for pattern in patterns:
        for match in re.finditer(pattern, text):
            try:
                values.append(float(match.group(1)))
            except (ValueError, IndexError):
                pass
    return max(values) if values else None


def extract_skills(resume_text):
    text = normalize_text(resume_text)
    found = []
    for skill in SKILLS_LIST:
        if contains_term(text, skill) and skill not in found:
            found.append(skill)
    for alias, canonical in SKILL_ALIASES.items():
        if contains_term(text, alias) and canonical not in found:
            found.append(canonical)
    return found


def generate_job_keywords(skills, education):
    roles = []
    seen = set()
    for skill in skills:
        for role in JOB_ROLES.get(skill, []):
            key = role.lower()
            if key not in seen:
                seen.add(key)
                roles.append(role)
    for degree in education:
        for role in EDUCATION_ROLE_FALLBACK.get(degree, []):
            key = role.lower()
            if key not in seen:
                seen.add(key)
                roles.append(role)
    return roles[:MAX_ROLE_SEARCHES]


# ============================================================
# ADZUNA API
# ============================================================

def get_jobs_from_adzuna(job_keyword, location="India"):
    url = f"https://api.adzuna.com/v1/api/jobs/{ADZUNA_COUNTRY_CODE}/search/1"
    params = {
        "app_id": ADZUNA_APP_ID,
        "app_key": ADZUNA_APP_KEY,
        "what": job_keyword,
        "where": location,
        "results_per_page": ADZUNA_RESULTS_PER_PAGE,
        "content-type": "application/json",
    }
    try:
        response = requests.get(url, params=params, timeout=REQUEST_TIMEOUT)
        if response.status_code == 200:
            return response.json().get("results", [])
        print(f"Adzuna API error for '{job_keyword}': {response.status_code}")
        return []
    except requests.exceptions.RequestException as e:
        print(f"Adzuna connection error for '{job_keyword}': {e}")
        return []


def extract_job_experience(job_text):
    text = normalize_text(job_text)
    patterns = [
        r"(\d+(?:\.\d+)?)\s*\+?\s*(?:years?|yrs?)\s*(?:of)?\s*(?:experience|exp)?",
        r"minimum\s*(?:of)?\s*(\d+(?:\.\d+)?)\s*(?:years?|yrs?)",
        r"at least\s*(\d+(?:\.\d+)?)\s*(?:years?|yrs?)",
    ]
    values = []
    for pattern in patterns:
        for match in re.finditer(pattern, text):
            try:
                values.append(float(match.group(1)))
            except (ValueError, IndexError):
                pass
    return min(values) if values else None


def calculate_match_score(job, resume_skills, education, resume_experience, target_location):
    title = job.get("title", "")
    description = job.get("description", "")
    category = job.get("category", {}).get("label", "")
    job_text = normalize_text(f"{title} {description} {category}")
    title_text = normalize_text(title)

    matched_skills = [s for s in resume_skills if contains_term(job_text, s)]
    skill_score = (len(matched_skills) / len(resume_skills)) * 50 if resume_skills else 0

    title_score = 0
    for skill in resume_skills:
        if contains_term(title_text, skill):
            title_score += 7
    role_words = ["developer", "analyst", "engineer", "scientist", "accountant", "finance",
                   "marketing", "hr", "designer", "recruiter", "sales", "business"]
    for word in role_words:
        if contains_term(title_text, word):
            title_score += 3
            break
    title_score = min(title_score, 20)

    education_score = 0
    for degree in education:
        for keyword in EDUCATION_JOB_KEYWORDS.get(degree, []):
            if contains_term(job_text, keyword):
                education_score = 15
                break
        if education_score == 15:
            break
    if education and education_score == 0:
        education_score = 7

    experience_score = 0
    required_exp = extract_job_experience(job_text)
    if resume_experience is not None:
        if required_exp is None:
            experience_score = 7
        elif resume_experience >= required_exp:
            experience_score = 10
        elif resume_experience + 1 >= required_exp:
            experience_score = 6
        else:
            experience_score = 2

    location_text = normalize_text(job.get("location", {}).get("display_name", ""))
    location_score = 5 if contains_term(location_text, target_location) else 2

    total = skill_score + title_score + education_score + experience_score + location_score
    return round(min(total, 100), 2), matched_skills


def get_match_level(score):
    if score >= 80: return "Excellent Match"
    if score >= 65: return "Very Good Match"
    if score >= 50: return "Good Match"
    if score >= 35: return "Moderate Match"
    return "Low Match"


def find_missing_skills(job, resume_skills):
    title = job.get("title", "")
    description = job.get("description", "")
    category = job.get("category", {}).get("label", "")
    job_text = normalize_text(f"{title} {description} {category}")
    resume_set = set(s.lower() for s in resume_skills)
    missing = [s for s in SKILLS_LIST if s.lower() not in resume_set and contains_term(job_text, s)]
    return missing[:10]


def format_salary(job):
    minimum = job.get("salary_min")
    maximum = job.get("salary_max")
    try:
        if minimum and maximum:
            return f"₹{minimum:,.0f} - ₹{maximum:,.0f}"
        if minimum:
            return f"From ₹{minimum:,.0f}"
        if maximum:
            return f"Up to ₹{maximum:,.0f}"
    except (ValueError, TypeError):
        pass
    return "Not Mentioned"


def format_posted_date(job):
    date_value = job.get("created")
    if not date_value:
        return "Not Mentioned"
    try:
        dt = datetime.fromisoformat(date_value.replace("Z", "+00:00"))
        return dt.strftime("%d %b %Y")
    except (ValueError, TypeError):
        return str(date_value)


# ============================================================
# MAIN ENTRY POINT — this is what main.py calls
# ============================================================

def get_adzuna_recommendations(resume_text: str, location: str = "India"):
    """Given raw resume text, returns a list of matched jobs from Adzuna,
    each shaped for the frontend (title, company, matchPercent, skills, etc.)."""

    if not ADZUNA_APP_ID or not ADZUNA_APP_KEY:
        print("Adzuna credentials missing — skipping Adzuna job search.")
        return []

    skills = extract_skills(resume_text)
    education = extract_education(resume_text)
    experience = extract_experience(resume_text)

    job_keywords = generate_job_keywords(skills, education)
    if not job_keywords:
        return []

    results = []
    seen_keys = set()

    for keyword in job_keywords:
        jobs = get_jobs_from_adzuna(keyword, location)

        for job in jobs:
            job_id = str(job.get("id", "")).strip()
            title = job.get("title", "").strip()
            company = job.get("company", {}).get("display_name", "").strip()
            unique_key = job_id if job_id else f"{title.lower()}|{company.lower()}"

            if unique_key in seen_keys:
                continue
            seen_keys.add(unique_key)

            score, matched_skills = calculate_match_score(job, skills, education, experience, location)
            if score < MIN_MATCH_SCORE:
                continue

            missing_skills = find_missing_skills(job, skills)

            results.append({
                "id": f"adzuna_{job_id}" if job_id else f"adzuna_{len(results)}",
                "title": title or "Untitled Role",
                "company": company or "Unknown Company",
                "location": job.get("location", {}).get("display_name", "Not specified"),
                "type": job.get("contract_time", "Not specified"),
                "matchPercent": int(score),
                "matchLevel": get_match_level(score),
                "skills": matched_skills,
                "missingSkills": missing_skills,
                "description": job.get("description", ""),
                "salary": format_salary(job),
                "postedDate": format_posted_date(job),
                "applyUrl": job.get("redirect_url", ""),
                "source": "adzuna",
            })

    results.sort(key=lambda j: j["matchPercent"], reverse=True)
    return results[:10]