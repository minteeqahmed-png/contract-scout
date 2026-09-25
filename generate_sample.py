from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import sys

def create_sample_contract(filename):
    c = canvas.Canvas(filename, pagesize=letter)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(100, 750, "SOFTWARE AS A SERVICE (SaaS) AGREEMENT")
    
    c.setFont("Helvetica", 12)
    c.drawString(100, 710, "Total Contract Value: $500,000.00")
    
    c.drawString(100, 670, "1. Payment Terms:")
    c.drawString(100, 650, "Client agrees to pay all undisputed invoices within fifteen (15) days of receipt.") # VIOLATION (Net 15)
    
    c.drawString(100, 610, "2. Limitation of Liability:")
    c.drawString(100, 590, "IN NO EVENT SHALL VENDOR'S LIABILITY EXCEED $1,000,000.") # VIOLATION (Cap > Contract Value)
    
    c.drawString(100, 550, "3. Governing Law:")
    c.drawString(100, 530, "This Agreement shall be governed by the laws of the State of California.") # VIOLATION (Playbook wants Delaware)
    
    c.drawString(100, 490, "4. Security:")
    c.drawString(100, 470, "Vendor ensures standard protections. No specific web vulnerabilities are addressed.") # VIOLATION (Missing new web security reqs)
    
    c.save()

if __name__ == "__main__":
    create_sample_contract("sample_contract.pdf")
    print("Created sample_contract.pdf")
