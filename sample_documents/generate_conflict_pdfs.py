"""
Generate two conflicting demo PDF documents for GreenLens demo purposes.
Doc A: Purchase Order PO-98231-GDH (buyer's version)
Doc B: Vendor Order Confirmation VC-2026-0847 (vendor's version)
Both reference the same deal but have deliberate conflicts on price, terms, delivery, and warranty.
"""
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
import os

OUT_DIR = os.path.dirname(os.path.abspath(__file__))

def make_styles():
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='DocTitle', fontSize=16, fontName='Helvetica-Bold',
        spaceAfter=4, textColor=colors.HexColor('#1a1a2e'), alignment=TA_LEFT))
    styles.add(ParagraphStyle(name='DocSubtitle', fontSize=10, fontName='Helvetica',
        spaceAfter=2, textColor=colors.HexColor('#555555'), alignment=TA_LEFT))
    styles.add(ParagraphStyle(name='SectionHead', fontSize=10, fontName='Helvetica-Bold',
        spaceBefore=12, spaceAfter=4, textColor=colors.HexColor('#1a1a2e')))
    styles.add(ParagraphStyle(name='Body', fontSize=9, fontName='Helvetica',
        spaceAfter=3, leading=14, textColor=colors.HexColor('#333333')))
    styles.add(ParagraphStyle(name='SmallNote', fontSize=8, fontName='Helvetica-Oblique',
        spaceAfter=2, textColor=colors.HexColor('#777777')))
    styles.add(ParagraphStyle(name='Warning', fontSize=9, fontName='Helvetica-Bold',
        spaceAfter=3, textColor=colors.HexColor('#cc0000')))
    return styles

def table_style_base():
    return TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#2c3e50')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,0), 8),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('ALIGN', (2,1), (-1,-1), 'RIGHT'),
        ('FONTSIZE', (0,1), (-1,-1), 8),
        ('FONTNAME', (0,1), (-1,-1), 'Helvetica'),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.HexColor('#f9f9f9'), colors.white]),
        ('GRID', (0,0), (-1,-1), 0.4, colors.HexColor('#cccccc')),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
    ])


def build_purchase_order(styles):
    """
    DOCUMENT A: Purchase Order from Global Dynamics Holdings (Buyer)
    Conflicts embedded vs vendor confirmation:
    - Unit price for AI License: $425/unit (buyer) vs $525/unit (vendor)
    - Payment terms: Net 60 (buyer PO) vs Net 30 (vendor confirmation)
    - Delivery: 21 business days (buyer) vs 14 business days (vendor)
    - Warranty: 24 months (buyer expectation) vs 12 months (vendor)
    - Late fee: 1.5%/month (buyer) vs 2.5%/month (vendor)
    - Consulting rate: $175/hr (buyer) vs $200/hr (vendor)
    """
    path = os.path.join(OUT_DIR, "Demo_PurchaseOrder_GlobalDynamics.pdf")
    doc = SimpleDocTemplate(path, pagesize=letter,
        leftMargin=0.85*inch, rightMargin=0.85*inch,
        topMargin=0.85*inch, bottomMargin=0.85*inch)
    story = []
    s = styles

    # Header
    story.append(Paragraph("PURCHASE ORDER", s['DocTitle']))
    story.append(Paragraph("Global Dynamics Holdings Ltd.", s['DocSubtitle']))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#2c3e50'), spaceAfter=10))

    meta = [
        ["PO Number:", "PO-98231-GDH", "Issue Date:", "June 28, 2026"],
        ["Contract Ref:", "TC-ENT-2026-003", "Required By:", "August 5, 2026"],
        ["Buyer:", "Global Dynamics Holdings Ltd.", "Approved By:", "James Morrison, CFO"],
        ["Vendor:", "TechCorp Solutions Inc.", "Department:", "IT & Infrastructure"],
    ]
    mt = Table(meta, colWidths=[1.3*inch, 2.2*inch, 1.3*inch, 2.2*inch])
    mt.setStyle(TableStyle([
        ('FONTNAME', (0,0), (0,-1), 'Helvetica-Bold'),
        ('FONTNAME', (2,0), (2,-1), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 8),
        ('TEXTCOLOR', (0,0), (0,-1), colors.HexColor('#555555')),
        ('TEXTCOLOR', (2,0), (2,-1), colors.HexColor('#555555')),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ('TOPPADDING', (0,0), (-1,-1), 3),
    ]))
    story.append(mt)
    story.append(Spacer(1, 10))

    story.append(Paragraph("VENDOR DETAILS", s['SectionHead']))
    story.append(Paragraph("TechCorp Solutions Inc. | 1200 Market Street, Suite 400, San Francisco, CA 94103", s['Body']))
    story.append(Paragraph("Contact: Sarah Chen, VP Enterprise Sales | sarah.chen@techcorp.com | +1 (415) 555-0192", s['Body']))
    story.append(Spacer(1, 6))

    story.append(Paragraph("ORDER ITEMS", s['SectionHead']))
    items_data = [
        ["#", "Description", "Qty", "Unit Price", "Total"],
        ["1", "AI Platform License (Annual) — Enterprise Plus", "1", "$425.00", "$45,200.00"],
        ["2", "Cloud Infrastructure Hosting (Annual)", "1", "$320.00", "$32,000.00"],
        ["3", "Security Audit Package (Quarterly x4)", "1", "$150.00", "$12,000.00"],
        ["4", "Technical Consulting Hours", "40 hrs", "$175.00/hr", "$7,000.00"],
        ["", "", "", "Subtotal", "$96,200.00"],
        ["", "", "", "Volume Discount (5%)", "-$4,810.00"],
        ["", "", "", "Tax (8.5%)", "$7,762.55"],
        ["", "TOTAL ORDER VALUE", "", "", "$99,152.55"],
    ]
    it = Table(items_data, colWidths=[0.3*inch, 2.8*inch, 0.7*inch, 1.3*inch, 1.1*inch])
    ts = table_style_base()
    ts.add('FONTNAME', (0, len(items_data)-1), (-1, len(items_data)-1), 'Helvetica-Bold')
    ts.add('BACKGROUND', (0, len(items_data)-1), (-1, len(items_data)-1), colors.HexColor('#eaf4ff'))
    it.setStyle(ts)
    story.append(it)
    story.append(Spacer(1, 8))

    story.append(Paragraph("TERMS AND CONDITIONS", s['SectionHead']))
    terms = [
        ["Payment Terms:", "Net 60 days from invoice receipt date"],
        ["Late Payment Fee:", "1.5% per month on overdue balance"],
        ["Delivery Timeline:", "21 business days from PO acceptance"],
        ["Warranty Period:", "24 months from delivery and acceptance date"],
        ["Support SLA:", "24-hour response time, 7 days a week"],
        ["Support Hours:", "24/7 for critical issues; business hours for standard"],
        ["Termination:", "Either party may terminate with 90 days written notice"],
        ["Governing Law:", "State of Texas, United States"],
        ["Dispute Resolution:", "Binding arbitration in Austin, TX"],
    ]
    tt = Table(terms, colWidths=[1.8*inch, 5.2*inch])
    tt.setStyle(TableStyle([
        ('FONTNAME', (0,0), (0,-1), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 8),
        ('TEXTCOLOR', (0,0), (0,-1), colors.HexColor('#2c3e50')),
        ('ROWBACKGROUNDS', (0,0), (-1,-1), [colors.HexColor('#f5f5f5'), colors.white]),
        ('GRID', (0,0), (-1,-1), 0.3, colors.HexColor('#dddddd')),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(tt)
    story.append(Spacer(1, 8))

    story.append(Paragraph("SPECIAL CONDITIONS", s['SectionHead']))
    story.append(Paragraph(
        "1. This Purchase Order is issued based on Quotation QT-2026-0392 dated June 15, 2026. "
        "All pricing is locked as quoted and vendor confirms no price increases during the contract term.", s['Body']))
    story.append(Paragraph(
        "2. The 5% volume discount applies as agreed during negotiation on June 20, 2026. "
        "Consulting rate of $175/hour is confirmed by vendor representative Sarah Chen via email June 22, 2026.", s['Body']))
    story.append(Paragraph(
        "3. Warranty of 24 months supersedes any vendor standard terms. Client requires extended warranty "
        "as condition of award. Vendor acceptance of this PO constitutes agreement to 24-month warranty.", s['Body']))
    story.append(Paragraph(
        "4. Payment terms of Net 60 are standard per Global Dynamics procurement policy GD-PROC-2024-11. "
        "Any deviation requires written approval from CFO James Morrison.", s['Body']))
    story.append(Spacer(1, 10))

    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor('#cccccc'), spaceAfter=8))
    story.append(Paragraph("AUTHORIZED SIGNATURES", s['SectionHead']))
    sig_data = [
        ["Issued By (Buyer):", "Approved By (Finance):"],
        ["James Morrison", "Linda Zhao"],
        ["CFO, Global Dynamics Holdings Ltd.", "VP Finance, Global Dynamics Holdings Ltd."],
        ["Date: June 28, 2026", "Date: June 28, 2026"],
    ]
    st_sig = Table(sig_data, colWidths=[3.5*inch, 3.5*inch])
    st_sig.setStyle(TableStyle([
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTNAME', (0,1), (-1,1), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 8),
        ('TEXTCOLOR', (0,0), (-1,0), colors.HexColor('#777777')),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('LINEABOVE', (0,1), (-1,1), 0.5, colors.HexColor('#cccccc')),
    ]))
    story.append(st_sig)
    story.append(Spacer(1, 6))
    story.append(Paragraph(
        "This document is the official purchase authorization of Global Dynamics Holdings Ltd. "
        "Vendor acceptance of goods/services constitutes agreement to all terms herein.", s['SmallNote']))

    doc.build(story)
    print(f"Created: {path}")
    return path


def build_vendor_confirmation(styles):
    """
    DOCUMENT B: Vendor Order Confirmation from TechCorp Solutions
    Deliberately conflicts with the PO on multiple terms.
    """
    path = os.path.join(OUT_DIR, "Demo_VendorConfirmation_TechCorp.pdf")
    doc = SimpleDocTemplate(path, pagesize=letter,
        leftMargin=0.85*inch, rightMargin=0.85*inch,
        topMargin=0.85*inch, bottomMargin=0.85*inch)
    story = []
    s = styles

    story.append(Paragraph("ORDER CONFIRMATION", s['DocTitle']))
    story.append(Paragraph("TechCorp Solutions Inc. — Vendor Copy", s['DocSubtitle']))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#c0392b'), spaceAfter=10))

    meta = [
        ["Confirmation #:", "VC-2026-0847", "Confirmation Date:", "July 1, 2026"],
        ["Client PO Ref:", "PO-98231-GDH", "Contract Ref:", "TC-ENT-2026-003"],
        ["Bill To:", "Global Dynamics Holdings Ltd.", "Account Manager:", "Sarah Chen"],
        ["Ship To:", "500 Innovation Drive, Austin TX", "Sales Rep:", "Mike Torres"],
    ]
    mt = Table(meta, colWidths=[1.3*inch, 2.2*inch, 1.3*inch, 2.2*inch])
    mt.setStyle(TableStyle([
        ('FONTNAME', (0,0), (0,-1), 'Helvetica-Bold'),
        ('FONTNAME', (2,0), (2,-1), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 8),
        ('TEXTCOLOR', (0,0), (0,-1), colors.HexColor('#555555')),
        ('TEXTCOLOR', (2,0), (2,-1), colors.HexColor('#555555')),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ('TOPPADDING', (0,0), (-1,-1), 3),
    ]))
    story.append(mt)
    story.append(Spacer(1, 10))

    story.append(Paragraph("CONFIRMED ORDER ITEMS", s['SectionHead']))
    items_data = [
        ["#", "Description", "Qty", "Unit Price", "Total"],
        ["1", "AI Platform License (Annual) — Enterprise Plus", "1", "$525.00", "$48,500.00"],
        ["2", "Cloud Infrastructure Hosting (Annual)", "1", "$350.00", "$35,000.00"],
        ["3", "Security Audit Package (Quarterly x4)", "1", "$150.00", "$12,000.00"],
        ["4", "Technical Consulting — Senior Engineer Rate", "40 hrs", "$200.00/hr", "$8,000.00"],
        ["", "", "", "Subtotal", "$103,500.00"],
        ["", "", "", "Discount", "$0.00"],
        ["", "", "", "Tax (8.5%)", "$8,797.50"],
        ["", "TOTAL CONFIRMED VALUE", "", "", "$112,297.50"],
    ]
    it = Table(items_data, colWidths=[0.3*inch, 2.8*inch, 0.7*inch, 1.3*inch, 1.1*inch])
    ts = table_style_base()
    ts.add('BACKGROUND', (0,0), (-1,0), colors.HexColor('#c0392b'))
    ts.add('FONTNAME', (0, len(items_data)-1), (-1, len(items_data)-1), 'Helvetica-Bold')
    ts.add('BACKGROUND', (0, len(items_data)-1), (-1, len(items_data)-1), colors.HexColor('#fff0ee'))
    it.setStyle(ts)
    story.append(it)
    story.append(Spacer(1, 6))
    story.append(Paragraph(
        "PRICING NOTE: Unit prices reflect current enterprise list pricing per TechCorp Rate Card 2026-Q3. "
        "The $525/unit AI Platform License includes premium 24/7 support tier. No volume discounts apply "
        "as client did not meet the 3-year commitment threshold required for discount eligibility.",
        s['Warning']))
    story.append(Spacer(1, 6))

    story.append(Paragraph("CONFIRMED TERMS AND CONDITIONS", s['SectionHead']))
    terms = [
        ["Payment Terms:", "Net 30 days from invoice date — STANDARD TERMS APPLY"],
        ["Late Payment Fee:", "2.5% per month on overdue balance (compounding)"],
        ["Delivery Timeline:", "14 business days from receipt of signed contract"],
        ["Warranty Period:", "12 months from delivery date (TechCorp standard warranty)"],
        ["Support SLA:", "48-hour response time, Monday-Friday 9AM-5PM PST only"],
        ["Consulting Rate:", "$200/hour — Senior Engineer rate (non-negotiable)"],
        ["Governing Law:", "State of California, United States"],
        ["Dispute Resolution:", "Litigation in San Francisco County Superior Court"],
        ["Auto-Renewal:", "Annual auto-renewal; 30 days notice required to cancel"],
    ]
    tt = Table(terms, colWidths=[1.8*inch, 5.2*inch])
    tt.setStyle(TableStyle([
        ('FONTNAME', (0,0), (0,-1), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 8),
        ('TEXTCOLOR', (0,0), (0,-1), colors.HexColor('#c0392b')),
        ('ROWBACKGROUNDS', (0,0), (-1,-1), [colors.HexColor('#fff8f8'), colors.white]),
        ('GRID', (0,0), (-1,-1), 0.3, colors.HexColor('#dddddd')),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(tt)
    story.append(Spacer(1, 8))

    story.append(Paragraph("VENDOR TERMS OVERRIDE NOTICE", s['SectionHead']))
    story.append(Paragraph(
        "1. PRICING: This confirmation supersedes any pricing referenced in client PO-98231-GDH. "
        "The quoted price of $425/unit in Quotation QT-2026-0392 was a preliminary estimate. "
        "Final confirmed pricing is $525/unit per TechCorp enterprise rate card effective July 1, 2026.", s['Body']))
    story.append(Paragraph(
        "2. PAYMENT: TechCorp standard Net 30 payment terms apply. Client's stated Net 60 preference "
        "was not agreed to by TechCorp's Finance department. Invoice INV-2026-0847 is due July 31, 2026.", s['Body']))
    story.append(Paragraph(
        "3. WARRANTY: TechCorp standard warranty is 12 months. Any extension beyond 12 months requires "
        "a separate Extended Warranty Agreement at additional cost ($8,500/year). No verbal or written "
        "representations by sales staff can extend the standard warranty without a signed addendum.", s['Body']))
    story.append(Paragraph(
        "4. CONSULTING: The applicable rate is $200/hour for Senior Engineer engagements. "
        "The $175/hour rate referenced in client communications applied to Junior Engineer tier only, "
        "which was not selected for this engagement. Total consulting exposure: $8,000.", s['Body']))
    story.append(Paragraph(
        "5. JURISDICTION: All disputes governed by California law and litigated in San Francisco, CA — "
        "not Texas as stated in client PO. Client acceptance of services constitutes agreement to these terms.", s['Body']))
    story.append(Spacer(1, 10))

    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor('#cccccc'), spaceAfter=8))
    story.append(Paragraph("TOTAL FINANCIAL EXPOSURE SUMMARY", s['SectionHead']))
    exposure = [
        ["Item", "Client PO Amount", "Vendor Confirmed", "Discrepancy"],
        ["AI Platform License", "$45,200.00", "$48,500.00", "+$3,300.00"],
        ["Cloud Infrastructure", "$32,000.00", "$35,000.00", "+$3,000.00"],
        ["Security Audit", "$12,000.00", "$12,000.00", "$0.00"],
        ["Consulting (40 hrs)", "$7,000.00", "$8,000.00", "+$1,000.00"],
        ["Volume Discount", "-$4,810.00", "$0.00", "+$4,810.00"],
        ["TAX DIFFERENCE", "$7,762.55", "$8,797.50", "+$1,034.95"],
        ["TOTAL DIFFERENCE", "$99,152.55", "$112,297.50", "+$13,144.95"],
    ]
    et = Table(exposure, colWidths=[2.2*inch, 1.5*inch, 1.5*inch, 1.3*inch])
    ets = table_style_base()
    ets.add('BACKGROUND', (0,0), (-1,0), colors.HexColor('#7f1d1d'))
    ets.add('FONTNAME', (0, len(exposure)-1), (-1, len(exposure)-1), 'Helvetica-Bold')
    ets.add('BACKGROUND', (0, len(exposure)-1), (-1, len(exposure)-1), colors.HexColor('#fee2e2'))
    ets.add('TEXTCOLOR', (3,1), (3,-1), colors.HexColor('#c0392b'))
    et.setStyle(ets)
    story.append(et)
    story.append(Spacer(1, 6))
    story.append(Paragraph(
        "CRITICAL: Total billing discrepancy of $13,144.95 exists between client PO and vendor confirmation. "
        "This must be resolved before payment is processed.", s['Warning']))
    story.append(Spacer(1, 10))

    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor('#cccccc'), spaceAfter=8))
    sig_data = [
        ["Issued By (Vendor):", "Reviewed By:"],
        ["David Park", "Rachel Kim"],
        ["COO, TechCorp Solutions Inc.", "Legal Counsel, TechCorp Solutions Inc."],
        ["Date: July 1, 2026", "Date: July 1, 2026"],
    ]
    st_sig = Table(sig_data, colWidths=[3.5*inch, 3.5*inch])
    st_sig.setStyle(TableStyle([
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTNAME', (0,1), (-1,1), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 8),
        ('TEXTCOLOR', (0,0), (-1,0), colors.HexColor('#777777')),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ('TOPPADDING', (0,0), (-1,-1), 3),
    ]))
    story.append(st_sig)
    story.append(Spacer(1, 4))
    story.append(Paragraph(
        "TechCorp Solutions Inc. standard terms and conditions apply. This confirmation constitutes "
        "TechCorp's acceptance of the order subject to the terms stated herein, which take precedence "
        "over any conflicting terms in the client's purchase order.", s['SmallNote']))

    doc.build(story)
    print(f"Created: {path}")
    return path


if __name__ == "__main__":
    styles = make_styles()
    build_purchase_order(styles)
    build_vendor_confirmation(styles)
    print("\nDone! Upload both PDFs to GreenLens to see conflict detection in action.")
    print("Key conflicts:")
    print("  - AI License: $425 (PO) vs $525 (vendor) = +$3,300")
    print("  - Payment: Net 60 (buyer) vs Net 30 (vendor)")
    print("  - Delivery: 21 days (buyer) vs 14 days (vendor)")
    print("  - Warranty: 24 months (buyer) vs 12 months (vendor)")
    print("  - Consulting: $175/hr (buyer) vs $200/hr (vendor)")
    print("  - Jurisdiction: Texas (buyer) vs California (vendor)")
    print("  - Total gap: $13,144.95")
