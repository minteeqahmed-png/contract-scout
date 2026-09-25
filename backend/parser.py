import io
import re
import pdfplumber

def extract_document(pdf_path: str) -> tuple[list[dict], int]:
    """Extracts clauses with normalized bounding boxes from a PDF."""
    clauses = []
    total_text_len = 0
    page_count = 0
    
    with pdfplumber.open(pdf_path) as pdf:
        page_count = len(pdf.pages)
        for i, page in enumerate(pdf.pages):
            words = page.extract_words(use_text_flow=True)
            if not words:
                continue
            
            # Using extract_words and lines heuristic
            # Simpler line extraction since extract_text_lines isn't always reliable
            # For this simplified version, let's just group words by approx vertical position
            
            lines = []
            # Group words by approx top coordinate (within 2 pts)
            words.sort(key=lambda w: (w["top"], w["x0"]))
            current_line = []
            for w in words:
                if not current_line:
                    current_line.append(w)
                elif abs(w["top"] - current_line[-1]["top"]) < 4:
                    current_line.append(w)
                else:
                    lines.append(current_line)
                    current_line = [w]
            if current_line:
                lines.append(current_line)
                
            if not lines:
                continue
                
            # Compute median inter-line gap
            gaps = []
            for j in range(1, len(lines)):
                gaps.append(lines[j][0]["top"] - lines[j-1][0]["bottom"])
            gaps.sort()
            median_gap = gaps[len(gaps)//2] if gaps else 0
            
            # Group lines into clauses
            clauses_in_page = []
            current_clause_lines = [lines[0]]
            
            for j in range(1, len(lines)):
                line = lines[j]
                prev_line = lines[j-1]
                gap = line[0]["top"] - prev_line[0]["bottom"]
                line_text = " ".join(w["text"] for w in line)
                
                starts_with_marker = bool(re.match(r'^(\d+(\.\d+)*\.?\s|[A-Z]\.\s|\(\w+\)\s)', line_text))
                
                if gap > 1.5 * median_gap or starts_with_marker:
                    clauses_in_page.append(current_clause_lines)
                    current_clause_lines = [line]
                else:
                    current_clause_lines.append(line)
            
            if current_clause_lines:
                clauses_in_page.append(current_clause_lines)
                
            for c_lines in clauses_in_page:
                text = " ".join(" ".join(w["text"] for w in l) for l in c_lines)
                total_text_len += len(text)
                
                x0 = min(w["x0"] for l in c_lines for w in l)
                top = min(w["top"] for l in c_lines for w in l)
                x1 = max(w["x1"] for l in c_lines for w in l)
                bottom = max(w["bottom"] for l in c_lines for w in l)
                
                width = page.width
                height = page.height
                
                clauses.append({
                    "text": text,
                    "bbox": {
                        "page_number": i + 1,
                        "left_pct": float((x0 / width) * 100),
                        "top_pct": float((top / height) * 100),
                        "width_pct": float(((x1 - x0) / width) * 100),
                        "height_pct": float(((bottom - top) / height) * 100)
                    }
                })
                
    if total_text_len < 100:
        raise ValueError("Error: PDF contains < 100 chars. OCR is required for scanned documents (un-OCR'd or empty PDF detected).")
        
    return clauses, page_count

def render_page_image(pdf_path: str, page_number: int) -> bytes:
    """Rasterizes a single page of the PDF to a PNG byte array."""
    buffer = io.BytesIO()
    with pdfplumber.open(pdf_path) as pdf:
        if page_number < 1 or page_number > len(pdf.pages):
            raise ValueError(f"Invalid page number {page_number}")
        page = pdf.pages[page_number - 1]
        img = page.to_image(resolution=150).original
        img.save(buffer, format="PNG")
    return buffer.getvalue()
