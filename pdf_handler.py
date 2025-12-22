"""
PDF Handler - PDF manipulation and generation
Handles merging, numbering, TOC generation, compression
"""

import os
from typing import List, Dict, Optional
from datetime import datetime
from PyPDF2 import PdfReader, PdfWriter, PdfMerger
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from io import BytesIO
import tempfile

# Import compression handler
try:
    from compress_handler import USCISPDFCompressor
    COMPRESSION_AVAILABLE = True
except ImportError:
    COMPRESSION_AVAILABLE = False


class PDFHandler:
    """Handle all PDF operations including compression"""

    def __init__(
        self,
        enable_compression: bool = False,
        quality_preset: str = 'high',
        smallpdf_api_key: Optional[str] = None
    ):
        """
        Initialize PDF Handler

        Args:
            enable_compression: Whether to compress PDFs before processing
            quality_preset: Compression quality ('high', 'balanced', 'maximum')
            smallpdf_api_key: Optional SmallPDF API key for premium compression
        """
        self.temp_dir = tempfile.gettempdir()
        self.enable_compression = enable_compression and COMPRESSION_AVAILABLE
        self.compressor = None

        if self.enable_compression:
            self.compressor = USCISPDFCompressor(
                quality_preset=quality_preset,
                smallpdf_api_key=smallpdf_api_key
            )

    def create_exhibit_cover_page(self, exhibit_number: str, title: str = None, summary: str = None) -> str:
        """
        Create a simple cover page with exhibit number and horizontal lines
        
        Args:
            exhibit_number: Exhibit number (A, B, C, etc.)
            
        Returns:
            Path to generated cover page PDF
        """
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen import canvas
        import os
        
        cover_path = os.path.join(self.temp_dir, f"cover_{exhibit_number}.pdf")
        
        try:
            # Create cover page
            c = canvas.Canvas(cover_path, pagesize=letter)
            width, height = letter

            # Draw top horizontal line
            c.setStrokeColorRGB(0, 0, 0)
            c.setLineWidth(2)
            c.line(50, height - 300, width - 50, height - 300)

            # Add exhibit number
            c.setFont("Helvetica-Bold", 48)
            text = f"Exhibit {exhibit_number}"
            text_width = c.stringWidth(text, "Helvetica-Bold", 48)
            x_pos = (width - text_width) / 2
            y_pos = height - 220
            c.drawString(x_pos, y_pos, text)

            # Add title if provided
            if title:
                c.setFont("Helvetica-Bold", 18)
                title_lines = self._wrap_text(title, 60)
                ty = y_pos - 60
                for line in title_lines:
                    c.drawCentredString(width / 2, ty, line)
                    ty -= 20

            # Add summary (smaller) if provided
            if summary:
                c.setFont("Helvetica", 10)
                summary_lines = self._wrap_text(summary, 90)
                sy = y_pos - 120
                for line in summary_lines[:10]:
                    c.drawCentredString(width / 2, sy, line)
                    sy -= 14

            # Draw bottom horizontal line
            c.line(50, height / 2 - 50, width - 50, height / 2 - 50)
            c.save()
            return cover_path

        except Exception as e:
            print(f"Error creating cover page: {e}")
            return None

    def _wrap_text(self, text: str, max_chars: int) -> List[str]:
        """Simple word-wrap utility for cover text"""
        if not text:
            return []
        words = text.split()
        lines = []
        cur = []
        cur_len = 0
        for w in words:
            if cur_len + len(w) + (1 if cur else 0) > max_chars:
                lines.append(' '.join(cur))
                cur = [w]
                cur_len = len(w)
            else:
                cur.append(w)
                cur_len += len(w) + (1 if cur_len else 0)
        if cur:
            lines.append(' '.join(cur))
        return lines

    def add_exhibit_number_with_cover(self, pdf_path: str, exhibit_number: str, title: str = None, summary: str = None, extracted_text: str = None, content_bytes: bytes = None) -> str:
        """
        Add separate cover page before PDF content
        
        Args:
            pdf_path: Path to original PDF
            exhibit_number: Exhibit number (A, B, C, etc.)
            
        Returns:
            Path to PDF with cover page
        """
        try:
            # STEP 1: Compress PDF first if compression is enabled
            working_path = pdf_path
            compression_info = None

            if self.enable_compression and self.compressor:
                compress_result = self.compressor.compress(pdf_path)
                if compress_result['success']:
                    working_path = compress_result['output_path']
                    compression_info = compress_result

            # STEP 2: Create cover page (include title/summary if provided)
            cover_path = self.create_exhibit_cover_page(exhibit_number, title=title, summary=summary)
            
            if not cover_path:
                return pdf_path  # Return original if cover creation fails

            # STEP 3: Merge cover page with original PDF
            merger = PdfMerger()

            # Add cover page first
            merger.append(cover_path)

            # Add original (possibly compressed) PDF
            merger.append(working_path)

            # STEP 3a: Optionally add a transcription + image pages PDF
            try:
                text_images_pdf = self.create_text_and_images_pdf(working_path, extracted_text=extracted_text, content_bytes=content_bytes)
                if text_images_pdf and os.path.exists(text_images_pdf):
                    merger.append(text_images_pdf)
            except Exception as e:
                print(f"Warning: failed to append text/images PDF for {pdf_path}: {e}")

            # STEP 4: Save the combined PDF
            output_path = os.path.join(
                self.temp_dir,
                f"Exhibit_{exhibit_number}_{os.path.basename(pdf_path)}"
            )

            merger.write(output_path)
            merger.close()

            return output_path

        except Exception as e:
            print(f"Error adding exhibit cover page: {e}")
            return pdf_path  # Return original if numbering fails

    def add_exhibit_number(self, pdf_path: str, exhibit_number: str) -> str:
        """
        Add exhibit number to PDF header (compresses first if enabled)

        Args:
            pdf_path: Path to original PDF
            exhibit_number: Exhibit number (A, B, C, etc.)

        Returns:
            Path to numbered PDF with compression info
        """
        try:
            # STEP 1: Compress PDF first if compression is enabled
            working_path = pdf_path
            compression_info = None

            if self.enable_compression and self.compressor:
                compress_result = self.compressor.compress(pdf_path)
                if compress_result['success']:
                    working_path = compress_result['output_path']
                    compression_info = compress_result
                    print(f"✓ Compressed {os.path.basename(pdf_path)}: "
                          f"{compress_result['reduction_percent']:.1f}% reduction "
                          f"({compress_result['method']})")

            # STEP 2: Read PDF (compressed or original)
            reader = PdfReader(working_path)
            writer = PdfWriter()

            # Create header with exhibit number (only on first page)
            for page_num, page in enumerate(reader.pages):
                # Create overlay with exhibit number only on first page
                packet = BytesIO()
                can = canvas.Canvas(packet, pagesize=letter)

                # Add exhibit number at top center (only on first page)
                if page_num == 0:
                    can.setFont("Helvetica-Bold", 10)
                    can.drawCentredString(
                        letter[0] / 2,  # Center of page
                        letter[1] - 0.5 * inch,  # 0.5 inch from top
                        f"Exhibit {exhibit_number}"
                    )

                # Add page number at bottom
                can.setFont("Helvetica", 9)
                can.drawCentredString(
                    letter[0] / 2,
                    0.5 * inch,
                    f"Page {page_num + 1} of {len(reader.pages)}"
                )

                can.save()

                # Merge overlay with original page
                packet.seek(0)
                overlay = PdfReader(packet)
                page.merge_page(overlay.pages[0])
                writer.add_page(page)

            # Save numbered PDF
            output_path = os.path.join(
                self.temp_dir,
                f"Exhibit_{exhibit_number}_{os.path.basename(pdf_path)}"
            )

            with open(output_path, 'wb') as output_file:
                writer.write(output_file)

            return output_path

        except Exception as e:
            print(f"Error adding exhibit number: {e}")
            return pdf_path  # Return original if numbering fails

    def merge_pdfs(self, pdf_paths: List[str], output_path: str) -> str:
        """Merge multiple PDFs into a single file.

        Args:
            pdf_paths: List of PDF file paths
            output_path: Full path for the merged output PDF

        Returns:
            Path to merged PDF
        """
        merger = PdfMerger()

        for pdf_path in pdf_paths:
            if os.path.exists(pdf_path):
                merger.append(pdf_path)

        merger.write(output_path)
        merger.close()

        return output_path

    def generate_toc(
        self,
        exhibits: List[Dict],
        case_name: str,
        beneficiary_name: Optional[str] = None
    ) -> str:
        """
        Generate professional Table of Contents

        Args:
            exhibits: List of exhibit dictionaries
            case_name: Case name/ID
            beneficiary_name: Optional beneficiary name

        Returns:
            Path to TOC PDF
        """
        output_path = os.path.join(self.temp_dir, f"{case_name}_TOC.pdf")

        doc = SimpleDocTemplate(
            output_path,
            pagesize=letter,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=18
        )

        # Container for elements
        elements = []
        styles = getSampleStyleSheet()

        # Custom styles
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#1f77b4'),
            spaceAfter=30,
            alignment=1  # Center
        )

        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=16,
            textColor=colors.HexColor('#333333'),
            spaceAfter=12,
            spaceBefore=12
        )

        # Title
        elements.append(Paragraph("EXHIBIT PACKAGE", title_style))
        elements.append(Paragraph("TABLE OF CONTENTS", title_style))
        elements.append(Spacer(1, 0.3 * inch))

        # Case information box
        case_info = [
            ["Case ID:", case_name],
            ["Generated:", datetime.now().strftime("%B %d, %Y")],
            ["Total Exhibits:", str(len(exhibits))]
        ]

        if beneficiary_name:
            case_info.insert(1, ["Beneficiary:", beneficiary_name])

        info_table = Table(case_info, colWidths=[2 * inch, 4 * inch])
        info_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f0f0f0')),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
            ('ALIGN', (1, 0), (1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 12),
            ('RIGHTPADDING', (0, 0), (-1, -1), 12),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))

        elements.append(info_table)
        elements.append(Spacer(1, 0.5 * inch))

        # Exhibit List heading
        elements.append(Paragraph("Exhibit List", heading_style))
        elements.append(Spacer(1, 0.2 * inch))

        # Exhibit table
        exhibit_data = [["Exhibit", "Title/Description", "Status"]]

        for exhibit in exhibits:
            status = "✓ Generated" if exhibit.get('path') or exhibit.get('pdf_path') else "✗ Failed"
            exhibit_data.append([
                f"Exhibit {exhibit['number']}",
                exhibit['name'][:60] + "..." if len(exhibit['name']) > 60 else exhibit['name'],
                status
            ])

        exhibit_table = Table(
            exhibit_data,
            colWidths=[1.2 * inch, 4.3 * inch, 1 * inch]
        )

        exhibit_table.setStyle(TableStyle([
            # Header row
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1f77b4')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 11),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),

            # Data rows
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('ALIGN', (0, 1), (0, -1), 'CENTER'),
            ('ALIGN', (1, 1), (1, -1), 'LEFT'),
            ('ALIGN', (2, 1), (2, -1), 'CENTER'),

            # Grid
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f9f9f9')]),

            # Padding
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))

        elements.append(exhibit_table)

        # Archive URLs section (if any exhibits have URLs)
        archived_exhibits = [ex for ex in exhibits if ex.get('archive_url') or ex.get('original_url')]

        if archived_exhibits:
            elements.append(Spacer(1, 0.5 * inch))
            elements.append(Paragraph("Archived URLs (archive.org)", heading_style))
            elements.append(Spacer(1, 0.2 * inch))

            url_data = [["Exhibit", "Original URL", "Archived URL"]]

            for exhibit in archived_exhibits:
                url_data.append([
                    f"Exhibit {exhibit['number']}",
                    exhibit.get('original_url', 'N/A')[:40] + "...",
                    exhibit.get('archive_url', 'N/A')[:40] + "..."
                ])

            url_table = Table(url_data, colWidths=[1 * inch, 2.5 * inch, 2.5 * inch])
            url_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1f77b4')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 9),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 8),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f9f9f9')]),
                ('LEFTPADDING', (0, 0), (-1, -1), 6),
                ('RIGHTPADDING', (0, 0), (-1, -1), 6),
                ('TOPPADDING', (0, 0), (-1, -1), 4),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ]))

            elements.append(url_table)

        # Footer
        elements.append(Spacer(1, 0.5 * inch))
        footer_style = ParagraphStyle(
            'Footer',
            parent=styles['Normal'],
            fontSize=9,
            textColor=colors.grey,
            alignment=1  # Center
        )

        elements.append(Paragraph(
            "This exhibit package was generated automatically.",
            footer_style
        ))
        elements.append(Paragraph(
            "All source URLs have been archived to archive.org for preservation.",
            footer_style
        ))

        # Build PDF
        doc.build(elements)

        return output_path

    def create_text_and_images_pdf(self, pdf_path: str, extracted_text: Optional[str] = None, content_bytes: Optional[bytes] = None) -> Optional[str]:
        """Create a PDF containing the extracted text and extracted images from a source PDF.

        Returns path to generated PDF or None on failure.
        """
        try:
            out_path = os.path.join(self.temp_dir, f"{os.path.splitext(os.path.basename(pdf_path))[0]}_TEXT_IMAGES.pdf")

            # Get text: prefer provided extracted_text, otherwise try reading from PDF
            text = extracted_text
            if not text:
                try:
                    reader = PdfReader(pdf_path)
                    pages_text = []
                    for p in reader.pages:
                        pages_text.append(p.extract_text() or "")
                    text = "\n\n".join(pages_text)
                except Exception:
                    text = None

            # Start building the PDF with reportlab
            doc = SimpleDocTemplate(out_path, pagesize=letter, rightMargin=72, leftMargin=72, topMargin=72, bottomMargin=72)
            styles = getSampleStyleSheet()
            elements = []

            if text:
                # Break text into paragraphs
                paragraphs = text.split('\n')
                para_style = ParagraphStyle('Body', parent=styles['Normal'], fontSize=10, leading=13)
                for p in paragraphs:
                    if p.strip():
                        elements.append(Paragraph(p.strip(), para_style))
                        elements.append(Spacer(1, 6))
                elements.append(PageBreak())

            # Try to extract images using PyMuPDF if available
            images = []
            try:
                import fitz  # PyMuPDF
                docm = None
                if content_bytes:
                    # load from bytes
                    docm = fitz.open(stream=content_bytes, filetype='pdf')
                else:
                    docm = fitz.open(pdf_path)

                for i in range(len(docm)):
                    page = docm[i]
                    for img in page.get_images(full=True):
                        xref = img[0]
                        base_image = docm.extract_image(xref)
                        image_bytes = base_image.get('image')
                        ext = base_image.get('ext', 'png')
                        tmp_img = os.path.join(self.temp_dir, f"img_{os.path.basename(pdf_path)}_{i}_{xref}.{ext}")
                        with open(tmp_img, 'wb') as imf:
                            imf.write(image_bytes)
                        images.append(tmp_img)
            except Exception:
                # If PyMuPDF not installed or extraction fails, skip images
                images = []

            # Add image pages
            from reportlab.platypus import Image as RLImage
            for img_path in images:
                try:
                    elements.append(Paragraph('Image extracted from original PDF', styles['Heading3']))
                    elements.append(Spacer(1, 12))
                    im = RLImage(img_path, width=6*inch, height=6*inch)
                    elements.append(im)
                    elements.append(PageBreak())
                except Exception:
                    continue

            if not elements:
                return None

            doc.build(elements)
            return out_path
        except Exception as e:
            print(f"Error creating text/images PDF: {e}")
            return None

    def url_to_pdf(self, url: str) -> Optional[str]:
        """
        Convert URL to PDF (requires external service or API2PDF)

        Args:
            url: URL to convert

        Returns:
            Path to generated PDF or None
        """
        # This would require API2PDF or similar service
        # For now, return None - implement when API key available
        print(f"URL to PDF conversion requires API2PDF: {url}")
        return None

    def generate_table_of_contents(
        self,
        exhibit_list: List[Dict],
        visa_type: str,
        output_path: str
    ) -> str:
        """
        Generate Table of Contents PDF

        Args:
            exhibit_list: List of exhibit dictionaries with number, title, pages
            visa_type: Visa category (O-1A, P-1A, etc.)
            output_path: Path for output PDF

        Returns:
            Path to generated TOC PDF
        """
        doc = SimpleDocTemplate(output_path, pagesize=letter)
        story = []
        styles = getSampleStyleSheet()

        # Title
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#1f77b4'),
            spaceAfter=30,
            alignment=1  # Center
        )
        story.append(Paragraph("EXHIBIT PACKAGE", title_style))
        story.append(Paragraph("TABLE OF CONTENTS", title_style))
        story.append(Spacer(1, 0.5*inch))

        # Case info
        info_style = ParagraphStyle(
            'Info',
            parent=styles['Normal'],
            fontSize=11,
            spaceAfter=20
        )
        info_text = f"""
        <b>Visa Type:</b> {visa_type}<br/>
        <b>Generated:</b> {datetime.now().strftime('%B %d, %Y')}<br/>
        <b>Total Exhibits:</b> {len(exhibit_list)}
        """
        story.append(Paragraph(info_text, info_style))
        story.append(Spacer(1, 0.3*inch))

        # Exhibit table
        table_data = [['Exhibit', 'Title', 'Pages']]

        for exhibit in exhibit_list:
            table_data.append([
                f"Exhibit {exhibit['number']}",
                exhibit['title'][:50],  # Truncate long titles
                str(exhibit.get('pages', '-'))
            ])

        table = Table(table_data, colWidths=[1.5*inch, 4*inch, 1*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey])
        ]))

        story.append(table)

        # Build PDF
        doc.build(story)
        return output_path
