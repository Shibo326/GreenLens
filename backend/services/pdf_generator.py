import io
import logging
import os
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm, mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    HRFlowable,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from models.response import AnalysisResult

logger = logging.getLogger(__name__)

# ─── Unicode Font Registration ────────────────────────────────────────────────
# Register DejaVu Sans for full Unicode support (₱, $, €, etc.)
# Falls back to Helvetica if DejaVu not found (no crash, just black boxes)
_FONT_REGISTERED = False

def _register_unicode_fonts():
    global _FONT_REGISTERED
    if _FONT_REGISTERED:
        return

    # Common locations for DejaVu fonts
    search_paths = [
        # Linux (Railway/Docker)
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        # macOS
        "/Library/Fonts/DejaVuSans.ttf",
        # Windows
        "C:/Windows/Fonts/DejaVuSans.ttf",
        # Python package (reportlab ships with some fonts)
        os.path.join(os.path.dirname(__file__), "fonts", "DejaVuSans.ttf"),
    ]

    regular = None
    bold = None

    for path in search_paths:
        if os.path.exists(path):
            regular = path
            bold_path = path.replace("DejaVuSans.ttf", "DejaVuSans-Bold.ttf")
            if os.path.exists(bold_path):
                bold = bold_path
            break

    if regular:
        try:
            pdfmetrics.registerFont(TTFont("DejaVuSans", regular))
            if bold:
                pdfmetrics.registerFont(TTFont("DejaVuSans-Bold", bold))
            else:
                pdfmetrics.registerFont(TTFont("DejaVuSans-Bold", regular))
            from reportlab.lib.fonts import addMapping
            addMapping("DejaVuSans", 0, 0, "DejaVuSans")
            addMapping("DejaVuSans", 1, 0, "DejaVuSans-Bold")
            _FONT_REGISTERED = True
            logger.info("DejaVu Unicode fonts registered for PDF generation")
        except Exception as e:
            logger.warning(f"Could not register DejaVu fonts: {e} — falling back to Helvetica")
    else:
        # Try to download/install DejaVu via reportlab's findSystemFonts
        try:
            from reportlab.pdfbase.ttfonts import TTFont
            import urllib.request, tempfile, shutil

            url = "https://github.com/dejavu-fonts/dejavu-fonts/raw/master/ttf/DejaVuSans.ttf"
            url_bold = "https://github.com/dejavu-fonts/dejavu-fonts/raw/master/ttf/DejaVuSans-Bold.ttf"
            fonts_dir = os.path.join(os.path.dirname(__file__), "fonts")
            os.makedirs(fonts_dir, exist_ok=True)

            reg_path = os.path.join(fonts_dir, "DejaVuSans.ttf")
            bold_path = os.path.join(fonts_dir, "DejaVuSans-Bold.ttf")

            if not os.path.exists(reg_path):
                urllib.request.urlretrieve(url, reg_path)
            if not os.path.exists(bold_path):
                urllib.request.urlretrieve(url_bold, bold_path)

            pdfmetrics.registerFont(TTFont("DejaVuSans", reg_path))
            pdfmetrics.registerFont(TTFont("DejaVuSans-Bold", bold_path))
            _FONT_REGISTERED = True
            logger.info("DejaVu fonts downloaded and registered")
        except Exception as e:
            logger.warning(f"Could not download DejaVu fonts: {e} — using Helvetica (₱ may show as box)")

def _F(bold=False) -> str:
    """Return the best available font name."""
    if _FONT_REGISTERED:
        return "DejaVuSans-Bold" if bold else "DejaVuSans"
    return "Helvetica-Bold" if bold else "Helvetica"

def _sanitize(text: str) -> str:
    """Replace currency symbols with safe equivalents if Unicode font not available."""
    if _FONT_REGISTERED:
        return text  # Unicode font handles everything
    # Fallback replacements when only Helvetica is available
    return (text
        .replace("₱", "PHP ")
        .replace("€", "EUR ")
        .replace("£", "GBP ")
        .replace("¥", "JPY ")
    )

# Register fonts at module load time
_register_unicode_fonts()

# ─── Color Palette (GreenLens) ────────────────────────────────────────────────
# Brand
LEAF = colors.HexColor("#3DDC84")           # primary green accent (leaf)
FOREST_DARK = colors.HexColor("#0A120E")    # deep forest header background
FOREST_HEADER = colors.HexColor("#131F19")  # secondary dark surface
# Greenwashing severity colors
SEV_HIGH = colors.HexColor("#F04452")   # MISLEADING (red)
SEV_MED = colors.HexColor("#F0A937")    # VAGUE (amber)
SEV_LOW = colors.HexColor("#5FA8D3")    # UNVERIFIED (blue)
# Neutrals
SLATE_900 = colors.HexColor("#1e293b")
SLATE_700 = colors.HexColor("#334155")
SLATE_500 = colors.HexColor("#64748b")
SLATE_300 = colors.HexColor("#cbd5e1")
SLATE_100 = colors.HexColor("#f1f5f9")
SLATE_50 = colors.HexColor("#f8fafc")
WHITE = colors.white
BLACK = colors.HexColor("#0f172a")
# Semantic
GREEN_600 = colors.HexColor("#16a34a")
GREEN_50 = colors.HexColor("#f0fdf4")
AMBER_600 = colors.HexColor("#d97706")
AMBER_50 = colors.HexColor("#fffbeb")
RED_50 = colors.HexColor("#fef2f2")
BLUE_50 = colors.HexColor("#eff6ff")
BLUE_700 = colors.HexColor("#1d4ed8")
CYAN_500 = colors.HexColor("#06b6d4")

# Greenwash severity display labels (mapped from Risk.level)
SEVERITY_LABEL = {"HIGH": "MISLEADING", "MEDIUM": "VAGUE", "LOW": "UNVERIFIED"}


def _hex(color) -> str:
    """Convert a ReportLab color to a 6-digit hex string (no #)."""
    return f"{int(color.red*255):02x}{int(color.green*255):02x}{int(color.blue*255):02x}"


class PDFGenerator:
    """
    Generates modern, professionally-designed greenwashing analysis reports
    from AnalysisResult data.
    Uses a clean slate/forest color palette with GreenLens green accents.
    """

    LEAF = "#3DDC84"

    def __init__(self):
        self.styles = getSampleStyleSheet()
        self._build_styles()

    def _build_styles(self):
        """Define custom paragraph styles using Unicode-capable font."""
        F = _F()
        FB = _F(bold=True)

        self.title = ParagraphStyle(
            "RTitle", parent=self.styles["Title"],
            fontSize=32, textColor=WHITE, alignment=TA_CENTER,
            spaceAfter=8, fontName=FB, leading=38,
        )
        self.subtitle = ParagraphStyle(
            "RSub", parent=self.styles["Normal"],
            fontSize=13, textColor=SLATE_300, alignment=TA_CENTER,
            spaceAfter=6, fontName=F,
        )
        self.section = ParagraphStyle(
            "RSec", parent=self.styles["Heading1"],
            fontSize=15, textColor=SLATE_900, fontName=FB,
            spaceBefore=20, spaceAfter=6,
        )
        self.body = ParagraphStyle(
            "RBody", parent=self.styles["Normal"],
            fontSize=10, textColor=SLATE_700, fontName=F,
            spaceAfter=6, leading=15,
        )
        self.body_bold = ParagraphStyle(
            "RBodyB", parent=self.body,
            fontName=FB, textColor=SLATE_900,
        )
        self.small = ParagraphStyle(
            "RSmall", parent=self.styles["Normal"],
            fontSize=9, textColor=SLATE_500, fontName=F,
        )
        self.footer = ParagraphStyle(
            "RFoot", parent=self.styles["Normal"],
            fontSize=8, textColor=SLATE_500, alignment=TA_CENTER,
            fontName=F,
        )
        self.metric_label = ParagraphStyle(
            "RMetL", parent=self.styles["Normal"],
            fontSize=8, textColor=SLATE_500, alignment=TA_CENTER,
            fontName=FB, leading=11,
        )
        self.metric_value = ParagraphStyle(
            "RMetV", parent=self.styles["Normal"],
            fontSize=22, textColor=SLATE_900, alignment=TA_CENTER,
            fontName=FB, leading=26,
        )

    def generate_report(self, analysis: AnalysisResult, session_id: str) -> bytes:
        """Generate a complete PDF report."""
        buffer = io.BytesIO()
        today = datetime.utcnow().strftime("%B %d, %Y")

        doc = SimpleDocTemplate(
            buffer, pagesize=A4,
            rightMargin=2 * cm, leftMargin=2 * cm,
            topMargin=2 * cm, bottomMargin=2 * cm,
            title="GreenLens AI - Greenwashing Analysis Report",
            author="GreenLens AI",
        )

        story = []
        story.extend(self._title_page(today, session_id))
        story.append(PageBreak())
        story.extend(self._analytics_dashboard(analysis))
        story.extend(self._greenwash_score(analysis))
        story.extend(self._executive_summary(analysis))
        story.extend(self._risk_analysis(analysis))
        if analysis.comparisonMatrix:
            story.extend(self._comparison_matrix(analysis))
        if analysis.conflicts:
            story.extend(self._conflicts(analysis))
        story.extend(self._recommendation(analysis))
        story.extend(self._footer_block())

        doc.build(story)
        pdf_bytes = buffer.getvalue()
        buffer.close()
        logger.info(f"PDF generated for session {session_id} ({len(pdf_bytes)} bytes)")
        return pdf_bytes

    def _title_page(self, today: str, session_id: str) -> list:
        """Build a premium title page with gradient-style dark header and professional branding."""
        elements = []
        elements.append(Spacer(1, 5 * cm))

        # Main title block — larger, more breathing room
        title_data = [
            [Spacer(1, 0.5 * cm)],
            [Paragraph("GREENLENS AI", ParagraphStyle(
                "BigTitle", parent=self.title, fontSize=38, leading=44, spaceAfter=4,
            ))],
            [Paragraph("GreenLens — Greenwashing Analysis Report", ParagraphStyle(
                "SubTitle2", parent=self.subtitle, fontSize=14, spaceAfter=12,
            ))],
            [HRFlowable(width="40%", thickness=1, color=LEAF)],
            [Spacer(1, 0.3 * cm)],
            [Paragraph(
                f'<font color="#{_hex(LEAF)}">GreenLens AI — Greenwashing Detection</font>',
                ParagraphStyle("Badge", parent=self.subtitle, fontSize=11,
                               fontName=_F(bold=True), textColor=LEAF),
            )],
            [Spacer(1, 0.3 * cm)],
        ]
        title_table = Table(title_data, colWidths=[16 * cm])
        title_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), FOREST_DARK),
            ("TOPPADDING", (0, 0), (0, 0), 40),
            ("BOTTOMPADDING", (0, -1), (-1, -1), 32),
            ("LEFTPADDING", (0, 0), (-1, -1), 24),
            ("RIGHTPADDING", (0, 0), (-1, -1), 24),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("ROUNDEDCORNERS", [10, 10, 10, 10]),
        ]))
        elements.append(title_table)
        elements.append(Spacer(1, 2 * cm))

        # Metadata card — cleaner, more spacing
        sid_display = session_id[:8] + "..." if len(session_id) > 8 else session_id
        meta_data = [
            [Paragraph("<b>Report Date</b>", self.small),
             Paragraph("<b>Session ID</b>", self.small),
             Paragraph("<b>Platform</b>", self.small)],
            [Paragraph(today, self.body),
             Paragraph(sid_display, self.body),
             Paragraph("GreenLens AI v1.0", self.body)],

        ]
        meta_table = Table(meta_data, colWidths=[5.3 * cm, 5.3 * cm, 5.4 * cm])
        meta_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), SLATE_100),
            ("BACKGROUND", (0, 1), (-1, 1), WHITE),
            ("BOX", (0, 0), (-1, -1), 0.75, SLATE_300),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, SLATE_300),
            ("TOPPADDING", (0, 0), (-1, -1), 12),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
            ("LEFTPADDING", (0, 0), (-1, -1), 14),
            ("RIGHTPADDING", (0, 0), (-1, -1), 14),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ]))
        elements.append(meta_table)
        elements.append(Spacer(1, 2 * cm))

        # Confidentiality notice
        elements.append(Paragraph(
            "<i>This report is generated by GreenLens AI for internal decision-making purposes. "
            "All findings are evidence-based and sourced from the uploaded documents.</i>",
            ParagraphStyle("Conf", parent=self.small, alignment=TA_CENTER, leading=13),
        ))
        return elements

    def _analytics_dashboard(self, analysis: AnalysisResult) -> list:
        """Build analytics dashboard with colored metric cards."""
        elements = []
        elements.append(Paragraph("Analytics Dashboard", self.section))
        elements.append(HRFlowable(width="100%", thickness=1.5, color=LEAF))
        elements.append(Spacer(1, 0.5 * cm))

        # Calculate metrics
        total_risks = len(analysis.risks)
        high = len([r for r in analysis.risks if r.level == "HIGH"])
        med = len([r for r in analysis.risks if r.level == "MEDIUM"])
        low = len([r for r in analysis.risks if r.level == "LOW"])
        conflicts = len(analysis.conflicts)
        confidence = int(analysis.recommendation.confidence * 100)

        # Determine colors for values
        flag_color = SEV_HIGH if high > 0 else SEV_MED if med > 0 else GREEN_600
        conf_color = GREEN_600 if confidence >= 70 else AMBER_600 if confidence >= 40 else SEV_HIGH
        conflict_color = SEV_HIGH if conflicts > 0 else GREEN_600

        # Metric cards - 4 columns
        labels_row = [
            Paragraph("GREENWASH FLAGS", self.metric_label),
            Paragraph("MISLEADING", self.metric_label),
            Paragraph("CONTRADICTIONS", self.metric_label),
            Paragraph("AI CONFIDENCE", self.metric_label),
        ]
        values_row = [
            Paragraph(f"<b>{total_risks}</b>", ParagraphStyle("V1", parent=self.metric_value, textColor=flag_color)),
            Paragraph(f"<b>{high}</b>", ParagraphStyle("V2", parent=self.metric_value, textColor=SEV_HIGH if high > 0 else GREEN_600)),
            Paragraph(f"<b>{conflicts}</b>", ParagraphStyle("V3", parent=self.metric_value, textColor=conflict_color)),
            Paragraph(f"<b>{confidence}%</b>", ParagraphStyle("V4", parent=self.metric_value, textColor=conf_color)),
        ]

        metric_table = Table([values_row, labels_row], colWidths=[4 * cm] * 4)
        metric_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), SLATE_50),
            ("BOX", (0, 0), (-1, -1), 1, SLATE_300),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, SLATE_300),
            ("TOPPADDING", (0, 0), (-1, 0), 14),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 4),
            ("TOPPADDING", (0, 1), (-1, 1), 2),
            ("BOTTOMPADDING", (0, 1), (-1, 1), 12),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ]))
        elements.append(metric_table)
        elements.append(Spacer(1, 0.5 * cm))

        # Greenwash flag breakdown visual bar
        if total_risks > 0:
            breakdown_parts = []
            if high > 0:
                breakdown_parts.append(f'<font color="#{_hex(SEV_HIGH)}"><b>{high} MISLEADING</b></font>')
            if med > 0:
                breakdown_parts.append(f'<font color="#{_hex(SEV_MED)}"><b>{med} VAGUE</b></font>')
            if low > 0:
                breakdown_parts.append(f'<font color="#{_hex(SEV_LOW)}"><b>{low} UNVERIFIED</b></font>')
            elements.append(Paragraph(
                f"Flag Breakdown:  {'  |  '.join(breakdown_parts)}", self.body
            ))

        # Categories
        categories = sorted(set(r.category for r in analysis.risks))
        if categories:
            elements.append(Paragraph(
                f"<b>Categories:</b> {', '.join(categories)}", self.body
            ))

        elements.append(Spacer(1, 0.8 * cm))
        return elements

    def _executive_summary(self, analysis: AnalysisResult) -> list:
        """Build executive summary with a professional left-border highlight card."""
        elements = []
        elements.append(Paragraph("Executive Summary", self.section))
        elements.append(HRFlowable(width="100%", thickness=0.5, color=SLATE_300))
        elements.append(Spacer(1, 0.4 * cm))

        # Summary in a left-bordered card (consulting report style)
        summary_data = [[Paragraph(_sanitize(analysis.executiveSummary), ParagraphStyle(
            "SumBody", parent=self.body, leading=17, spaceAfter=0, fontSize=10.5,
        ))]]
        summary_table = Table(summary_data, colWidths=[15.5 * cm])
        summary_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), SLATE_50),
            ("BOX", (0, 0), (-1, -1), 0.5, SLATE_300),
            ("LEFTPADDING", (0, 0), (-1, -1), 18),
            ("RIGHTPADDING", (0, 0), (-1, -1), 16),
            ("TOPPADDING", (0, 0), (-1, -1), 16),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 16),
            # Left accent border
            ("LINEBEFOREDECOR", (0, 0), (0, -1), 3, LEAF),
        ]))
        elements.append(summary_table)
        elements.append(Spacer(1, 1 * cm))
        return elements

    def _greenwash_score(self, analysis: AnalysisResult) -> list:
        """Build a prominent Greenwash Score callout card near the top of the report.

        Score bands (0-100):
          0-30   -> "Mostly Greenwashing"
          31-60  -> "Vague / Mixed Signals"
          61-100 -> "Credible"
        None is handled gracefully by showing "N/A".
        """
        elements = []
        elements.append(Paragraph("Greenwash Score", self.section))
        elements.append(HRFlowable(width="100%", thickness=1.5, color=LEAF))
        elements.append(Spacer(1, 0.5 * cm))

        score = analysis.greenwashScore

        if score is None:
            score_display = "N/A"
            band_label = "Not yet computed"
            band_color = SLATE_500
        else:
            score_display = f"{score}/100"
            if score <= 30:
                band_label = "Mostly Greenwashing"
                band_color = SEV_HIGH
            elif score <= 60:
                band_label = "Vague / Mixed Signals"
                band_color = SEV_MED
            else:
                band_label = "Credible"
                band_color = GREEN_600

        score_style = ParagraphStyle(
            "GwScore", parent=self.metric_value, fontSize=30, leading=34,
            textColor=band_color, alignment=TA_CENTER,
        )
        band_style = ParagraphStyle(
            "GwBand", parent=self.body, fontSize=13, leading=17,
            textColor=WHITE, fontName=_F(bold=True), alignment=TA_CENTER,
        )
        hint_style = ParagraphStyle(
            "GwHint", parent=self.small, textColor=SLATE_300, alignment=TA_CENTER,
        )

        card_data = [
            [Paragraph(f"<b>{score_display}</b>", score_style)],
            [Paragraph(band_label, band_style)],
            [Paragraph(
                "0-30 Mostly Greenwashing  |  31-60 Vague / Mixed Signals  |  61-100 Credible",
                hint_style,
            )],
        ]
        card = Table(card_data, colWidths=[16 * cm])
        card.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), FOREST_HEADER),
            ("TOPPADDING", (0, 0), (-1, 0), 18),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 4),
            ("TOPPADDING", (0, 1), (-1, 1), 2),
            ("BOTTOMPADDING", (0, 1), (-1, 1), 10),
            ("TOPPADDING", (0, 2), (-1, 2), 2),
            ("BOTTOMPADDING", (0, 2), (-1, 2), 14),
            ("LEFTPADDING", (0, 0), (-1, -1), 20),
            ("RIGHTPADDING", (0, 0), (-1, -1), 20),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ROUNDEDCORNERS", [8, 8, 8, 8]),
        ]))
        elements.append(card)
        elements.append(Spacer(1, 0.9 * cm))
        return elements

    def _risk_analysis(self, analysis: AnalysisResult) -> list:
        """Build the risk analysis table with clean styling."""
        elements = []
        elements.append(Paragraph("Greenwash Flags", self.section))
        elements.append(HRFlowable(width="100%", thickness=0.5, color=SLATE_300))
        elements.append(Spacer(1, 0.3 * cm))

        if not analysis.risks:
            elements.append(Paragraph(
                "No greenwashing flags identified — claims appear substantiated.",
                ParagraphStyle("NoRisk", parent=self.body, textColor=GREEN_600),
            ))
            elements.append(Spacer(1, 0.5 * cm))
            return elements

        # Header style for table cells
        hdr_style = ParagraphStyle("TH", parent=self.body, fontSize=9,
                                   textColor=WHITE, fontName="Helvetica-Bold")
        cell_style = ParagraphStyle("TD", parent=self.body, fontSize=9,
                                    textColor=SLATE_700, leading=13)

        table_data = [[
            Paragraph("FLAG", hdr_style),
            Paragraph("CATEGORY", hdr_style),
            Paragraph("DESCRIPTION", hdr_style),
            Paragraph("SOURCE", hdr_style),
        ]]

        level_text_color = {"HIGH": SEV_HIGH, "MEDIUM": SEV_MED, "LOW": SEV_LOW}
        level_bg = {"HIGH": RED_50, "MEDIUM": AMBER_50, "LOW": BLUE_50}

        row_styles = []
        for i, risk in enumerate(analysis.risks, start=1):
            tc = level_text_color.get(risk.level, BLACK)
            flag_label = SEVERITY_LABEL.get(risk.level, risk.level)
            table_data.append([
                Paragraph(f"<b>{flag_label}</b>", ParagraphStyle(
                    f"Lv{i}", parent=cell_style, textColor=tc, fontName="Helvetica-Bold")),
                Paragraph(risk.category, cell_style),
                Paragraph(_sanitize(risk.description), cell_style),
                Paragraph(risk.sourceDocument, ParagraphStyle(
                    f"Src{i}", parent=cell_style, fontSize=8, textColor=SLATE_500)),
            ])
            row_styles.append(("BACKGROUND", (0, i), (-1, i), level_bg.get(risk.level, WHITE)))

        table = Table(table_data, colWidths=[2.2*cm, 2.5*cm, 7.8*cm, 3.5*cm], repeatRows=1)
        style = TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), SLATE_900),
            ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
            ("FONTSIZE", (0, 0), (-1, 0), 9),
            ("GRID", (0, 0), (-1, -1), 0.5, SLATE_300),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING", (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ])
        for cmd in row_styles:
            style.add(*cmd)
        table.setStyle(style)
        elements.append(table)
        elements.append(Spacer(1, 0.8 * cm))
        return elements

    def _comparison_matrix(self, analysis: AnalysisResult) -> list:
        """Build comparison matrix — only called when data exists."""
        elements = []
        elements.append(Paragraph("Claim vs. Reality", self.section))
        elements.append(HRFlowable(width="100%", thickness=0.5, color=SLATE_300))
        elements.append(Spacer(1, 0.3 * cm))

        # Collect columns
        all_cols: list[str] = []
        for row in analysis.comparisonMatrix:
            for col in row.values.keys():
                if col not in all_cols:
                    all_cols.append(col)

        hdr_style = ParagraphStyle("CMH", parent=self.body, fontSize=9,
                                   textColor=WHITE, fontName="Helvetica-Bold")
        cell_style = ParagraphStyle("CMC", parent=self.body, fontSize=9, leading=13)

        # Header
        header = [Paragraph("ASPECT", hdr_style)]
        for col in all_cols:
            header.append(Paragraph(col.upper(), hdr_style))
        header.append(Paragraph("VERDICT", hdr_style))
        table_data = [header]

        for i, row in enumerate(analysis.comparisonMatrix):
            data_row = [Paragraph(f"<b>{row.field}</b>", cell_style)]
            for col in all_cols:
                val = row.values.get(col, "-")
                is_winner = row.winner == col
                s = ParagraphStyle(f"CM{i}{col}", parent=cell_style,
                    textColor=GREEN_600 if is_winner else SLATE_700,
                    fontName="Helvetica-Bold" if is_winner else "Helvetica")
                data_row.append(Paragraph(val, s))
            data_row.append(Paragraph(
                f"<b>{row.winner or '-'}</b>",
                ParagraphStyle(f"W{i}", parent=cell_style, textColor=GREEN_600, fontName="Helvetica-Bold"),
            ))
            table_data.append(data_row)

        num_cols = len(all_cols) + 2
        col_w = 16 * cm / num_cols
        table = Table(table_data, colWidths=[col_w] * num_cols, repeatRows=1)
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), SLATE_900),
            ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
            ("GRID", (0, 0), (-1, -1), 0.5, SLATE_300),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, SLATE_50]),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ]))
        elements.append(table)
        elements.append(Spacer(1, 0.8 * cm))
        return elements

    def _conflicts(self, analysis: AnalysisResult) -> list:
        """Build conflicts section — only called when conflicts exist."""
        elements = []
        elements.append(Paragraph("Contradictions Detected", self.section))
        elements.append(HRFlowable(width="100%", thickness=0.5, color=SLATE_300))
        elements.append(Spacer(1, 0.3 * cm))

        sev_color = {"HIGH": SEV_HIGH, "MEDIUM": SEV_MED, "LOW": SEV_LOW}

        for i, conflict in enumerate(analysis.conflicts, 1):
            sc = sev_color.get(conflict.severity, BLACK)
            block = []

            # Conflict title
            block.append(Paragraph(
                f'<b>#{i} {conflict.type}</b>  '
                f'<font color="#{_hex(sc)}"><b>[{conflict.severity}]</b></font>',
                self.body_bold,
            ))
            block.append(Spacer(1, 0.2 * cm))

            # Side-by-side excerpts
            excerpt_style = ParagraphStyle("Exc", parent=self.body, fontSize=9,
                                          textColor=SLATE_700, leading=13)
            doc_data = [
                [Paragraph(f"<b>{conflict.documentA.name}</b>", self.small),
                 Paragraph(f"<b>{conflict.documentB.name}</b>", self.small)],
                [Paragraph(f'"{_sanitize(conflict.documentA.excerpt)}"', excerpt_style),
                 Paragraph(f'"{_sanitize(conflict.documentB.excerpt)}"', excerpt_style)],
            ]
            doc_table = Table(doc_data, colWidths=[8 * cm, 8 * cm])
            doc_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), SLATE_100),
                ("BACKGROUND", (0, 1), (-1, 1), WHITE),
                ("BOX", (0, 0), (-1, -1), 0.5, SLATE_300),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, SLATE_300),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]))
            block.append(doc_table)
            block.append(Spacer(1, 0.2 * cm))

            block.append(Paragraph(
                f"<b>Explanation:</b> {_sanitize(conflict.explanation)}", self.body))
            block.append(Paragraph(
                f"<b>Action:</b> {_sanitize(conflict.recommendedAction)}",
                ParagraphStyle(f"Act{i}", parent=self.body, textColor=BLUE_700),
            ))
            block.append(Spacer(1, 0.4 * cm))

            elements.append(KeepTogether(block))
            if i < len(analysis.conflicts):
                elements.append(HRFlowable(width="100%", thickness=0.5, color=SLATE_300, spaceAfter=8))

        elements.append(Spacer(1, 0.5 * cm))
        return elements

    def _recommendation(self, analysis: AnalysisResult) -> list:
        """Build the recommendation section with a premium styled card."""
        elements = []
        rec = analysis.recommendation

        elements.append(Paragraph("Recommendation", self.section))
        elements.append(HRFlowable(width="100%", thickness=1.5, color=LEAF))
        elements.append(Spacer(1, 0.4 * cm))

        # Recommendation title in a bold accent card
        title_style = ParagraphStyle("RecT", parent=self.body, fontSize=13,
                                     textColor=WHITE, fontName=_F(bold=True),
                                     alignment=TA_CENTER, leading=18)
        title_data = [[Paragraph(_sanitize(rec.title), title_style)]]
        title_table = Table(title_data, colWidths=[16 * cm])
        title_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), SLATE_900),
            ("TOPPADDING", (0, 0), (-1, -1), 16),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 16),
            ("LEFTPADDING", (0, 0), (-1, -1), 20),
            ("RIGHTPADDING", (0, 0), (-1, -1), 20),
            ("ROUNDEDCORNERS", [6, 6, 6, 6]),
        ]))
        elements.append(title_table)
        elements.append(Spacer(1, 0.5 * cm))

        # Confidence indicator
        confidence_pct = int(rec.confidence * 100)
        conf_color = GREEN_600 if confidence_pct >= 70 else AMBER_600 if confidence_pct >= 40 else SEV_HIGH
        elements.append(Paragraph(
            f'<b>AI Confidence:</b>  '
            f'<font color="#{_hex(conf_color)}"><b>{confidence_pct}%</b></font>',
            self.body,
        ))
        elements.append(Spacer(1, 0.4 * cm))

        # Summary paragraph
        elements.append(Paragraph(_sanitize(rec.summary), ParagraphStyle(
            "RecSum", parent=self.body, leading=16, spaceAfter=8,
        )))
        elements.append(Spacer(1, 0.4 * cm))

        # Next steps as numbered action items in a professional card
        if rec.nextSteps:
            elements.append(Paragraph("<b>Next Steps</b>", self.body_bold))
            elements.append(Spacer(1, 0.3 * cm))
            step_rows = []
            for idx, step in enumerate(rec.nextSteps, 1):
                num_style = ParagraphStyle(
                    f"StN{idx}", parent=self.body, fontSize=11,
                    textColor=WHITE, fontName=_F(bold=True), alignment=TA_CENTER)
                step_rows.append([
                    Paragraph(f"<b>{idx}</b>", num_style),
                    Paragraph(_sanitize(step), ParagraphStyle(
                        f"StT{idx}", parent=self.body, leading=15)),
                ])
            step_table = Table(step_rows, colWidths=[1.4 * cm, 14.6 * cm])

            # Build step table styles with alternating num backgrounds
            step_styles = [
                ("BOX", (0, 0), (-1, -1), 0.75, SLATE_300),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, SLATE_300),
                ("TOPPADDING", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
                ("LEFTPADDING", (0, 0), (0, -1), 6),
                ("RIGHTPADDING", (0, 0), (0, -1), 6),
                ("LEFTPADDING", (1, 0), (1, -1), 12),
                ("RIGHTPADDING", (1, 0), (1, -1), 12),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("BACKGROUND", (1, 0), (1, -1), SLATE_50),
            ]
            # Color the number cells
            for idx in range(len(rec.nextSteps)):
                step_styles.append(("BACKGROUND", (0, idx), (0, idx), FOREST_HEADER))

            step_table.setStyle(TableStyle(step_styles))
            elements.append(step_table)

        elements.append(Spacer(1, 1 * cm))
        return elements

    def _footer_block(self) -> list:
        """Build a professional document footer with branding."""
        elements = []
        elements.append(Spacer(1, 0.5 * cm))
        elements.append(HRFlowable(width="100%", thickness=1.5, color=LEAF))
        elements.append(Spacer(1, 0.4 * cm))
        elements.append(Paragraph(
            "Generated by GreenLens AI  |  GreenLens AI — Greenwashing Detection  |  greenlens.app",
            self.footer,
        ))
        elements.append(Spacer(1, 0.2 * cm))
        elements.append(Paragraph(
            "This report was generated automatically using AI-powered greenwashing analysis. "
            "All findings are sourced directly from the uploaded documents.",
            ParagraphStyle("Disc", parent=self.footer, fontSize=7, textColor=SLATE_500),
        ))
        return elements
