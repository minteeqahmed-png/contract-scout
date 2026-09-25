import os
import uuid
import json
import tempfile
import logging
from fastapi import FastAPI, UploadFile, HTTPException
from fastapi.responses import Response, FileResponse
from fastapi.staticfiles import StaticFiles
from .parser import extract_document, render_page_image
from .indexer import Indexer
from .auditor import run_audit_pipeline, ContractAuditReport
from .docx_generator import generate_redline_docx

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

@app.middleware("http")
async def add_security_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Content-Security-Policy"] = "default-src 'self' cdn.tailwindcss.com unpkg.com; img-src 'self' data:;"
    return response

# In-memory cache: ONLY reliable with a single worker
reports_cache = {}
pdfs_cache = {}

with open("config/compliance_playbook.json", "r") as f:
    playbook = json.load(f)

@app.post("/api/audit", response_model=ContractAuditReport)
async def audit_endpoint(file: UploadFile):
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Invalid file type. Only PDF files are allowed.")
        
    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File too large. Maximum size is 10MB.")
        
    report_id = str(uuid.uuid4())
    
    # Save temp pdf
    pdf_path = os.path.join(tempfile.gettempdir(), f"{report_id}.pdf")
    with open(pdf_path, "wb") as f:
        f.write(content)
        
    try:
        clauses, page_count = extract_document(pdf_path)
        indexer = Indexer()
        indexer.index(clauses)
        
        report = await run_audit_pipeline(report_id, playbook, clauses, page_count, indexer)
        
        reports_cache[report_id] = report
        pdfs_cache[report_id] = pdf_path
        
        return report
    except Exception as e:
        logger.error(f"Error auditing contract: {str(e)}")
        raise HTTPException(status_code=400, detail="Failed to process the contract. Please ensure it is a valid PDF.")

@app.get("/api/page/{report_id}/{page_num}")
async def get_page_image(report_id: str, page_num: int):
    if report_id not in pdfs_cache:
        raise HTTPException(status_code=404, detail="Report not found")
    try:
        img_bytes = render_page_image(pdfs_cache[report_id], page_num)
        return Response(content=img_bytes, media_type="image/png")
    except Exception as e:
        logger.error(f"Error generating page image: {str(e)}")
        raise HTTPException(status_code=400, detail="Failed to render page image.")

@app.get("/api/export/docx/{report_id}")
async def export_docx(report_id: str):
    if report_id not in reports_cache:
        raise HTTPException(status_code=404, detail="Report not found")
    report = reports_cache[report_id]
    docx_bytes = generate_redline_docx(report)
    
    return Response(
        content=docx_bytes, 
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f"attachment; filename=audit_{report_id}.docx"}
    )

app.mount("/", StaticFiles(directory="static", html=True), name="static")
