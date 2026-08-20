import os
import uuid
import io
import smtplib
from datetime import datetime, timedelta
from typing import Optional, List
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from fastapi import FastAPI, Depends, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, text
from sqlalchemy.sql import func
from pydantic import BaseModel, EmailStr
from passlib.context import CryptContext
from jose import jwt, JWTError
from pypdf import PdfReader

from database import engine, Base, get_db
import jobs_matcher

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
RESET_TOKEN_EXPIRE_MINUTES = 15
security = HTTPBearer()


def hash_password(p): return pwd_context.hash(p)
def verify_password(p, h): return pwd_context.verify(p, h)


def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def create_reset_token(email: str) -> str:
    """Short-lived token (15 min) used only for password reset links."""
    to_encode = {"sub": email, "purpose": "password_reset"}
    expire = datetime.utcnow() + timedelta(minutes=RESET_TOKEN_EXPIRE_MINUTES)
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

# ===================== EMAIL HELPERS =====================

GMAIL_USER = os.getenv("GMAIL_USER")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")

# Change this to your actual live frontend URL
FRONTEND_URL = "https://dheerajsuner050-a11y.github.io/pluto-project/frontend"


def send_email(to_email: str, subject: str, body: str):
    """Generic email sender — used by both welcome and reset-password emails."""
    try:
        msg = MIMEMultipart()
        msg["From"] = GMAIL_USER
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))

        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(GMAIL_USER, GMAIL_APP_PASSWORD)
            server.send_message(msg)

    except Exception as e:
        print(f"Failed to send email to {to_email}: {e}")


def send_welcome_email(to_email: str, name: str):
    body = f"""Hi {name},

Welcome to PLUTO! Your account has been created successfully.

You can now upload your resume, get your ATS score, and discover jobs matched to your skills.

Thanks,
The PLUTO Team
"""
    send_email(to_email, "Welcome to PLUTO!", body)


def send_reset_email(to_email: str, name: str, token: str):
    reset_link = f"{FRONTEND_URL}/reset-password.html?token={token}"
    body = f"""Hi {name},

We received a request to reset your PLUTO password.

Click the link below to set a new password (valid for {RESET_TOKEN_EXPIRE_MINUTES} minutes):
{reset_link}

If you didn't request this, you can safely ignore this email.

Thanks,
The PLUTO Team
"""
    send_email(to_email, "Reset your PLUTO password", body)

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

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    token: str
    newPassword: str

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

        send_welcome_email(new_user.email, new_user.full_name)

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


# ===== FORGOT PASSWORD =====
@app.post("/api/auth/forgot-password")
def forgot_password(data: ForgotPasswordRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == data.email).first()

    # Always return the same message, whether or not the email exists —
    # this prevents attackers from guessing which emails are registered.
    if user:
        token = create_reset_token(user.email)
        send_reset_email(user.email, user.full_name, token)

    return {"message": "If that email is registered, a reset link has been sent."}


# ===== RESET PASSWORD =====
@app.post("/api/auth/reset-password")
def reset_password(data: ResetPasswordRequest, db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(data.token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=400, detail="This reset link is invalid or has expired.")

    if payload.get("purpose") != "password_reset":
        raise HTTPException(status_code=400, detail="Invalid reset token.")

    user = db.query(User).filter(User.email == payload.get("sub")).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    user.password = hash_password(data.newPassword)
    db.commit()

    return {"message": "Password reset successfully! You can now log in with your new password."}


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


# ===== RESUME UPLOAD (+ AUTOFILL PROFILE) =====
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

    # ----- AUTOFILL PROFILE -----
    # Only fills in fields that are still empty, so we never overwrite
    # something the user already edited manually.
    try:
        skills_found = jobs_matcher.extract_skills(extracted_text)
        education_found = jobs_matcher.extract_education(extracted_text)
        experience_found = jobs_matcher.extract_experience(extracted_text)

        if not current_user.skills and skills_found:
            current_user.skills = ",".join(skills_found)

        if not current_user.education and education_found:
            current_user.education = ", ".join(education_found)

        if not current_user.experience and experience_found is not None:
            current_user.experience = f"{experience_found:g} year(s)"

        db.commit()
    except Exception as e:
        print(f"Autofill profile failed (non-blocking): {e}")

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
    return latest.extracted_text if latest and latest.extracted_text else ""


def calc_match(job_skills, resume_text_lower):
    if not job_skills or not resume_text_lower:
        return 0
    matched = [s for s in job_skills if s.strip().lower() in resume_text_lower]
    return round((len(matched) / len(job_skills)) * 100)


@app.get("/api/jobs/recommended")
def get_recommended_jobs(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    resume_text = get_latest_resume_text(current_user, db)
    resume_text_lower = resume_text.lower()

    internal_jobs = db.query(Job).all()
    result = []
    for job in internal_jobs:
        job_skills = job.skills.split(",") if job.skills else []
        result.append({
            "id": str(job.id),
            "title": job.title,
            "company": job.company,
            "location": job.location,
            "type": job.job_type,
            "matchPercent": calc_match(job_skills, resume_text_lower),
            "skills": job_skills,
            "description": job.description,
            "source": "internal",
        })

    if resume_text:
        try:
            adzuna_jobs = jobs_matcher.get_adzuna_recommendations(resume_text)
            result.extend(adzuna_jobs)
        except Exception as e:
            print(f"Adzuna job fetch failed: {e}")

    result.sort(key=lambda j: j["matchPercent"], reverse=True)
    return result