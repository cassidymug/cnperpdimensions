from io import BytesIO
from typing import Dict, Any, List, Optional
from datetime import date, datetime
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from app.core.config import settings
import os, base64

FALLBACK_LOGO_BASE64 = "iVBORw0KGgoAAAANSUhEUgAAAEAAAABACAQAAAAAYLlVAAAAC0lEQVR42mP8/5+hHgAHggN4Vf6kZQAAAABJRU5ErkJggg=="
COPYRIGHT_LINE = "COMPUTING NETWORKING PRINTING SOLUTIONS PTY LTD TEL 74818826 77122880 BOTSWANA"

def _load_logo_bytes(path: Optional[str]) -> Optional[bytes]:
    if path and os.path.exists(path):
        try:
            with open(path, 'rb') as f:
                return f.read()
        except Exception:
            return None
    try:
        return base64.b64decode(FALLBACK_LOGO_BASE64)
    except Exception:
        return None

def build_pdf_header_footer(c: canvas.Canvas, margin: float, width: float, footer_brand_text: str):
    c.setStrokeColor(colors.lightgrey)
    c.setLineWidth(0.5)
    c.line(margin, 18*mm, width - margin, 18*mm)
    c.setFont("Helvetica", 7)
    c.setFillColor(colors.grey)
    c.drawString(margin, 14*mm, f"{footer_brand_text} • {COPYRIGHT_LINE}")
    c.drawRightString(width - margin, 14*mm, f"Page {c.getPageNumber()}")

def render_watermark(c: canvas.Canvas, text: str, width: float, height: float):
    c.saveState()
    c.setFillColor(colors.lightgrey)
    c.setFont("Helvetica-Bold", 60)
    c.translate(width/2, height/2)
    c.rotate(45)
    c.drawCentredString(0, 0, text[:40])
    c.restoreState()

def export_simple_table_pdf(title: str, period: Dict[str,str], columns: List[str], rows: List[List[Any]],
                            include_logo=True, include_watermark=True, watermark_text: Optional[str]=None) -> BytesIO:
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    margin = 25 * mm
    y = height - margin
    logo_bytes = _load_logo_bytes(settings.brand_logo_path if include_logo else None)
    wm_text = watermark_text or settings.brand_watermark_text

    # Header
    c.setFont("Helvetica-Bold", 12)
    c.setFillColor(colors.HexColor('#0d6efd'))
    c.drawString(margin, y, settings.brand_header_text)
    y -= 14
    c.setFillColor(colors.black)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(margin, y, title)
    y -= 14
    c.setFont("Helvetica", 9)
    c.setFillColor(colors.grey)
    c.drawString(margin, y, f"Period: {period.get('start','')} to {period.get('end','')}")
    y -= 12
    c.drawString(margin, y, f"Generated: {datetime.utcnow().isoformat(timespec='seconds')}Z")
    c.setFillColor(colors.black)
    y -= 18

    # Logo
    if include_logo and logo_bytes:
        try:
            img = ImageReader(BytesIO(logo_bytes))
            c.drawImage(img, width - margin - 40*mm, height - margin - 22*mm, width=35*mm, preserveAspectRatio=True, mask='auto')
        except Exception:
            pass

    if include_watermark:
        try:
            render_watermark(c, wm_text, width, height)
        except Exception:
            pass

    # Table
    col_widths = []
    total_table_width = width - 2*margin - 4
    equal = total_table_width / len(columns)
    col_widths = [equal]*len(columns)
    headers = columns
    def draw_header(y_pos):
        c.setFillColor(colors.lightgrey)
        c.rect(margin-2, y_pos-10, total_table_width+4, 12, fill=1, stroke=0)
        c.setFillColor(colors.black)
        c.setFont("Helvetica", 8)
        x = margin
        for i,h in enumerate(headers):
            c.drawString(x, y_pos, h)
            x += col_widths[i]

    draw_header(y)
    y -= 14
    c.setFont("Helvetica", 8)
    for row in rows:
        if y < 30*mm:
            build_pdf_header_footer(c, margin, width, settings.brand_footer_text)
            c.showPage()
            y = height - margin
            draw_header(y)
            y -= 14
        x = margin
        for i, cell in enumerate(row):
            txt = str(cell)[:40]
            c.drawString(x, y, txt)
            x += col_widths[i]
        y -= 12

    build_pdf_header_footer(c, margin, width, settings.brand_footer_text)
    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer

def flatten_dict(obj: Dict[str, Any], parent: str = "", rows: Optional[List[List[str]]] = None, max_depth: int = 2) -> List[List[str]]:
    if rows is None:
        rows = []
    if max_depth < 0:
        return rows
    for k, v in obj.items():
        key_path = f"{parent}{k}" if not parent else f"{parent}.{k}"
        if isinstance(v, dict) and max_depth > 0:
            flatten_dict(v, key_path, rows, max_depth-1)
        elif isinstance(v, (list, tuple)):
            # summarize list length only
            rows.append([key_path, f"list[{len(v)}]"])
        else:
            try:
                if isinstance(v, (int, float)):
                    rows.append([key_path, f"{v:,.2f}"])
                else:
                    rows.append([key_path, str(v)])
            except Exception:
                rows.append([key_path, str(v)])
    return rows

def export_key_value_pdf(title: str, period: Dict[str,str], data: Dict[str, Any], include_logo=True, include_watermark=True, watermark_text: Optional[str]=None) -> BytesIO:
    kv_rows = flatten_dict(data, max_depth=2)
    return export_simple_table_pdf(title, period, ["Key","Value"], kv_rows, include_logo=include_logo, include_watermark=include_watermark, watermark_text=watermark_text)

def period_for_point(as_of: date) -> Dict[str,str]:
    d = as_of.isoformat()
    return {"start": d, "end": d}

def export_trial_balance_rows(rows: List[dict]) -> List[List[Any]]:
    out = []
    for r in rows:
        out.append([r.get('code'), r.get('name'), r.get('type'), f"{r.get('debit',0):,.2f}", f"{r.get('credit',0):,.2f}"])
    return out
