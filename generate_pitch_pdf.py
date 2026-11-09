#!/usr/bin/env python3
"""
Generate a professional pitch deck PDF from markdown content.
"""

import re
import os
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
from reportlab.pdfgen import canvas

# Configuration
SLIDE_WIDTH = 11 * inch  # Letter landscape
SLIDE_HEIGHT = 8.5 * inch
PAGE_SIZE = (SLIDE_WIDTH, SLIDE_HEIGHT)

def parse_markdown(md_file):
    """Parse the markdown file into structured slides."""
    with open(md_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    slides = []
    current_slide = None
    
    lines = content.split('\n')
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        
        # Detect slide headers (## Slide N:)
        if line.startswith('## Slide '):
            if current_slide:
                slides.append(current_slide)
            current_slide = {
                'title': line.split(':', 1)[1].strip() if ':' in line else line,
                'content': []
            }
        elif line.startswith('### '):
            # Subtitle
            if current_slide:
                current_slide['subtitle'] = line[4:]
        elif line.startswith('---'):
            # Slide separator
            if current_slide:
                slides.append(current_slide)
                current_slide = None
        elif current_slide and line:
            current_slide['content'].append(line)
        
        i += 1
    
    if current_slide:
        slides.append(current_slide)
    
    return slides

def create_styles():
    """Create custom styles for the presentation."""
    styles = getSampleStyleSheet()
    
    # Title style
    styles.add(ParagraphStyle(
        name='SlideTitle',
        parent=styles['Heading1'],
        fontSize=32,
        textColor=colors.HexColor('#1a365d'),
        spaceAfter=12,
        alignment=TA_LEFT,
        fontName='Helvetica-Bold'
    ))
    
    # Subtitle style
    styles.add(ParagraphStyle(
        name='SlideSubtitle',
        parent=styles['Heading2'],
        fontSize=22,
        textColor=colors.HexColor('#2d3748'),
        spaceAfter=20,
        alignment=TA_LEFT,
        fontName='Helvetica-Bold'
    ))
    
    # Body text
    styles.add(ParagraphStyle(
        name='SlideBody',
        parent=styles['Normal'],
        fontSize=14,
        textColor=colors.HexColor('#2d3748'),
        spaceAfter=8,
        leading=20,
        alignment=TA_LEFT,
        fontName='Helvetica'
    ))
    
    # Bullet style
    styles.add(ParagraphStyle(
        name='SlideBullet',
        parent=styles['Normal'],
        fontSize=13,
        textColor=colors.HexColor('#2d3748'),
        spaceAfter=6,
        leading=18,
        leftIndent=20,
        bulletIndent=10,
        fontName='Helvetica'
    ))
    
    # Code/emphasis style
    styles.add(ParagraphStyle(
        name='SlideCode',
        parent=styles['Normal'],
        fontSize=11,
        textColor=colors.HexColor('#c53030'),
        fontName='Courier',
        backColor=colors.HexColor('#f7fafc'),
        leftIndent=10,
        rightIndent=10
    ))
    
    # Speaker notes
    styles.add(ParagraphStyle(
        name='SpeakerNote',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.HexColor('#718096'),
        spaceAfter=6,
        leading=14,
        leftIndent=20,
        fontName='Helvetica-Oblique'
    ))
    
    return styles

class SlideCanvas(canvas.Canvas):
    """Custom canvas for slide formatting."""
    
    def __init__(self, *args, **kwargs):
        canvas.Canvas.__init__(self, *args, **kwargs)
        self.pages = []
        
    def showPage(self):
        self.pages.append(dict(self.__dict__))
        self._startPage()
        
    def save(self):
        page_count = len(self.pages)
        for i, page in enumerate(self.pages):
            self.__dict__.update(page)
            self.draw_page_number(i + 1, page_count)
            canvas.Canvas.showPage(self)
        canvas.Canvas.save(self)
        
    def draw_page_number(self, page_num, total):
        """Draw page number at bottom right."""
        self.setFont('Helvetica', 10)
        self.setFillColor(colors.HexColor('#718096'))
        self.drawRightString(SLIDE_WIDTH - 0.5*inch, 0.4*inch, 
                            f"BALAT v2 | {page_num}/{total}")

def process_content_line(line, styles):
    """Convert markdown line to reportlab element."""
    elements = []
    
    # Handle different markdown patterns
    if line.startswith('**Speaker note'):
        text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', line)
        elements.append(Paragraph(text, styles['SpeakerNote']))
    elif line.startswith('- '):
        # Bullet point
        bullet_text = line[2:]
        bullet_text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', bullet_text)
        bullet_text = re.sub(r'`(.*?)`', r'<font name="Courier" color="#c53030">\1</font>', bullet_text)
        elements.append(Paragraph(f'• {bullet_text}', styles['SlideBullet']))
    elif line.startswith('```'):
        # Skip code fence markers for now
        pass
    elif line.startswith('> '):
        # Quote
        quote_text = line[2:]
        elements.append(Paragraph(f'<i>{quote_text}</i>', styles['SlideBody']))
    elif line.startswith('| '):
        # Table row - skip for now, handled separately
        pass
    elif re.match(r'^#+', line):
        # Additional headers within slide content
        level = len(re.match(r'^#+', line).group())
        text = line.lstrip('#').strip()
        if level <= 4:
            elements.append(Paragraph(f'<b>{text}</b>', styles['SlideSubtitle']))
    else:
        # Regular paragraph
        text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', line)
        text = re.sub(r'`(.*?)`', r'<font name="Courier" color="#c53030">\1</font>', text)
        text = re.sub(r'\[(.*?)\]\((.*?)\)', r'<link href="\2">\1</link>', text)
        if text:
            elements.append(Paragraph(text, styles['SlideBody']))
    
    return elements

def create_slide(slide_data, styles, story):
    """Create a single slide."""
    
    # Add title
    if 'title' in slide_data:
        story.append(Spacer(1, 0.3*inch))
        story.append(Paragraph(slide_data['title'], styles['SlideTitle']))
    
    # Add subtitle
    if 'subtitle' in slide_data:
        story.append(Paragraph(slide_data['subtitle'], styles['SlideSubtitle']))
    
    story.append(Spacer(1, 0.2*inch))
    
    # Process content
    in_table = False
    table_data = []
    in_code_block = False
    code_lines = []
    
    for line in slide_data.get('content', []):
        if line.startswith('```'):
            if in_code_block:
                # End code block
                code_text = '\n'.join(code_lines)
                story.append(Paragraph(f'<font name="Courier" size="9">{code_text}</font>', 
                                      styles['SlideCode']))
                story.append(Spacer(1, 0.1*inch))
                code_lines = []
                in_code_block = False
            else:
                # Start code block
                in_code_block = True
            continue
        
        if in_code_block:
            code_lines.append(line)
            continue
        
        if line.startswith('| '):
            # Table row
            if not in_table:
                in_table = True
                table_data = []
            cells = [cell.strip() for cell in line.split('|')[1:-1]]
            table_data.append(cells)
        elif line.startswith('|---'):
            # Table separator - skip
            continue
        else:
            # End table if we were in one
            if in_table and table_data:
                t = Table(table_data, hAlign='LEFT')
                t.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#edf2f7')),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#1a365d')),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 11),
                    ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                    ('FONTSIZE', (0, 1), (-1, -1), 10),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                    ('TOPPADDING', (0, 0), (-1, -1), 8),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e0')),
                ]))
                story.append(t)
                story.append(Spacer(1, 0.15*inch))
                table_data = []
                in_table = False
            
            # Regular content
            elements = process_content_line(line, styles)
            for elem in elements:
                story.append(elem)
    
    # Handle remaining table
    if in_table and table_data:
        t = Table(table_data, hAlign='LEFT')
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#edf2f7')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#1a365d')),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 11),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e0')),
        ]))
        story.append(t)
    
    # Page break for next slide
    story.append(PageBreak())

def generate_pdf(md_file, output_pdf, svg_file=None):
    """Generate the PDF presentation."""
    
    # Parse markdown
    print(f"Parsing {md_file}...")
    slides = parse_markdown(md_file)
    print(f"Found {len(slides)} slides")
    
    # Create PDF
    print(f"Generating {output_pdf}...")
    doc = SimpleDocTemplate(
        output_pdf,
        pagesize=PAGE_SIZE,
        leftMargin=0.75*inch,
        rightMargin=0.75*inch,
        topMargin=0.5*inch,
        bottomMargin=0.6*inch
    )
    
    story = []
    styles = create_styles()
    
    # Add each slide
    for i, slide in enumerate(slides, 1):
        print(f"  Processing slide {i}: {slide.get('title', 'Untitled')[:50]}...")
        create_slide(slide, styles, story)
    
    # Build PDF with custom canvas
    doc.build(story, canvasmaker=SlideCanvas)
    print(f"✓ PDF created: {output_pdf}")

if __name__ == '__main__':
    import sys
    
    # Set up paths
    base_dir = '/home/muqtada/Documents/balat'
    md_file = os.path.join(base_dir, 'pm/pitch-deckv2.md')
    output_pdf = os.path.join(base_dir, 'pitchppt.pdf')
    svg_file = os.path.join(base_dir, 'pm/assets/balat-validation-stack.svg')
    
    if not os.path.exists(md_file):
        print(f"Error: Markdown file not found: {md_file}")
        sys.exit(1)
    
    generate_pdf(md_file, output_pdf, svg_file)
    print(f"\n✓ Presentation PDF generated successfully!")
    print(f"  Location: {output_pdf}")
