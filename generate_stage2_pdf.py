"""
Generate MODIFIED HR_Policy.pdf for Stage 2 testing.
3 changes from original:
  1. Remote work: 2 days → 3 days per week
  2. Sick leave: 12 days → 15 days per year
  3. Leave carryover: 10 days → 5 days max
"""
import os
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.colors import HexColor
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY

OUTPUT_DIR = "temp_doc/stage2"
os.makedirs(OUTPUT_DIR, exist_ok=True)

styles = getSampleStyleSheet()
title_style = ParagraphStyle('DocTitle', parent=styles['Title'], fontSize=22, spaceAfter=6, textColor=HexColor('#1a365d'), fontName='Helvetica-Bold')
company_style = ParagraphStyle('Company', parent=styles['Normal'], fontSize=11, textColor=HexColor('#4a5568'), alignment=TA_CENTER, spaceAfter=20)
section_style = ParagraphStyle('SectionHead', parent=styles['Heading2'], fontSize=14, textColor=HexColor('#2d3748'), spaceBefore=16, spaceAfter=8, fontName='Helvetica-Bold')
subsection_style = ParagraphStyle('SubSection', parent=styles['Heading3'], fontSize=12, textColor=HexColor('#4a5568'), spaceBefore=10, spaceAfter=6, fontName='Helvetica-Bold')
body_style = ParagraphStyle('Body', parent=styles['Normal'], fontSize=10.5, leading=15, alignment=TA_JUSTIFY, spaceAfter=8, textColor=HexColor('#2d3748'))
clause_style = ParagraphStyle('Clause', parent=body_style, leftIndent=20, bulletIndent=10, spaceAfter=6)

def header_block(title, doc_id, effective_date, department):
    return [
        Paragraph("TECHCORP INC.", company_style),
        Paragraph("━" * 60, ParagraphStyle('Line', fontSize=6, textColor=HexColor('#cbd5e0'), alignment=TA_CENTER)),
        Spacer(1, 10),
        Paragraph(title, title_style),
        Spacer(1, 6),
        Paragraph(f"Document ID: {doc_id} &nbsp;&nbsp;|&nbsp;&nbsp; Department: {department} &nbsp;&nbsp;|&nbsp;&nbsp; Effective: {effective_date}",
                  ParagraphStyle('Meta', parent=styles['Normal'], fontSize=9, textColor=HexColor('#718096'), alignment=TA_CENTER)),
        Paragraph(f"Classification: INTERNAL &nbsp;&nbsp;|&nbsp;&nbsp; Version: 2.0 &nbsp;&nbsp;|&nbsp;&nbsp; Updated: June 2026",
                  ParagraphStyle('Meta2', parent=styles['Normal'], fontSize=9, textColor=HexColor('#718096'), alignment=TA_CENTER, spaceAfter=16)),
        HRFlowable(width="100%", thickness=1, color=HexColor('#e2e8f0')),
        Spacer(1, 12),
    ]

doc = SimpleDocTemplate(os.path.join(OUTPUT_DIR, "HR_Policy.pdf"), pagesize=A4,
                        topMargin=1.5*cm, bottomMargin=1.5*cm, leftMargin=2*cm, rightMargin=2*cm)
story = header_block("Human Resources Policy Manual", "HR-2026-001", "June 15, 2026", "Human Resources")

# Section 1: Leave Policy
story.append(Paragraph("1. Leave and Time-Off Policy", section_style))
story.append(Paragraph(
    "TechCorp Inc. provides a comprehensive leave program to support employee well-being and work-life balance. "
    "All full-time employees are eligible for the following leave benefits upon completion of their probationary period (90 days).",
    body_style))

story.append(Paragraph("1.1 Annual Leave (Paid Time Off)", subsection_style))
story.append(Paragraph("All full-time employees are entitled to <b>24 days</b> of paid annual leave per calendar year.", clause_style))
story.append(Paragraph("Leave accrues at a rate of 2 days per month of continuous service.", clause_style))
# ═══ CHANGE 3: Carryover changed to 6 days ═══
story.append(Paragraph("A maximum of <b>6 days</b> of unused leave may be carried over to the next calendar year. Any excess will be forfeited.", clause_style))
story.append(Paragraph("Leave requests must be submitted at least <b>5 business days</b> in advance through the HR portal.", clause_style))
story.append(Paragraph("Managers must approve or deny leave requests within 2 business days.", clause_style))

story.append(Paragraph("1.2 Sick Leave", subsection_style))
# ═══ CHANGE 2: Sick leave changed to 16 days ═══
story.append(Paragraph("Employees are entitled to <b>16 days</b> of paid sick leave per year.", clause_style))
story.append(Paragraph("Sick leave exceeding <b>3 consecutive days</b> requires a medical certificate from a licensed physician.", clause_style))
story.append(Paragraph("Unused sick leave does not carry over and cannot be encashed.", clause_style))

story.append(Paragraph("1.3 Parental Leave", subsection_style))
story.append(Paragraph("Primary caregivers are entitled to <b>16 weeks</b> of paid parental leave.", clause_style))
story.append(Paragraph("Secondary caregivers are entitled to <b>4 weeks</b> of paid parental leave.", clause_style))
story.append(Paragraph("Parental leave may be taken within 12 months of the child's birth or adoption date.", clause_style))

# Section 2: Remote Work
story.append(Paragraph("2. Remote Work Policy", section_style))
story.append(Paragraph(
    "TechCorp supports flexible work arrangements. The following guidelines govern remote work eligibility and requirements.",
    body_style))

story.append(Paragraph("2.1 Eligibility and Schedule", subsection_style))
story.append(Paragraph("All full-time employees who have completed their probationary period are eligible for remote work.", clause_style))
# ═══ CHANGE 1: Remote work reduced to 1 day ═══
story.append(Paragraph("Employees may work remotely for a maximum of <b>1 day per week</b>.", clause_style))
story.append(Paragraph("Remote work days must be pre-approved by the employee's direct manager.", clause_style))
story.append(Paragraph("Employees must be available during core business hours (<b>10:00 AM - 4:00 PM</b>) regardless of work location.", clause_style))

story.append(Paragraph("2.2 Remote Work Requirements", subsection_style))
story.append(Paragraph("Employees must have a stable internet connection with minimum 25 Mbps download speed.", clause_style))
story.append(Paragraph("All work must be performed using company-issued devices only.", clause_style))
story.append(Paragraph("VPN must be connected at all times when accessing company systems remotely.", clause_style))
story.append(Paragraph("Employees working remotely must maintain a dedicated, private workspace.", clause_style))

# Section 3: Office Hours & Conduct
story.append(Paragraph("3. Office Hours and Professional Conduct", section_style))
story.append(Paragraph("3.1 Standard Work Hours", subsection_style))
story.append(Paragraph("Standard office hours are <b>9:00 AM to 6:00 PM</b>, Monday through Friday.", clause_style))
story.append(Paragraph("A one-hour lunch break is provided between 12:30 PM and 1:30 PM.", clause_style))
story.append(Paragraph("Employees are expected to maintain a minimum of <b>40 hours</b> per work week.", clause_style))

story.append(Paragraph("3.2 Dress Code", subsection_style))
story.append(Paragraph("Business casual attire is required on all office days.", clause_style))
story.append(Paragraph("Fridays are designated as casual dress days.", clause_style))

story.append(Paragraph("3.3 Performance Reviews", subsection_style))
story.append(Paragraph("Annual performance reviews are conducted in <b>March</b> of each year.", clause_style))
story.append(Paragraph("Mid-year check-ins are conducted in September.", clause_style))
story.append(Paragraph("Performance ratings directly impact annual bonus calculations and promotion eligibility.", clause_style))

doc.build(story)
print(f"DONE - Modified HR_Policy.pdf saved to: {os.path.abspath(OUTPUT_DIR)}")
print("\n3 CHANGES FROM ORIGINAL:")
print("  1. Remote work: 2 days/week -> 3 days/week")
print("  2. Sick leave: 12 days/year -> 15 days/year")
print("  3. Leave carryover: 10 days max -> 5 days max")
