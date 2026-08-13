import os
import uuid
import io
from datetime import datetime, timedelta
from typing import Optional, List

from fastapi import FastAPI, Depends, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, text
from sqlalchemy.sql import func
from pydantic import BaseModel, EmailStr
from passlib.context import CryptContext
from jose import jwt
from pypdf import PdfReader

from database import engine, Base, get_db

# ===================== MODELS =====================

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String(100), nullable=False)
    email = Column(String(150), unique=True, nullable=False, index=True)
    password = Column(String(255), nullable=False)
    phone = Column(String(20), nullable=True)
    location = Column(String(150), nullable=True)
    education = Column(Text, nullable=True)
    experience = Column(Text, nullable=True)
    skills = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Resume(Base):
    __tablename__ = "resumes"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    filename = Column(String(255), nullable=False)
    filepath = Column(String(500), nullable=False)
    extracted_text = Column(Text, nullable=True)
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())


class Job(Base):
    __tablename__ = "jobs"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(150), nullable=False)
    company = Column(String(150), nullable=False)
    location = Column(String(150), nullable=False)
    job_type = Column(String(50), nullable=True)
    description = Column(Text, nullable=False)
    skills = Column(Text, nullable=False)
    apply_url = Column(String(500), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


Base.metadata.create_all(bind=engine)

# ===================== AUTH HELPERS =====================

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
SECRET_KEY = "pluto-secret-key-change-this-later"
ALGORITHM = "HS256"
TOKEN_EXPIRE_MINUTES = 60 * 24
security = HTTPBearer()


def hash_password(p): return pwd_context.hash(p)
def verify_password(p, h): return pwd_context.verify(p, h)


def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token.")

    user = db.query(User).filter(User.email == payload.get("sub")).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found.")
    return user

# ===================== SCHEMAS =====================

class UserRegisterRequest(BaseModel):
    fullName: str
    email: EmailStr
    password: str

class UserLoginRequest(BaseModel):
    email: EmailStr
    password: str

class UserProfileUpdateRequest(BaseModel):
    name: str
    email: str
    phone: Optional[str] = None
    location: Optional[str] = None
    education: Optional[str] = None
    experience: Optional[str] = None
    skills: List[str] = []

# ===================== APP =====================

app = FastAPI(title="PLUTO Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def read_root():
    return {"message": "Hello World! PLUTO backend is running."}


@app.get("/test-db")
def test_db_connection():
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return {"status": "success", "message": "Connected to MySQL successfully!"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


# ===== REGISTER =====
@app.post("/api/auth/register")
def register_user(user_data: UserRegisterRequest, db: Session = Depends(get_db)):
    try:
        existing_user = db.query(User).filter(User.email == user_data.email).first()
        if existing_user:
            raise HTTPException(status_code=400, detail="An account with this email already exists.")

        new_user = User(
            full_name=user_data.fullName,
            email=user_data.email,
            password=hash_password(user_data.password),
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        return {"message": "Account created successfully!"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"DEBUG ERROR: {str(e)}")


# ===== LOGIN =====
@app.post("/api/auth/login")
def login_user(login_data: UserLoginRequest, db: Session = Depends(get_db)):
    try:
        user = db.query(User).filter(User.email == login_data.email).first()
        if not user or not verify_password(login_data.password, user.password):
            raise HTTPException(status_code=401, detail="Invalid email or password.")
        token = create_access_token(data={"sub": user.email})
        return {"token": token, "name": user.full_name}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"DEBUG ERROR: {str(e)}")


# ===== PROFILE =====
@app.get("/api/users/profile")
def get_profile(current_user: User = Depends(get_current_user)):
    return {
        "name": current_user.full_name,
        "email": current_user.email,
        "phone": current_user.phone,
        "location": current_user.location,
        "education": current_user.education,
        "experience": current_user.experience,
        "skills": current_user.skills.split(",") if current_user.skills else [],
    }


@app.put("/api/users/profile")
def update_profile(
    profile_data: UserProfileUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    current_user.full_name = profile_data.name
    current_user.email = profile_data.email
    current_user.phone = profile_data.phone
    current_user.location = profile_data.location
    current_user.education = profile_data.education
    current_user.experience = profile_data.experience
    current_user.skills = ",".join(profile_data.skills)
    db.commit()
    return {"message": "Profile updated successfully!"}


# ===== RESUME UPLOAD =====
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def extract_text_from_pdf(file_content: bytes) -> str:
    reader = PdfReader(io.BytesIO(file_content))
    full_text = ""
    for page in reader.pages:
        page_text = page.extract_text()
        if page_text:
            full_text += page_text + " "
    return full_text.strip()


@app.post("/api/resumes/upload")
async def upload_resume(
    resume: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    file_ext = os.path.splitext(resume.filename)[1].lower()
    if file_ext != ".pdf":
        raise HTTPException(status_code=400, detail="Only PDF files are allowed.")

    file_content = await resume.read()
    if len(file_content) / (1024 * 1024) > 5:
        raise HTTPException(status_code=400, detail="File is too large. Max size is 5MB.")

    unique_filename = f"{current_user.id}_{uuid.uuid4().hex}{file_ext}"
    file_path = os.path.join(UPLOAD_FOLDER, unique_filename)
    with open(file_path, "wb") as f:
        f.write(file_content)

    extracted_text = extract_text_from_pdf(file_content)
    if not extracted_text:
        raise HTTPException(status_code=400, detail="Couldn't read any text from this PDF.")

    new_resume = Resume(
        user_id=current_user.id,
        filename=resume.filename,
        filepath=file_path,
        extracted_text=extracted_text,
    )
    db.add(new_resume)
    db.commit()
    db.refresh(new_resume)
    return {"resumeId": new_resume.id}


# ===== ATS =====
ROLE_KEYWORDS = {
    "Frontend Developer": ["html", "css", "javascript", "react", "responsive design", "git", "ui/ux", "rest api"],
    "Backend Developer": ["node.js", "express", "api", "database", "sql", "mongodb", "authentication", "server"],
    "Data Analyst": ["excel", "sql", "python", "data visualization", "tableau", "power bi", "statistics"],
    "Data Scientist": ["python", "machine learning", "pandas", "numpy", "statistics", "sql", "data modeling"],
    "Digital Marketing": ["seo", "google ads", "social media", "content marketing", "analytics", "email marketing"],
}
EXPERIENCE_HINTS = ["experience", "worked", "internship", "employed", "responsibilities"]
EDUCATION_HINTS = ["degree", "bachelor", "university", "college", "b.sc", "b.tech", "education", "diploma"]


@app.get("/api/ats/reports/{resume_id}")
def get_ats_report(resume_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    resume = db.query(Resume).filter(Resume.id == resume_id).first()
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found.")
    if resume.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="You don't have access to this resume.")

    text_lower = resume.extracted_text.lower()
    best_role, best_score, best_matched, best_missing = None, 0, [], []
    for role, keywords in ROLE_KEYWORDS.items():
        matched = [kw for kw in keywords if kw in text_lower]
        missing = [kw for kw in keywords if kw not in matched]
        score = round((len(matched) / len(keywords)) * 100)
        if score > best_score:
            best_score, best_role, best_matched, best_missing = score, role, matched, missing

    experience_score = min(100, 40 + sum(1 for w in EXPERIENCE_HINTS if w in text_lower) * 15)
    education_score = min(100, 40 + sum(1 for w in EDUCATION_HINTS if w in text_lower) * 15)
    text_length = len(resume.extracted_text)
    formatting_score = 90 if text_length > 800 else 70 if text_length > 300 else 45
    overall_score = round((best_score + best_score + experience_score + education_score + formatting_score) / 5)

    suggestions = []
    if best_missing:
        suggestions.append(f"Consider adding these relevant keywords: {', '.join(best_missing[:3])}.")
    if experience_score < 70:
        suggestions.append("Add more detail about your work experience or internships.")
    if education_score < 70:
        suggestions.append("Include your education details (degree, institution, year).")
    if not suggestions:
        suggestions.append("Your resume looks strong! Keep it updated as your skills grow.")

    return {
        "overallScore": overall_score, "keywordScore": best_score, "skillsScore": best_score,
        "experienceScore": experience_score, "educationScore": education_score,
        "formattingScore": formatting_score, "matchedKeywords": best_matched,
        "missingKeywords": best_missing, "suggestions": suggestions,
    }


# ===== JOBS =====
def get_latest_resume_text(current_user, db):
    latest = db.query(Resume).filter(Resume.user_id == current_user.id).order_by(Resume.uploaded_at.desc()).first()
    return latest.extracted_text.lower() if latest and latest.extracted_text else ""


def calc_match(job_skills, resume_text_lower):
    if not job_skills or not resume_text_lower:
        return 0
    matched = [s for s in job_skills if s.strip().lower() in resume_text_lower]
    return round((len(matched) / len(job_skills)) * 100)


@app.get("/api/jobs/recommended")
def get_recommended_jobs(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    resume_text_lower = get_latest_resume_text(current_user, db)
    jobs = db.query(Job).all()
    result = []
    for job in jobs:
        job_skills = job.skills.split(",") if job.skills else []
        result.append({
            "id": job.id, "title": job.title, "company": job.company, "location": job.location,
            "type": job.job_type, "matchPercent": calc_match(job_skills, resume_text_lower),
            "skills": job_skills, "description": job.description,
        })
    result.sort(key=lambda j: j["matchPercent"], reverse=True)
    return result


@app.get("/api/jobs/{job_id}")
def get_job_details(job_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")
    resume_text_lower = get_latest_resume_text(current_user, db)
    job_skills = job.skills.split(",") if job.skills else []
    return {
        "title": job.title, "company": job.company, "location": job.location, "type": job.job_type,
        "matchPercent": calc_match(job_skills, resume_text_lower), "description": job.description,
        "skills": job_skills, "applyUrl": job.apply_url,
    }