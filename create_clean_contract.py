from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

def create_pdf(filename="clean_contract.pdf"):
    doc = SimpleDocTemplate(filename, pagesize=letter)
    styles = getSampleStyleSheet()
    
    # Create custom styles
    title_style = styles['Heading1']
    title_style.alignment = 1 # Center
    
    body_style = styles['Normal']
    body_style.spaceAfter = 12
    body_style.leading = 14

    story = []
    
    # Title
    story.append(Paragraph("Software Licensing Agreement", title_style))
    story.append(Spacer(1, 12))
    
    # Preamble
    story.append(Paragraph("This Software Licensing Agreement (the \"Agreement\") is entered into by and between the Licensor and the Licensee. Both parties agree to the following mutually beneficial terms:", body_style))
    
    # Clauses designed to pass compliance audits
    clauses = [
        "1. Standard Limitation of Liability: The total liability of the Licensor for any claims arising out of this Agreement shall not exceed the total fees paid by the Licensee in the twelve (12) months preceding the claim. This limitation applies to all damages, including direct, indirect, and consequential damages.",
        "2. Termination for Convenience: Either party may terminate this Agreement at any time, for any reason, by providing thirty (30) days prior written notice to the other party. Upon termination, Licensee will receive a pro-rata refund of any prepaid fees for unused services.",
        "3. Mutual Indemnification: Each party agrees to indemnify, defend, and hold harmless the other party against any claims, losses, or damages arising out of the indemnifying party's gross negligence, willful misconduct, or violation of applicable laws.",
        "4. Non-Compete Exemption: The Licensee is completely free to develop, market, or use any competing software or services during and after the term of this Agreement. There are no non-compete restrictions placed upon the Licensee.",
        "5. Favorable Payment Terms: Licensee agrees to pay all undisputed invoices within sixty (60) days of receipt. No late fees or interest shall accrue on payments during this period.",
        "6. Auto-Renewal Opt-In: This Agreement shall not automatically renew. Any renewal of this Agreement must be agreed upon in writing by both parties at least fifteen (15) days prior to the expiration of the current term.",
        "7. Governing Law: This Agreement shall be governed by and construed in accordance with the standard commercial laws applicable in the Licensee's primary jurisdiction, ensuring fair representation for both parties."
    ]
    
    for clause in clauses:
        story.append(Paragraph(clause, body_style))
        
    # Signatures
    story.append(Spacer(1, 24))
    story.append(Paragraph("IN WITNESS WHEREOF, the parties hereto have executed this Agreement.", body_style))
    story.append(Spacer(1, 24))
    story.append(Paragraph("Licensor: _________________________    Licensee: _________________________", body_style))
    
    doc.build(story)
    print(f"Successfully generated {filename}")

if __name__ == "__main__":
    create_pdf()
