import os
import json
import pytest
import asyncio
from reportlab.pdfgen import canvas
from backend.parser import extract_document
from backend.indexer import Indexer
from backend.auditor import run_audit_pipeline
from backend.docx_generator import generate_redline_docx

@pytest.fixture
def synthetic_pdf(tmp_path):
    pdf_path = str(tmp_path / "test_contract.pdf")
    c = canvas.Canvas(pdf_path)
    
    c.drawString(100, 800, "1. Contract Title: Software Services Agreement")
    c.drawString(100, 780, "2. Total Contract Value is $500,000.")
    c.drawString(100, 760, "3. Liability Cap:")
    c.drawString(100, 740, "Vendor liability shall not be capped or limited in any manner.")
    
    c.showPage()
    
    c.drawString(100, 800, "4. Payment Terms:")
    c.drawString(100, 780, "Payment due within Net 10 days; 5% interest per week applies.")
    
    c.save()
    return pdf_path

@pytest.mark.asyncio
async def test_audit_pipeline(synthetic_pdf):
    with open("config/compliance_playbook.json", "r") as f:
        playbook = json.load(f)
        
    clauses, page_count = extract_document(synthetic_pdf)
    
    for clause in clauses:
        bbox = clause["bbox"]
        assert 0 <= bbox["left_pct"] <= 100
        assert 0 <= bbox["top_pct"] <= 100
        assert 0 <= bbox["width_pct"] <= 100
        assert 0 <= bbox["height_pct"] <= 100
        
    indexer = Indexer()
    indexer.index(clauses)
    
    report = await run_audit_pipeline("test_report", playbook, clauses, page_count, indexer)
    
    assert report.has_unlimited_exposure is True
    assert report.total_financial_exposure == "UNLIMITED EXPOSURE (Catastrophic)"
    
    liability_res = next(r for r in report.results if r.rule_name == "Liability Cap")
    assert liability_res.is_unlimited_exposure is True
    assert liability_res.status in ("FAIL", "RISK")
    
    gov_law_res = next(r for r in report.results if r.rule_name == "Governing Law & Jurisdiction")
    assert gov_law_res.original_clause is None
    assert gov_law_res.status == "FAIL"
    
    docx_bytes = generate_redline_docx(report)
    assert len(docx_bytes) > 0
