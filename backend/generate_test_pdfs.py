"""
Generate 3 realistic sustainability report PDFs for testing GreenLens AI.

Each document is designed to trigger different greenwashing flags:
1. EcoFresh_SustainabilityReport_2025.pdf  -  Vague claims + no third-party verification
2. GreenTech_ESG_Disclosure_2025.pdf  -  Contradictions between marketing and data
3. NaturePure_PackagingClaims_2025.pdf  -  Hidden trade-offs + cherry-picked metrics

Run: python generate_test_pdfs.py
Output: 3 PDF files in backend/test_docs/
"""

import os

def generate_pdfs():
    """Generate test PDFs using fpdf2 (lightweight, no external dependencies beyond fpdf2)."""
    try:
        from fpdf import FPDF
    except ImportError:
        print("fpdf2 not installed. Generating text-based test files instead.")
        print("Install with: pip install fpdf2")
        generate_text_files()
        return

    output_dir = os.path.join(os.path.dirname(__file__), "test_docs")
    os.makedirs(output_dir, exist_ok=True)

    def safe_text(text):
        """Replace Unicode chars that Helvetica can't handle."""
        return text.replace("\u2014", "-").replace("\u2013", "-").replace("\u2018", "'").replace("\u2019", "'").replace("\u201c", '"').replace("\u201d", '"')

    output_dir = os.path.join(os.path.dirname(__file__), "test_docs")
    os.makedirs(output_dir, exist_ok=True)

    # --- Document 1: EcoFresh Beverage Co. ---
    pdf1 = FPDF()
    pdf1.add_page()
    pdf1.set_font("Helvetica", "B", 16)
    pdf1.cell(0, 10, "EcoFresh Beverage Co.", ln=True, align="C")
    pdf1.set_font("Helvetica", "B", 14)
    pdf1.cell(0, 10, "Sustainability Report 2025", ln=True, align="C")
    pdf1.ln(10)
    pdf1.set_font("Helvetica", "", 11)

    doc1_text = """Executive Summary

EcoFresh Beverage Co. is committed to a sustainable future. Our eco-friendly products are made with natural ingredients and we are dedicated to protecting the planet for future generations. We believe in green innovation and responsible business practices.

Our Sustainability Commitments

- We are working towards carbon neutrality by 2030
- Our packaging is designed to be environmentally responsible
- We source ingredients from sustainable suppliers
- Our facilities use renewable energy solutions

Environmental Performance

Total carbon emissions (Scope 1 & 2): 142,000 tonnes CO2e (2024)
Previous year emissions: 138,000 tonnes CO2e (2023)
Note: Scope 3 emissions are not currently tracked.

Our bottles are made with "up to 30% recycled content"  -  leading the industry in sustainable packaging innovation. We have eliminated single-use plastic straws from our product line, replacing them with paper alternatives.

Water Usage: 4.2 billion liters consumed in manufacturing (2024)
Water Reduction Target: Reduce water intensity by 5% by 2030 (from 2024 baseline)

Certifications and Standards
We follow our own internal EcoFresh Green Standard for all sustainability assessments. Our sustainability team conducts annual self-audits to ensure compliance with our internal guidelines.

Community Impact
EcoFresh donated $500,000 to environmental charities in 2024, representing 0.02% of our $2.5 billion annual revenue.

Looking Ahead
We remain committed to our journey toward a more sustainable future. Our team is exploring various options to reduce our environmental footprint and we look forward to sharing more updates in the coming years."""

    for para in doc1_text.split("\n\n"):
        if para.strip().startswith(("Executive", "Our Sustainability", "Environmental", "Certifications", "Community", "Looking", "Water")):
            pdf1.set_font("Helvetica", "B", 12)
            pdf1.multi_cell(0, 6, safe_text(para.strip()))
            pdf1.set_font("Helvetica", "", 11)
        else:
            pdf1.multi_cell(0, 6, safe_text(para.strip()))
        pdf1.ln(4)

    pdf1.output(os.path.join(output_dir, "EcoFresh_SustainabilityReport_2025.pdf"))
    print("Created: EcoFresh_SustainabilityReport_2025.pdf")

    # --- Document 2: GreenTech Solutions ---
    pdf2 = FPDF()
    pdf2.add_page()
    pdf2.set_font("Helvetica", "B", 16)
    pdf2.cell(0, 10, "GreenTech Solutions Inc.", ln=True, align="C")
    pdf2.set_font("Helvetica", "B", 14)
    pdf2.cell(0, 10, "ESG Disclosure & Annual Impact Report 2025", ln=True, align="C")
    pdf2.ln(10)
    pdf2.set_font("Helvetica", "", 11)

    doc2_text = """CEO Letter: A Carbon Neutral Future

I am proud to announce that GreenTech Solutions achieved carbon neutrality in 2024. Our commitment to net-zero emissions demonstrates that technology companies can lead the climate transition while delivering shareholder value. We offset 100% of our operational emissions through verified carbon credits.

Emissions Data (Audited by Deloitte)

Scope 1 (Direct): 8,200 tonnes CO2e
Scope 2 (Electricity): 45,600 tonnes CO2e  
Scope 3 (Supply Chain): 892,000 tonnes CO2e
TOTAL: 945,800 tonnes CO2e

Carbon Offset Portfolio:
- Forestry credits (Brazil): 35,000 tonnes (verified VCS)
- Renewable energy credits: 18,800 tonnes (Gold Standard)
Total offsets purchased: 53,800 tonnes

Note: Carbon neutrality claim covers Scope 1 and Scope 2 only (53,800 tonnes offset against 53,800 tonnes emitted). Scope 3 emissions (892,000 tonnes) representing 94.3% of total emissions are excluded from the neutrality boundary.

Renewable Energy

Marketing Statement: "Powered by 100% renewable energy"
Actual breakdown:
- Direct renewable PPAs: 22% of total electricity
- Unbundled RECs (Renewable Energy Certificates): 78% of total electricity
Note: Unbundled RECs do not represent actual delivery of renewable electrons. They are accounting instruments that can be purchased separately from physical electricity supply.

Supply Chain

We require all Tier 1 suppliers to sign our Sustainability Pledge. Current compliance:
- Tier 1 suppliers signed: 67%
- Tier 1 suppliers audited: 12%
- Tier 2+ suppliers assessed: 0%

Our products contain conflict minerals sourced from regions with known human rights concerns. We are developing a responsible minerals policy (target publication: 2027).

Waste and Circular Economy

E-waste generated: 14,200 tonnes (2024)
E-waste recycled: 2,100 tonnes (14.8%)
Remaining 85.2% sent to landfill or incineration.

Marketing claim: "Industry-leading e-waste recycling program"
Industry average recycling rate: 17.4% (EPA 2024 data)"""

    for para in doc2_text.split("\n\n"):
        if para.strip().startswith(("CEO Letter", "Emissions Data", "Carbon Offset", "Renewable", "Supply Chain", "Waste", "Marketing")):
            pdf2.set_font("Helvetica", "B", 12)
            pdf2.multi_cell(0, 6, safe_text(para.strip()))
            pdf2.set_font("Helvetica", "", 11)
        else:
            pdf2.multi_cell(0, 6, safe_text(para.strip()))
        pdf2.ln(4)

    pdf2.output(os.path.join(output_dir, "GreenTech_ESG_Disclosure_2025.pdf"))
    print("Created: GreenTech_ESG_Disclosure_2025.pdf")

    # --- Document 3: NaturePure Cosmetics ---
    pdf3 = FPDF()
    pdf3.add_page()
    pdf3.set_font("Helvetica", "B", 16)
    pdf3.cell(0, 10, "NaturePure Cosmetics", ln=True, align="C")
    pdf3.set_font("Helvetica", "B", 14)
    pdf3.cell(0, 10, "Product Sustainability & Packaging Claims 2025", ln=True, align="C")
    pdf3.ln(10)
    pdf3.set_font("Helvetica", "", 11)

    doc3_text = """Product Line Overview

NaturePure is 100% committed to clean beauty. All our products are natural, eco-friendly, and designed with the planet in mind. Our packaging is sustainable and our formulas are green.

Packaging Claims (as printed on product labels)

Front of Package:
- "100% Recyclable Packaging"
- "Made with Ocean-Bound Plastic"  
- "Plastic Negative - We Remove More Than We Use"
- "Biodegradable Formula"
- "Carbon Neutral Product"

Fine Print (back label, 6pt font):
- "Recyclability varies by municipality. Check local recycling guidelines."
- "Ocean-bound plastic: outer carton only (represents 8% of total packaging weight). Primary container is virgin PET plastic."
- "Plastic negativity calculated using credit system. Credits purchased from third-party collection programs in Southeast Asia. No direct removal from oceans."
- "Biodegradability tested under industrial composting conditions (58C, 90 days). Product will NOT biodegrade in home compost, landfill, or marine environments."
- "Carbon neutrality achieved through purchase of carbon credits. Product lifecycle emissions: 2.4 kg CO2e per unit."

Ingredient Sourcing

Marketing: "Ethically sourced from small farms"
Reality: 73% of raw materials purchased through commodity brokers. Direct farm relationships exist for 4 of 47 ingredients (8.5%).

Palm oil derivative present in 28 of 35 product SKUs. RSPO certification: "Mass Balance" level (allows mixing certified and non-certified palm oil in supply chain).

Animal Testing Statement: "Cruelty-free and never tested on animals"
Footnote: "NaturePure does not test on animals. However, some ingredients may have been tested on animals by our raw material suppliers prior to our procurement. NaturePure does not conduct or commission animal testing for finished products sold in markets that do not require it."

Environmental Metrics

Total plastic used in packaging: 890 tonnes (2024)
Previous year: 820 tonnes (2023)  -  8.5% INCREASE
Marketing claim: "Reducing our plastic footprint year over year"
Basis for claim: Plastic per unit decreased 2% (due to increased sales volume, not absolute reduction)

Water footprint: 12.4 million liters (manufacturing only)
Full lifecycle water footprint (including ingredient farming): 340 million liters
Marketing reference: "Low water footprint manufacturing"

Certifications Held:
- Leaping Bunny (cruelty-free  -  finished products only)
- FSC (paper cartons only  -  15% of packaging by weight)
Certifications NOT held: B Corp, ISO 14001, EWG Verified, USDA Organic"""

    for para in doc3_text.split("\n\n"):
        if para.strip().startswith(("Product Line", "Packaging Claims", "Front of", "Fine Print", "Ingredient", "Animal", "Environmental", "Marketing", "Certifications")):
            pdf3.set_font("Helvetica", "B", 12)
            pdf3.multi_cell(0, 6, safe_text(para.strip()))
            pdf3.set_font("Helvetica", "", 11)
        else:
            pdf3.multi_cell(0, 6, safe_text(para.strip()))
        pdf3.ln(4)

    pdf3.output(os.path.join(output_dir, "NaturePure_PackagingClaims_2025.pdf"))
    print("Created: NaturePure_PackagingClaims_2025.pdf")

    print(f"\n3 test PDFs generated in: {output_dir}/")
    print("Upload these to GreenLens to test the analysis pipeline.")


def generate_text_files():
    """Fallback: generate .txt versions if fpdf2 is not available."""
    output_dir = os.path.join(os.path.dirname(__file__), "test_docs")
    os.makedirs(output_dir, exist_ok=True)

    # Just inform the user to install fpdf2
    print(f"\nTo generate proper PDFs, run:")
    print(f"  pip install fpdf2")
    print(f"  python generate_test_pdfs.py")
    print(f"\nAlternatively, you can copy the text content from this script into PDF files manually.")


if __name__ == "__main__":
    generate_pdfs()
