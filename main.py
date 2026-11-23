
import json

from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from PIL import Image
from io import BytesIO
from pathlib import Path
from uuid import uuid4
from datetime import datetime, timezone
from fastapi.responses import FileResponse

from database import SessionLocal, Assessment
from ai_model import analyze_image as run_ai_analysis
from assessment_report import create_assessment_report


# =====================================
# AIDWINGS SETTINGS
# =====================================

app = FastAPI(title="AidWings API")

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

MAX_IMAGE_SIZE = 10 * 1024 * 1024

ALLOWED_FORMATS = {
    "JPEG": ".jpg",
    "PNG": ".png",
    "WEBP": ".webp"
}

ALLOWED_CATEGORIES = {
    "blockedaccessroute": "Blocked access route",
    "damagedinfrastructure": "Damaged infrastructure",
    "supplyshortage": "Supply shortage",
    "other": "Other"
}


# =====================================
# CATEGORY VALIDATION
# =====================================

def normalize_category(category):
    return (
        category.strip()
        .lower()
        .replace(" ", "")
        .replace("_", "")
        .replace("-", "")
    )


# =====================================
# IMAGE VALIDATION
# =====================================

def validate_image(data):

    try:
        image = Image.open(BytesIO(data))
        image.verify()

        image = Image.open(BytesIO(data))

        image_format = image.format
        width, height = image.size

        if image_format not in ALLOWED_FORMATS:
            raise HTTPException(
                status_code=400,
                detail="Unsupported image format."
            )

        return image_format, width, height

    except HTTPException:
        raise

    except Exception:
        raise HTTPException(
            status_code=400,
            detail="Invalid image."
        )


# =====================================
# HOME
# =====================================

@app.get("/")
def home():
    return {
        "project": "AidWings",
        "status": "Running",
        "message": "Welcome to AidWings API"
    }


# =====================================
# HEALTH CHECK
# =====================================

@app.get("/health")
def health():
    return {
        "status": "healthy"
    }


# =====================================
# RECEIVE IMAGE
# =====================================

@app.post("/images")
async def receive_image(file: UploadFile = File(...)):

    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(400, "Please upload an image.")

    data = await file.read(MAX_IMAGE_SIZE + 1)

    if len(data) > MAX_IMAGE_SIZE:
        raise HTTPException(413, "Image is too large.")

    image_format, width, height = validate_image(data)

    image_id = str(uuid4())

    image_path = UPLOAD_DIR / (
        image_id + ALLOWED_FORMATS[image_format]
    )

    image_path.write_bytes(data)

    return {
        "project": "AidWings",
        "message": "Image received successfully!",
        "image_id": image_id,
        "format": image_format
    }


# =====================================
# BASIC IMAGE ANALYSIS
# =====================================

@app.post("/analyze-image")
async def analyze_image(file: UploadFile = File(...)):

    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(400, "Please upload an image.")

    data = await file.read(MAX_IMAGE_SIZE + 1)

    if len(data) > MAX_IMAGE_SIZE:
        raise HTTPException(413, "Image is too large.")

    image_format, width, height = validate_image(data)

    # Convert uploaded image into a format the AI model can read
    image = Image.open(BytesIO(data)).convert("RGB")

    # Run the pretrained image-classification model
    ai_results = run_ai_analysis(image)

    return {
        "project": "AidWings",
        "image_status": "Valid",
        "image_format": image_format,
        "width": width,
        "height": height,
        "ai_analysis": ai_results,
        "review_status": "Pending human review"
    }


# =====================================
# SUBMIT HUMANITARIAN ASSESSMENT
# =====================================

@app.post("/aid-assessment")
async def aid_assessment(
    file: UploadFile = File(...),
    location: str = Form(...),
    description: str = Form(""),
    category: str = Form(...)
):

    # Check location
    if not location.strip():
        raise HTTPException(400, "Location is required.")

    # Check category
    category_key = normalize_category(category)

    if category_key not in ALLOWED_CATEGORIES:
        raise HTTPException(
            status_code=400,
            detail={
                "message": "Invalid humanitarian category.",
                "allowed_categories": list(
                    ALLOWED_CATEGORIES.values()
                ),
                "received_category": category
            }
        )

    category = ALLOWED_CATEGORIES[category_key]

    # Check image
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(400, "Please upload an image.")

    data = await file.read(MAX_IMAGE_SIZE + 1)

    if len(data) > MAX_IMAGE_SIZE:
        raise HTTPException(413, "Image is too large.")

    image_format, width, height = validate_image(data)

    # Create assessment ID
    assessment_id = str(uuid4())

    image_path = UPLOAD_DIR / (
        assessment_id + ALLOWED_FORMATS[image_format]
    )

    image_path.write_bytes(data)

    # NEW: Run image classification
    image = Image.open(BytesIO(data)).convert("RGB")
    ai_results = run_ai_analysis(image)

    # NEW: Generate complete assessment report
    report = create_assessment_report(
        assessment_id=assessment_id,
        location=location.strip(),
        description=description,
        category=category,
        image_analysis=ai_results
    )

    # NEW: Convert report into JSON for permanent storage
    report_json = json.dumps(report, ensure_ascii=False)

    timestamp = datetime.now(timezone.utc).isoformat()

    # Save assessment in database
    db = SessionLocal()

    try:
        new_assessment = Assessment(
            id=assessment_id,
            location=location.strip(),
            description=description,
            category=category,
            image_path=str(image_path),
            timestamp=timestamp,
            review_status="Pending human review",

            # NEW: Save complete AI report
            report_json=report_json
        )

        db.add(new_assessment)
        db.commit()

    except Exception as e:
        db.rollback()

        print("DATABASE SAVE ERROR:", repr(e))

        raise HTTPException(
            status_code=500,
            detail="Database could not save the assessment. Check VS Code terminal."
        )

    finally:
        db.close()

    return {
        "project": "AidWings",
        "message": "Assessment submitted successfully!",
        "assessment_id": assessment_id,
        "timestamp": timestamp,
        "location": location.strip(),
        "description": description,
        "category": category,
        "image_status": "Received",
        "image_width": width,
        "image_height": height,
        "review_status": "Pending human review",

        # NEW: Return generated AI report
        "report": report
    }


# =====================================
# VIEW ALL ASSESSMENTS
# =====================================

@app.get("/assessments")
def get_assessments():

    db = SessionLocal()

    try:
        assessments = db.query(Assessment).all()

        results = []

        for assessment in assessments:
            results.append({
                "id": assessment.id,
                "location": assessment.location,
                "description": assessment.description,
                "category": assessment.category,
                "image_path": assessment.image_path,
                "timestamp": assessment.timestamp,
                "review_status": assessment.review_status
            })

        return {
            "project": "AidWings",
            "total_assessments": len(results),
            "assessments": results
        }

    finally:
        db.close()


# =====================================
# FILTER ASSESSMENTS BY CATEGORY
# =====================================

@app.get("/assessments/category/{category}")
def get_assessments_by_category(category: str):

    category_key = normalize_category(category)

    if category_key not in ALLOWED_CATEGORIES:
        raise HTTPException(
            status_code=400,
            detail="Invalid category."
        )

    category = ALLOWED_CATEGORIES[category_key]

    db = SessionLocal()

    try:
        assessments = (
            db.query(Assessment)
            .filter(Assessment.category == category)
            .all()
        )

        results = []

        for assessment in assessments:
            results.append({
                "id": assessment.id,
                "location": assessment.location,
                "description": assessment.description,
                "category": assessment.category,
                "timestamp": assessment.timestamp,
                "review_status": assessment.review_status
            })

        return {
            "project": "AidWings",
            "category": category,
            "total_assessments": len(results),
            "assessments": results
        }

    finally:
        db.close()


# =====================================
# VIEW AN ASSESSMENT IMAGE
# =====================================

@app.get("/assessment-image/{assessment_id}")
def get_assessment_image(assessment_id: str):

    db = SessionLocal()

    try:
        assessment = (
            db.query(Assessment)
            .filter(Assessment.id == assessment_id)
            .first()
        )

        if not assessment:
            raise HTTPException(
                status_code=404,
                detail="Assessment not found."
            )

        image_path = Path(assessment.image_path)

        if not image_path.is_file():
            raise HTTPException(
                status_code=404,
                detail="Image file not found."
            )

        return FileResponse(image_path)

    finally:
        db.close()


# =====================================
# NEW: VIEW SAVED AI REPORT
# =====================================

@app.get("/assessment-report/{assessment_id}")
def get_assessment_report(assessment_id: str):

    db = SessionLocal()

    try:
        assessment = (
            db.query(Assessment)
            .filter(Assessment.id == assessment_id)
            .first()
        )

        if not assessment:
            raise HTTPException(
                status_code=404,
                detail="Assessment not found."
            )

        if not assessment.report_json:
            raise HTTPException(
                status_code=404,
                detail="No saved AI report exists for this assessment."
            )

        return json.loads(assessment.report_json)

    finally:
        db.close()
