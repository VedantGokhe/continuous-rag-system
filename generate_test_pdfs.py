"""
Generate professional enterprise policy PDFs for testing Continuous-RAG.
Stage 1: Initial document set (4 policy documents from different departments)
"""
import os
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch, cm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.colors import HexColor
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY

OUTPUT_DIR = "temp_doc"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Common styles
styles = getSampleStyleSheet()

title_style = ParagraphStyle(
    'DocTitle', parent=styles['Title'],
    fontSize=22, spaceAfter=6, textColor=HexColor('#1a365d'),
    fontName='Helvetica-Bold'
)
company_style = ParagraphStyle(
    'Company', parent=styles['Normal'],
    fontSize=11, textColor=HexColor('#4a5568'), alignment=TA_CENTER,
    spaceAfter=20
)
section_style = ParagraphStyle(
    'SectionHead', parent=styles['Heading2'],
    fontSize=14, textColor=HexColor('#2d3748'), spaceBefore=16, spaceAfter=8,
    fontName='Helvetica-Bold'
)
subsection_style = ParagraphStyle(
    'SubSection', parent=styles['Heading3'],
    fontSize=12, textColor=HexColor('#4a5568'), spaceBefore=10, spaceAfter=6,
    fontName='Helvetica-Bold'
)
body_style = ParagraphStyle(
    'Body', parent=styles['Normal'],
    fontSize=10.5, leading=15, alignment=TA_JUSTIFY, spaceAfter=8,
    textColor=HexColor('#2d3748')
)
clause_style = ParagraphStyle(
    'Clause', parent=body_style,
    leftIndent=20, bulletIndent=10, spaceAfter=6
)

def header_block(title, doc_id, effective_date, department):
    return [
        Paragraph("TECHCORP INC.", company_style),
        Paragraph("━" * 60, ParagraphStyle('Line', fontSize=6, textColor=HexColor('#cbd5e0'), alignment=TA_CENTER)),
        Spacer(1, 10),
        Paragraph(title, title_style),
        Spacer(1, 6),
        Paragraph(f"Document ID: {doc_id} &nbsp;&nbsp;|&nbsp;&nbsp; Department: {department} &nbsp;&nbsp;|&nbsp;&nbsp; Effective: {effective_date}", 
                  ParagraphStyle('Meta', parent=styles['Normal'], fontSize=9, textColor=HexColor('#718096'), alignment=TA_CENTER)),
        Paragraph(f"Classification: INTERNAL &nbsp;&nbsp;|&nbsp;&nbsp; Version: 1.0", 
                  ParagraphStyle('Meta2', parent=styles['Normal'], fontSize=9, textColor=HexColor('#718096'), alignment=TA_CENTER, spaceAfter=16)),
        HRFlowable(width="100%", thickness=1, color=HexColor('#e2e8f0')),
        Spacer(1, 12),
    ]


def create_hr_policy():
    """HR Policy — covers leave, remote work, office hours, conduct"""
    doc = SimpleDocTemplate(os.path.join(OUTPUT_DIR, "HR_Policy.pdf"), pagesize=A4,
                            topMargin=1.5*cm, bottomMargin=1.5*cm, leftMargin=2*cm, rightMargin=2*cm)
    story = header_block(
        "Human Resources Policy Manual",
        "HR-2026-001", "January 1, 2026", "Human Resources"
    )

    # Section 1: Leave Policy
    story.append(Paragraph("1. Leave and Time-Off Policy", section_style))
    story.append(Paragraph(
        "TechCorp Inc. provides a comprehensive leave program to support employee well-being and work-life balance. "
        "All full-time employees are eligible for the following leave benefits upon completion of their probationary period (90 days).",
        body_style))
    
    story.append(Paragraph("1.1 Annual Leave (Paid Time Off)", subsection_style))
    story.append(Paragraph("• All full-time employees are entitled to <b>24 days</b> of paid annual leave per calendar year.", clause_style))
    story.append(Paragraph("• Leave accrues at a rate of 2 days per month of continuous service.", clause_style))
    story.append(Paragraph("• A maximum of <b>10 days</b> of unused leave may be carried over to the next calendar year. Any excess will be forfeited.", clause_style))
    story.append(Paragraph("• Leave requests must be submitted at least <b>5 business days</b> in advance through the HR portal.", clause_style))
    story.append(Paragraph("• Managers must approve or deny leave requests within 2 business days.", clause_style))

    story.append(Paragraph("1.2 Sick Leave", subsection_style))
    story.append(Paragraph("• Employees are entitled to <b>12 days</b> of paid sick leave per year.", clause_style))
    story.append(Paragraph("• Sick leave exceeding <b>3 consecutive days</b> requires a medical certificate from a licensed physician.", clause_style))
    story.append(Paragraph("• Unused sick leave does not carry over and cannot be encashed.", clause_style))

    story.append(Paragraph("1.3 Parental Leave", subsection_style))
    story.append(Paragraph("• Primary caregivers are entitled to <b>16 weeks</b> of paid parental leave.", clause_style))
    story.append(Paragraph("• Secondary caregivers are entitled to <b>4 weeks</b> of paid parental leave.", clause_style))
    story.append(Paragraph("• Parental leave may be taken within 12 months of the child's birth or adoption date.", clause_style))

    # Section 2: Remote Work
    story.append(Paragraph("2. Remote Work Policy", section_style))
    story.append(Paragraph(
        "TechCorp supports flexible work arrangements. The following guidelines govern remote work eligibility and requirements.",
        body_style))
    
    story.append(Paragraph("2.1 Eligibility and Schedule", subsection_style))
    story.append(Paragraph("• All full-time employees who have completed their probationary period are eligible for remote work.", clause_style))
    story.append(Paragraph("• Employees may work remotely for a maximum of <b>2 days per week</b>.", clause_style))
    story.append(Paragraph("• Remote work days must be pre-approved by the employee's direct manager.", clause_style))
    story.append(Paragraph("• Employees must be available during core business hours (<b>10:00 AM - 4:00 PM</b>) regardless of work location.", clause_style))

    story.append(Paragraph("2.2 Remote Work Requirements", subsection_style))
    story.append(Paragraph("• Employees must have a stable internet connection with minimum 25 Mbps download speed.", clause_style))
    story.append(Paragraph("• All work must be performed using company-issued devices only.", clause_style))
    story.append(Paragraph("• VPN must be connected at all times when accessing company systems remotely.", clause_style))
    story.append(Paragraph("• Employees working remotely must maintain a dedicated, private workspace.", clause_style))

    # Section 3: Office Hours & Conduct
    story.append(Paragraph("3. Office Hours and Professional Conduct", section_style))
    story.append(Paragraph("3.1 Standard Work Hours", subsection_style))
    story.append(Paragraph("• Standard office hours are <b>9:00 AM to 6:00 PM</b>, Monday through Friday.", clause_style))
    story.append(Paragraph("• A one-hour lunch break is provided between 12:30 PM and 1:30 PM.", clause_style))
    story.append(Paragraph("• Employees are expected to maintain a minimum of <b>40 hours</b> per work week.", clause_style))

    story.append(Paragraph("3.2 Dress Code", subsection_style))
    story.append(Paragraph("• Business casual attire is required on all office days.", clause_style))
    story.append(Paragraph("• Fridays are designated as casual dress days.", clause_style))

    story.append(Paragraph("3.3 Performance Reviews", subsection_style))
    story.append(Paragraph("• Annual performance reviews are conducted in <b>March</b> of each year.", clause_style))
    story.append(Paragraph("• Mid-year check-ins are conducted in September.", clause_style))
    story.append(Paragraph("• Performance ratings directly impact annual bonus calculations and promotion eligibility.", clause_style))

    doc.build(story)
    print(f"✓ Created: HR_Policy.pdf")


def create_finance_policy():
    """Finance Policy — covers expenses, travel budget, equipment"""
    doc = SimpleDocTemplate(os.path.join(OUTPUT_DIR, "Finance_Guidelines.pdf"), pagesize=A4,
                            topMargin=1.5*cm, bottomMargin=1.5*cm, leftMargin=2*cm, rightMargin=2*cm)
    story = header_block(
        "Finance and Expense Guidelines",
        "FIN-2026-003", "January 1, 2026", "Finance"
    )

    story.append(Paragraph("1. Expense Reimbursement Policy", section_style))
    story.append(Paragraph(
        "This section outlines the rules governing business expense reimbursement for all TechCorp employees. "
        "All expenses must be legitimate business costs and properly documented.",
        body_style))

    story.append(Paragraph("1.1 General Rules", subsection_style))
    story.append(Paragraph("• All expense claims must be submitted within <b>30 days</b> of the expense being incurred.", clause_style))
    story.append(Paragraph("• Original receipts or digital copies must accompany all claims exceeding $25.", clause_style))
    story.append(Paragraph("• Expenses above <b>$500</b> require pre-approval from the department head.", clause_style))
    story.append(Paragraph("• Expenses above <b>$5,000</b> require CFO approval.", clause_style))

    story.append(Paragraph("1.2 Meal and Entertainment", subsection_style))
    story.append(Paragraph("• Business meals with clients are reimbursable up to <b>$75 per person</b>.", clause_style))
    story.append(Paragraph("• Team lunch/dinner events are capped at <b>$50 per person</b>.", clause_style))
    story.append(Paragraph("• Alcohol is not reimbursable under any circumstances.", clause_style))

    story.append(Paragraph("1.3 Co-working Spaces", subsection_style))
    story.append(Paragraph("• Co-working space expenses are <b>NOT reimbursable</b>. Employees are expected to work from the office or their home office.", clause_style))
    story.append(Paragraph("• Exceptions may be granted for employees on extended business travel with written approval from their VP.", clause_style))

    story.append(Paragraph("2. Equipment and Technology Allowance", section_style))
    story.append(Paragraph("2.1 Standard Equipment", subsection_style))
    story.append(Paragraph("• All employees receive a company-issued laptop, monitor, keyboard, and mouse upon joining.", clause_style))
    story.append(Paragraph("• Equipment must be returned upon separation from the company.", clause_style))

    story.append(Paragraph("2.2 Home Office Allowance", subsection_style))
    story.append(Paragraph("• Employees approved for remote work receive a one-time <b>$500 home office setup allowance</b>.", clause_style))
    story.append(Paragraph("• An annual <b>$150 internet reimbursement</b> is provided for remote-eligible employees.", clause_style))
    story.append(Paragraph("• Ergonomic equipment (standing desk, chair) may be requested through the IT portal with manager approval.", clause_style))

    story.append(Paragraph("3. In-Office Attendance Requirements", section_style))
    story.append(Paragraph(
        "The Finance department has determined that effective collaboration and financial controls require a minimum "
        "level of in-person presence across all departments.",
        body_style))
    story.append(Paragraph("• All employees must be present in the office for a minimum of <b>4 days per week</b>.", clause_style))
    story.append(Paragraph("• Department heads may grant exceptions for up to 1 additional remote day per week based on role requirements.", clause_style))
    story.append(Paragraph("• Attendance is tracked through the building access card system and reported monthly.", clause_style))

    story.append(Paragraph("4. Travel Budget", section_style))
    story.append(Paragraph("4.1 Domestic Travel", subsection_style))
    story.append(Paragraph("• Economy class airfare for flights under 4 hours.", clause_style))
    story.append(Paragraph("• Hotel accommodations up to <b>$200 per night</b> for domestic travel.", clause_style))
    story.append(Paragraph("• Daily meal allowance of <b>$60</b> during business travel.", clause_style))

    story.append(Paragraph("4.2 International Travel", subsection_style))
    story.append(Paragraph("• All international travel requires <b>VP-level approval</b> at minimum.", clause_style))
    story.append(Paragraph("• Business class is permitted for flights exceeding 6 hours.", clause_style))
    story.append(Paragraph("• Hotel accommodations up to <b>$300 per night</b> for international travel.", clause_style))
    story.append(Paragraph("• International travel insurance is mandatory and provided by the company.", clause_style))

    doc.build(story)
    print(f"✓ Created: Finance_Guidelines.pdf")


def create_it_security_policy():
    """IT Security Policy — devices, AI tools, VPN, data handling"""
    doc = SimpleDocTemplate(os.path.join(OUTPUT_DIR, "IT_Security_Policy.pdf"), pagesize=A4,
                            topMargin=1.5*cm, bottomMargin=1.5*cm, leftMargin=2*cm, rightMargin=2*cm)
    story = header_block(
        "Information Technology & Security Policy",
        "IT-2026-002", "February 1, 2026", "Information Technology"
    )

    story.append(Paragraph("1. Device Usage Policy", section_style))
    story.append(Paragraph(
        "TechCorp provides all employees with company-managed devices. These guidelines ensure the security "
        "and integrity of company data and systems.",
        body_style))

    story.append(Paragraph("1.1 Company Devices", subsection_style))
    story.append(Paragraph("• Employees must use <b>company-issued devices only</b> for all work-related activities.", clause_style))
    story.append(Paragraph("• Personal software installation on company devices requires IT department approval.", clause_style))
    story.append(Paragraph("• Company devices must not be shared with family members or unauthorized individuals.", clause_style))
    story.append(Paragraph("• All devices must have full-disk encryption enabled at all times.", clause_style))

    story.append(Paragraph("1.2 Personal Device Policy (BYOD)", subsection_style))
    story.append(Paragraph("• <b>Personal devices are NOT permitted</b> for accessing company email, Slack, or internal systems.", clause_style))
    story.append(Paragraph("• Exception: Personal mobile phones may be used for two-factor authentication (2FA) only.", clause_style))
    story.append(Paragraph("• Employees found accessing company data on personal devices will face disciplinary action.", clause_style))

    story.append(Paragraph("2. Network and VPN Security", section_style))
    story.append(Paragraph("2.1 VPN Requirements", subsection_style))
    story.append(Paragraph("• All remote connections to company systems <b>must use the corporate VPN</b>.", clause_style))
    story.append(Paragraph("• VPN must be connected before accessing any internal tools, databases, or file shares.", clause_style))
    story.append(Paragraph("• Public Wi-Fi networks must never be used without VPN protection.", clause_style))

    story.append(Paragraph("2.2 Password Policy", subsection_style))
    story.append(Paragraph("• Passwords must be at least <b>14 characters</b> with uppercase, lowercase, numbers, and symbols.", clause_style))
    story.append(Paragraph("• Passwords must be changed every <b>90 days</b>.", clause_style))
    story.append(Paragraph("• Multi-factor authentication (MFA) is mandatory for all company accounts.", clause_style))
    story.append(Paragraph("• Password managers (approved: 1Password, Bitwarden) are encouraged.", clause_style))

    story.append(Paragraph("3. AI and External Tool Usage", section_style))
    story.append(Paragraph(
        "With the rapid adoption of AI tools, TechCorp has established the following guidelines to protect "
        "proprietary information while allowing productive use of approved AI tools.",
        body_style))

    story.append(Paragraph("3.1 Approved AI Tools", subsection_style))
    story.append(Paragraph("• <b>GitHub Copilot</b> (Enterprise license) — approved for code generation.", clause_style))
    story.append(Paragraph("• <b>Grammarly Business</b> — approved for writing assistance on non-confidential content.", clause_style))
    story.append(Paragraph("• <b>Internal AI Assistant</b> (Continuous-RAG) — approved for policy queries.", clause_style))

    story.append(Paragraph("3.2 Prohibited AI Tools", subsection_style))
    story.append(Paragraph("• <b>ChatGPT, Claude, Gemini</b> (consumer versions) — <b>PROHIBITED</b> for any work involving company data.", clause_style))
    story.append(Paragraph("• Any AI tool not on the approved list must receive IT Security approval before use.", clause_style))
    story.append(Paragraph("• Uploading company code, documents, or data to any external AI service is strictly forbidden.", clause_style))

    story.append(Paragraph("4. Data Classification and Handling", section_style))
    story.append(Paragraph("4.1 Data Categories", subsection_style))
    story.append(Paragraph("• <b>Public</b> — Marketing materials, press releases. No restrictions.", clause_style))
    story.append(Paragraph("• <b>Internal</b> — Policies, org charts, project plans. Company-only access.", clause_style))
    story.append(Paragraph("• <b>Confidential</b> — Financial data, customer PII, source code. Need-to-know basis.", clause_style))
    story.append(Paragraph("• <b>Restricted</b> — Trade secrets, M&A data, security keys. Executive approval required.", clause_style))

    story.append(Paragraph("4.2 Data Breach Reporting", subsection_style))
    story.append(Paragraph("• Any suspected data breach must be reported to IT Security within <b>1 hour</b> of discovery.", clause_style))
    story.append(Paragraph("• Contact: security@techcorp.com or ext. 9911.", clause_style))
    story.append(Paragraph("• Do NOT attempt to investigate or contain the breach yourself.", clause_style))

    doc.build(story)
    print(f"✓ Created: IT_Security_Policy.pdf")


def create_travel_policy():
    """Travel Policy — international work, approved countries, visa"""
    doc = SimpleDocTemplate(os.path.join(OUTPUT_DIR, "Travel_and_Remote_Work_Abroad.pdf"), pagesize=A4,
                            topMargin=1.5*cm, bottomMargin=1.5*cm, leftMargin=2*cm, rightMargin=2*cm)
    story = header_block(
        "International Travel & Remote Work Abroad Policy",
        "TRV-2026-004", "January 15, 2026", "Legal & Compliance"
    )

    story.append(Paragraph("1. Scope and Purpose", section_style))
    story.append(Paragraph(
        "This policy governs all international business travel and requests to work remotely from outside the employee's "
        "home country. Due to tax, legal, and security implications, strict approval processes are required.",
        body_style))

    story.append(Paragraph("2. International Remote Work", section_style))
    story.append(Paragraph("2.1 General Rules", subsection_style))
    story.append(Paragraph("• International remote work is permitted for a maximum of <b>30 consecutive days</b> per calendar year.", clause_style))
    story.append(Paragraph("• All international remote work requires <b>VP-level approval</b> and must be submitted at least 30 days in advance.", clause_style))
    story.append(Paragraph("• Employees must work during their <b>home office time zone hours</b> unless otherwise agreed.", clause_style))
    story.append(Paragraph("• VPN must be active at all times. Some countries may have VPN restrictions — check with IT Security.", clause_style))

    story.append(Paragraph("2.2 Approved Countries", subsection_style))
    story.append(Paragraph(
        "Remote work is only permitted from countries on the approved list. The following countries are currently approved:",
        body_style))
    story.append(Paragraph("• <b>Tier 1 (No restrictions):</b> United Kingdom, Canada, Germany, Australia, Singapore, Japan", clause_style))
    story.append(Paragraph("• <b>Tier 2 (VP approval required):</b> France, Netherlands, Spain, Portugal, New Zealand, South Korea", clause_style))
    story.append(Paragraph("• <b>Tier 3 (Not approved):</b> UAE, Russia, China, Iran, North Korea, Cuba, Venezuela — remote work from these countries is <b>NOT permitted</b> due to tax treaties, data residency laws, or sanctions.", clause_style))

    story.append(Paragraph("2.3 Tax Implications", subsection_style))
    story.append(Paragraph("• Working from another country for more than <b>15 days</b> may create tax obligations in that jurisdiction.", clause_style))
    story.append(Paragraph("• The Finance team must be notified of any international remote work period exceeding 15 days.", clause_style))
    story.append(Paragraph("• TechCorp will not be responsible for personal tax liabilities arising from unapproved international work.", clause_style))

    story.append(Paragraph("3. Business Travel Guidelines", section_style))
    story.append(Paragraph("3.1 Pre-Travel Requirements", subsection_style))
    story.append(Paragraph("• International travel must be booked through the company's designated travel agency (TravelCorp).", clause_style))
    story.append(Paragraph("• Travel insurance is automatically provided for all approved business travel.", clause_style))
    story.append(Paragraph("• Employees must register their travel in the Security Travel Tracker system.", clause_style))

    story.append(Paragraph("3.2 Visa and Documentation", subsection_style))
    story.append(Paragraph("• Employees are responsible for obtaining appropriate visas for business travel.", clause_style))
    story.append(Paragraph("• The company will reimburse visa fees for approved business travel.", clause_style))
    story.append(Paragraph("• Work permits are required for stays exceeding <b>90 days</b> in most jurisdictions.", clause_style))

    story.append(Paragraph("4. Emergency Contacts", section_style))
    story.append(Paragraph("• Global Security Operations Center: +1-800-TECH-SEC (available 24/7)", clause_style))
    story.append(Paragraph("• Legal & Compliance: compliance@techcorp.com", clause_style))
    story.append(Paragraph("• Travel Emergency: travel-emergency@techcorp.com", clause_style))

    doc.build(story)
    print(f"✓ Created: Travel_and_Remote_Work_Abroad.pdf")


if __name__ == "__main__":
    print("\n📄 Generating Stage 1 test PDFs...\n")
    create_hr_policy()
    create_finance_policy()
    create_it_security_policy()
    create_travel_policy()
    print(f"\n✅ All PDFs created in: {os.path.abspath(OUTPUT_DIR)}/")
    print("\nFiles:")
    for f in os.listdir(OUTPUT_DIR):
        size = os.path.getsize(os.path.join(OUTPUT_DIR, f))
        print(f"  📄 {f} ({size:,} bytes)")
