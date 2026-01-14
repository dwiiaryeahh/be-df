"""
Export service - Handle PDF dan Excel export untuk crawling data
"""
from typing import Dict
from sqlalchemy.orm import Session
from datetime import datetime
from app.db.models import Campaign, Crawling
import io

# For PDF
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors

# For Excel
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side


def get_campaign_with_crawling(db: Session, campaign_id: int) -> Dict:
    """Get campaign dan crawling data"""
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    
    if not campaign:
        return {"status": "error", "message": "Campaign not found"}
    
    crawlings = db.query(Crawling).filter(
        Crawling.campaign_id == campaign_id
    ).all()
    
    return {
        "status": "success",
        "campaign": campaign,
        "crawlings": crawlings
    }


def generate_pdf(db: Session, campaign_id: int) -> bytes:
    """Generate PDF using reportlab"""
    data = get_campaign_with_crawling(db, campaign_id)
    
    if data["status"] == "error":
        return None
    
    campaign = data["campaign"]
    crawlings = data["crawlings"]
    
    # Create PDF buffer with narrower margins
    pdf_buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        pdf_buffer, 
        pagesize=letter,
        leftMargin=0.5*inch,
        rightMargin=0.5*inch,
        topMargin=0.5*inch,
        bottomMargin=0.5*inch
    )
    elements = []
    
    # Styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'HeaderTitle',
        fontSize=14,
        spaceAfter=12,
        textColor=colors.HexColor('#2c3e50')
    )
    section_title_style = ParagraphStyle(
        'SectionTitle',
        fontSize=12,
        textColor=colors.HexColor('#2c3e50')
    )
    
  
    header_data = [
        [Paragraph("Backpack DF", title_style)]
    ]
    header_table = Table([
        ["", Paragraph("Backpack DF", title_style)] # Placeholder for logo in first col
    ], colWidths=[1.0*inch, 7.0*inch])
    
    header_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (1, 0), (1, 0), 'LEFT'),
    ]))
    elements.append(header_table)
    
    # Divider 1
    elements.append(Spacer(1, 5))
    elements.append(Table([[""]], colWidths=[8.0*inch], style=[
        ('LINEBELOW', (0,0), (-1,-1), 1, colors.black)
    ]))
    elements.append(Spacer(1, 0.2*inch))

    # 2. Information Section (Clean, no borders)
    created_at_str = campaign.created_at.strftime("%Y-%m-%d %H:%M:%S") if campaign.created_at and hasattr(campaign.created_at, 'strftime') else str(campaign.created_at) if campaign.created_at else "-"
    
    # Format: "Label   : Value"
    info_data = [
        ['Campaign Name', ':', campaign.name],
        ['Target IMSI', ':', campaign.imsi],
        ['Provider', ':', campaign.provider],
        ['Date', ':', created_at_str],
    ]
    
    # Using 3 columns to align the colon perfectly
    info_table = Table(info_data, colWidths=[1.5*inch, 0.2*inch, 6.3*inch])
    info_table.setStyle(TableStyle([
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'), # Label left
        ('ALIGN', (1, 0), (1, -1), 'CENTER'), # Colon center
        ('ALIGN', (2, 0), (2, -1), 'LEFT'), # Value left
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    elements.append(info_table)
    
    # Divider 2
    elements.append(Spacer(1, 5))
    elements.append(Table([[""]], colWidths=[8.0*inch], style=[
        ('LINEBELOW', (0,0), (-1,-1), 1, colors.black)
    ]))
    elements.append(Spacer(1, 0.2*inch))
    
    # 3. Data IMSI Table
    elements.append(Paragraph("Data IMSI", section_title_style))
    elements.append(Spacer(1, 0.1*inch))
    
    # Prepare crawling table data
    crawling_data = [['IMSI', 'Channel', 'Provider', 'Lat/Long', 'UL RSSI', 'Timestamp']]
    
    for crawl in crawlings:
        # Handle timestamp
        if hasattr(crawl, 'timestamp') and crawl.timestamp:
            if isinstance(crawl.timestamp, str):
                timestamp_str = crawl.timestamp
            else:
                timestamp_str = crawl.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        else:
            timestamp_str = "-"
        
        ulrssi_str = str(crawl.ulRssi) if hasattr(crawl, 'ulRssi') and crawl.ulRssi is not None else "-"
        
        crawling_data.append([
            crawl.imsi,
            'CH-01',
            'Telkomsel',
            '-6.2088,106.8456',
            ulrssi_str,
            timestamp_str
        ])
    
    crawling_table = Table(crawling_data, colWidths=[1.5*inch, 1.0*inch, 1.3*inch, 1.7*inch, 1.0*inch, 1.5*inch])
    crawling_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#123467')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        # ('BACKGROUND', (0, 1), (-1, -1), colors.beige), # Removed beige background for cleaner look? Keeping as per request "match top" usually implies style match, but user asked for cleanup. I'll keep the striping.
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')])
    ]))
    elements.append(crawling_table)
    
    # Build PDF
    doc.build(elements)
    pdf_buffer.seek(0)
    return pdf_buffer.getvalue()


def generate_excel(db: Session, campaign_id: int) -> bytes:
    """Generate Excel export dengan openpyxl"""
    data = get_campaign_with_crawling(db, campaign_id)
    
    if data["status"] == "error":
        return None
    
    campaign = data["campaign"]
    crawlings = data["crawlings"]
    
    # Create workbook
    wb = Workbook()
    ws = wb.active
    ws.title = "Crawling Report"
    
    # Set column widths
    ws.column_dimensions['A'].width = 20
    ws.column_dimensions['B'].width = 18
    ws.column_dimensions['C'].width = 15
    ws.column_dimensions['D'].width = 20
    ws.column_dimensions['E'].width = 15
    ws.column_dimensions['F'].width = 20

    info_font = Font(bold=True, size=11, color="2c3e50")
    info_fill = PatternFill(start_color="ecf0f1", end_color="ecf0f1", fill_type="solid")
    
    header_font = Font(bold=True, color="FFFFFF", size=11)
    header_fill = PatternFill(start_color="123467", end_color="123467", fill_type="solid")
    header_alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    
    border = Border(
        left=Side(style='thin', color='bdc3c7'),
        right=Side(style='thin', color='bdc3c7'),
        top=Side(style='thin', color='bdc3c7'),
        bottom=Side(style='thin', color='bdc3c7')
    )

    # Campaign info section
    row = 1
    
    # Row labels
    labels = [
        ("Campaign Name:", campaign.name),
        ("Target IMSI:", campaign.imsi),
        ("Provider:", campaign.provider),
        ("Created At:", campaign.created_at.strftime("%Y-%m-%d %H:%M:%S") if campaign.created_at and hasattr(campaign.created_at, 'strftime') else str(campaign.created_at) if campaign.created_at else "-"),
    ]
    
    for label, value in labels:
        ws[f'A{row}'] = label
        ws[f'A{row}'].font = info_font
        ws[f'A{row}'].fill = info_fill
        ws[f'A{row}'].border = border
        
        ws[f'B{row}'] = value
        ws[f'B{row}'].border = border
        ws[f'B{row}'].alignment = Alignment(horizontal="left", vertical="center")
        
        row += 1
    
    # Crawling data table
    row += 1
    
    headers = ["IMSI", "Channel", "Provider", "Lat/Long", "UL RSSI", "Timestamp"]
    for col_num, header in enumerate(headers, 1):
        cell = ws.cell(row=row, column=col_num)
        cell.value = header
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = header_alignment
        cell.border = border
    
    ws.row_dimensions[row].height = 20
    
    row += 1
    
    # Data rows
    for crawl in crawlings:
        # Handle timestamp - can be string or datetime
        if hasattr(crawl, 'timestamp') and crawl.timestamp:
            if isinstance(crawl.timestamp, str):
                timestamp_str = crawl.timestamp
            else:
                timestamp_str = crawl.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        else:
            timestamp_str = "-"
        
        ulrssi_str = str(crawl.ulRssi) if hasattr(crawl, 'ulRssi') and crawl.ulRssi is not None else "-"
        
        data_row = [
            crawl.imsi,
            "CH-01",  # TODO: update nanti dari data model
            "Telkomsel",  # TODO: update nanti dari data model
            "-6.2088,106.8456",  # TODO: update nanti dari data model
            ulrssi_str,
            timestamp_str
        ]
        
        for col_num, value in enumerate(data_row, 1):
            cell = ws.cell(row=row, column=col_num)
            cell.value = value
            cell.alignment = Alignment(horizontal="left", vertical="center")
            cell.border = border
            
            # Alternate row colors
            if row % 2 == 0:
                cell.fill = PatternFill(start_color="f8f9fa", end_color="f8f9fa", fill_type="solid")
        
        row += 1
    
    # Save to bytes
    excel_bytes = io.BytesIO()
    wb.save(excel_bytes)
    excel_bytes.seek(0)
    return excel_bytes.getvalue()
