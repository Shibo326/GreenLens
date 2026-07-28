"""
GreenLens Known Greenwashers Knowledge Base

A curated database of real-world greenwashing cases, regulatory fines, common tactics,
and industry benchmarks. This knowledge is injected into analysis prompts to help the AI:
1. Reference real precedents when detecting similar patterns
2. Cite specific regulatory actions as evidence of severity
3. Explain greenwashing tactics using real-world examples students can relate to
4. Provide context about what regulators consider misleading

Sources: ACCC (Australia), FTC (US), EU Green Claims Directive, ASIC, CMA (UK),
DGCCRF (France), court cases, NGO investigations (Greenpeace, ClientEarth, BEUC).

Last updated: July 2026
"""

# ─── REGULATORY FINES & ENFORCEMENT ACTIONS ──────────────────────────────────

ENFORCEMENT_CASES = [
    {
        "company": "Shein",
        "year": 2024,
        "jurisdiction": "France (DGCCRF)",
        "fine": "€40 million",
        "violation": "Record fine for misleading environmental claims across marketing materials",
        "lesson": "Fast fashion brands face massive fines for vague 'sustainable' claims without substantiation",
    },
    {
        "company": "15 European Car Makers",
        "year": 2025,
        "jurisdiction": "EU",
        "fine": "€600 million (total)",
        "violation": "Cartel making false claims about recycled content in vehicles",
        "lesson": "Industry-wide greenwashing cartels face massive collective penalties",
    },
    {
        "company": "DWS (Deutsche Bank asset manager)",
        "year": 2025,
        "jurisdiction": "Germany",
        "fine": "€25 million",
        "violation": "Misleading statements about ESG integration in investment decisions",
        "lesson": "Financial greenwashing (claiming investments are 'green' without proof) attracts significant fines",
    },
    {
        "company": "Coca-Cola",
        "year": 2025,
        "jurisdiction": "EU (BEUC complaint)",
        "fine": "Forced label changes (no monetary fine)",
        "violation": "'100% recycled plastic' claims on bottles when only the body (not cap/label) was recycled",
        "lesson": "Unqualified '100% recycled' claims must apply to the ENTIRE product, not just one component",
    },
    {
        "company": "Vanguard Renewables",
        "year": 2024,
        "jurisdiction": "Australia (ASIC)",
        "fine": "AU$12.9 million",
        "violation": "Misleading claims about sustainable investment products",
        "lesson": "'Green fund' labels must reflect actual portfolio holdings, not marketing aspirations",
    },
    {
        "company": "Apple",
        "year": 2024,
        "jurisdiction": "Germany (activist complaint)",
        "fine": "Voluntarily ceased advertising",
        "violation": "'Carbon neutral' claims for Apple Watch pressured by activists",
        "lesson": "Even tech giants face pressure to remove carbon neutral claims that don't cover full lifecycle",
    },
    {
        "company": "Adidas",
        "year": 2025,
        "jurisdiction": "Germany",
        "fine": "Cease and desist (lawsuit won by activists)",
        "violation": "Used term 'climate neutrality' without adequate substantiation",
        "lesson": "Courts are ruling that 'climate neutral' requires full scope coverage and verified offsets",
    },
    {
        "company": "TotalEnergies",
        "year": 2025,
        "jurisdiction": "France (Paris Court)",
        "fine": "Ordered to remove specific claims",
        "violation": "Court ruled company misled consumers by implying it's 'part of the solution to climate change' while expanding fossil fuel production",
        "lesson": "Companies cannot claim to be 'transitioning to renewables' while actively increasing fossil fuel investment",
    },
    {
        "company": "H&M",
        "year": 2022-2023,
        "jurisdiction": "USA (class action), Netherlands",
        "fine": "Class action filed (dismissed on standing, not merits)",
        "violation": "'Conscious Collection' marketing implied products were sustainable without clear definition or third-party certification",
        "lesson": "Vague collection names like 'Conscious', 'Green', 'Earth' without specific metrics are greenwashing",
    },
    {
        "company": "Nestlé, Danone",
        "year": 2023-2025,
        "jurisdiction": "EU (BEUC + ClientEarth)",
        "fine": "Forced labeling changes",
        "violation": "'100% recycled' claims on plastic water bottles when caps/labels were virgin plastic",
        "lesson": "Same pattern as Coca-Cola — partial recycled content cannot be marketed as 100%",
    },
]

# ─── THE SEVEN SINS OF GREENWASHING ──────────────────────────────────────────

SEVEN_SINS = [
    {
        "sin": "Hidden Trade-off",
        "description": "Claiming a product is 'green' based on one attribute while ignoring more significant environmental impacts",
        "example": "Paper from an unsustainably logged forest marketed as 'recyclable' — yes it's recyclable, but the deforestation impact is far worse",
        "student_analogy": "It's like saying your junk food is healthy because it's gluten-free, while ignoring it has 500 calories of sugar",
    },
    {
        "sin": "No Proof",
        "description": "Environmental claims without accessible supporting evidence or third-party certification",
        "example": "A brand claiming '50% less water used in production' with no audit report, no methodology, no baseline year",
        "student_analogy": "It's like putting 'Honor Student' on your resume without ever showing your grades to anyone",
    },
    {
        "sin": "Vagueness",
        "description": "Claims so broad or undefined they're meaningless — 'eco-friendly', 'green', 'natural', 'sustainable'",
        "example": "'All-natural' cleaning products containing arsenic (arsenic IS natural, but toxic)",
        "student_analogy": "Saying 'I'm a good person' — that means nothing without specifics. Good at what? Compared to what?",
    },
    {
        "sin": "Irrelevance",
        "description": "Claims that are technically true but meaningless because they apply to all products in the category",
        "example": "'CFC-free' — CFCs have been banned worldwide since 1987. EVERYTHING is CFC-free. It's not a choice, it's the law.",
        "student_analogy": "Like a restaurant bragging 'We don't serve poison!' — that's not a feature, it's literally the minimum legal requirement",
    },
    {
        "sin": "Lesser of Two Evils",
        "description": "Claims that may be true within the product category but distract from the impact of the category itself",
        "example": "'Organic cigarettes' or 'fuel-efficient SUV' — the product category itself is harmful regardless of the 'green' variant",
        "student_analogy": "Like saying 'I only skipped class TWICE this week' — still not a flex",
    },
    {
        "sin": "Fibbing",
        "description": "Outright false claims — using fake certifications, inventing stats, or claiming certifications that don't exist",
        "example": "Products displaying fake 'certified organic' logos that don't correspond to any real certification body",
        "student_analogy": "Like photoshopping a trophy into your photo — completely made up",
    },
    {
        "sin": "Worshipping False Labels",
        "description": "Creating fake third-party endorsement through self-created 'eco labels' or misleading certification imagery",
        "example": "A company creating its own 'Green Approved' seal that looks official but is just their internal marketing team's invention",
        "student_analogy": "Like creating your own awards show and giving yourself 'Best Student' — you can't certify yourself",
    },
]

# ─── INDUSTRY-SPECIFIC GREENWASHING PATTERNS ─────────────────────────────────

INDUSTRY_PATTERNS = {
    "fashion": {
        "common_tactics": [
            "Vague 'conscious' or 'sustainable' collection names without defined criteria",
            "'Made with recycled materials' when only 5-20% of fabric is actually recycled",
            "Highlighting one 'green' product line while 95%+ of production is conventional",
            "Carbon offset claims for fast fashion (offsetting doesn't address overproduction)",
            "'Take-back' programs that end up in landfill/incineration (less than 1% actually recycled into new clothing)",
        ],
        "key_companies_flagged": ["Shein (€40M fine)", "H&M ('Conscious' lawsuit)", "Zara/Inditex", "Boohoo", "Primark"],
        "what_real_sustainability_looks_like": "Third-party certified (GOTS, OEKO-TEX, Fair Trade), transparent supply chain, published living wage data, circular design principles, <10% growth rate",
    },
    "energy": {
        "common_tactics": [
            "'Net zero by 2050' pledges with no interim targets or funded roadmap",
            "'Clean energy' branding while 80%+ revenue comes from fossil fuels",
            "Carbon neutral claims using questionable offsets (non-additional, non-permanent)",
            "'Renewable energy certificates' (RECs) marketed as 'powered by renewables' when actual energy comes from the grid",
            "Scope manipulation — claiming 'carbon neutral' on Scope 1 only (ignoring 85%+ of actual emissions in Scope 2+3)",
        ],
        "key_companies_flagged": ["TotalEnergies (court ruling)", "Shell (Netherlands ruling)", "Santos (Australia)", "BP ('Beyond Petroleum')", "Chevron"],
        "what_real_sustainability_looks_like": "SBTi-validated targets covering ALL scopes, year-over-year absolute emission reductions (not intensity), transparent offset quality standards (Gold Standard/Verra), actual capex allocation to renewables >50%",
    },
    "food_beverage": {
        "common_tactics": [
            "'100% recycled bottle' claims that exclude cap and label (55%+ of packaging)",
            "'Carbon neutral' products achieved entirely through offsets, not emission reduction",
            "'Natural' or 'clean label' claims on ultra-processed foods",
            "Highlighting one sustainable ingredient while using palm oil from deforested land",
            "'Responsibly sourced' without third-party certification (Rainforest Alliance, MSC, etc.)",
        ],
        "key_companies_flagged": ["Coca-Cola (EU forced label change)", "Nestlé (plastic claims)", "Danone", "Nespresso"],
        "what_real_sustainability_looks_like": "Full lifecycle assessment published, third-party certified supply chains, absolute plastic reduction targets (not just recycled content), Scope 3 emissions reported and reducing",
    },
    "tech": {
        "common_tactics": [
            "'Carbon neutral' for a single product line while overall company emissions grow",
            "'Powered by renewable energy' using RECs rather than direct renewable supply",
            "'Recycled materials' claims for a tiny component (e.g., one screw) in a non-repairable device",
            "Planned obsolescence marketed as 'innovation' while claiming sustainability",
            "'E-waste programs' with very low actual collection rates (<5% of devices sold)",
        ],
        "key_companies_flagged": ["Apple (Watch carbon neutral - retracted)", "Samsung", "Amazon (Climate Pledge)"],
        "what_real_sustainability_looks_like": "Right to repair supported, 10+ year software support, published product lifecycle assessments, actual circular design (modular, repairable), e-waste collection rate >20%",
    },
}

# ─── REGULATORY FRAMEWORK REFERENCE ──────────────────────────────────────────

REGULATORY_FRAMEWORKS = {
    "FTC_Green_Guides": {
        "jurisdiction": "United States",
        "key_rules": [
            "General environmental benefit claims (e.g., 'eco-friendly') should be avoided unless substantiated for ALL significant impacts",
            "Carbon offset claims must disclose if offsets haven't been achieved yet",
            "'Recyclable' claims must be true for the ENTIRE product unless clearly qualified",
            "'Made with recycled content' must specify exact percentage",
            "Comparative claims ('50% more recycled') must specify baseline clearly",
        ],
        "penalty": "Per-violation fines; FTC can seek court injunctions and consumer redress",
    },
    "EU_Green_Claims_Directive": {
        "jurisdiction": "European Union (27 countries)",
        "key_rules": [
            "ALL environmental claims must be substantiated by scientific evidence BEFORE being made",
            "Generic claims ('eco-friendly', 'green', 'climate-friendly') are banned unless proven for the product's full lifecycle",
            "Carbon neutral/offset claims face strict scrutiny — must disclose what's measured, method, and verification",
            "Companies must use recognized methodologies (PEF, ISO 14040) for any quantified claims",
            "Sustainability labels must be based on third-party certification schemes",
        ],
        "penalty": "Up to 4% of annual global turnover; product withdrawal; banned from public procurement",
    },
    "ACCC_Australia": {
        "jurisdiction": "Australia",
        "key_rules": [
            "Environmental claims must not be misleading or deceptive under the Australian Consumer Law",
            "Businesses must have 'reasonable grounds' for making sustainability claims at the time they are made",
            "ACCC has identified 8 key principles for trustworthy environmental claims",
            "Specific focus on carbon neutral claims, renewable energy claims, and recyclability",
        ],
        "penalty": "Up to AUD$50 million for corporations; ASIC enforcement for financial greenwashing",
    },
    "UK_CMA_Green_Claims_Code": {
        "jurisdiction": "United Kingdom",
        "key_rules": [
            "Claims must be truthful and accurate",
            "Claims must be clear and unambiguous",
            "Claims must not omit or hide important relevant information",
            "Comparisons must be fair and meaningful",
            "Claims must consider the full lifecycle of the product",
            "Claims must be substantiated with robust, credible evidence",
        ],
        "penalty": "Up to 10% of global annual turnover (from April 2025 under new Digital Markets Act powers)",
    },
}

# ─── HELPER FUNCTION ─────────────────────────────────────────────────────────


def get_knowledge_context(industry_hint: str = "", max_chars: int = 3000) -> str:
    """
    Build a compact knowledge context string to inject into LLM prompts.
    Provides real-world greenwashing cases and regulatory context.
    
    Args:
        industry_hint: Optional industry keyword (fashion, energy, food, tech)
                      to prioritize relevant cases
        max_chars: Maximum characters for the context block
    """
    sections = []
    
    # Always include top enforcement cases (most impactful for analysis)
    sections.append("KNOWN GREENWASHING PRECEDENTS (real cases you can reference):")
    top_cases = ENFORCEMENT_CASES[:6]  # Top 6 most relevant
    for case in top_cases:
        sections.append(
            f"• {case['company']} ({case['year']}, {case['jurisdiction']}): "
            f"{case['violation']} — Fine: {case['fine']}. "
            f"Lesson: {case['lesson']}"
        )
    
    # Include industry-specific patterns if a hint is provided
    industry_key = ""
    if industry_hint:
        hint_lower = industry_hint.lower()
        if any(w in hint_lower for w in ["fashion", "clothing", "apparel", "shein", "h&m", "zara"]):
            industry_key = "fashion"
        elif any(w in hint_lower for w in ["energy", "oil", "gas", "fossil", "shell", "bp"]):
            industry_key = "energy"
        elif any(w in hint_lower for w in ["food", "beverage", "drink", "coca", "nestle", "bottle"]):
            industry_key = "food_beverage"
        elif any(w in hint_lower for w in ["tech", "apple", "samsung", "electronics", "device"]):
            industry_key = "tech"
    
    if industry_key and industry_key in INDUSTRY_PATTERNS:
        pattern = INDUSTRY_PATTERNS[industry_key]
        sections.append(f"\nINDUSTRY PATTERNS ({industry_key.upper()}):")
        sections.append("Common tactics in this sector:")
        for tactic in pattern["common_tactics"][:4]:
            sections.append(f"  - {tactic}")
        sections.append(f"What REAL sustainability looks like: {pattern['what_real_sustainability_looks_like']}")
    
    # Include the Seven Sins framework (compact version)
    sections.append("\nGREENWASHING DETECTION FRAMEWORK (Seven Sins):")
    for sin in SEVEN_SINS[:5]:  # Top 5 most common
        sections.append(f"• {sin['sin']}: {sin['description']}")
    
    # Build and trim to max_chars
    result = "\n".join(sections)
    if len(result) > max_chars:
        result = result[:max_chars - 3] + "..."
    
    return result


def get_regulatory_context(jurisdiction: str = "") -> str:
    """
    Get regulatory framework information for a specific jurisdiction.
    Used when the AI needs to cite specific regulations.
    """
    if not jurisdiction:
        # Return all frameworks briefly
        lines = ["REGULATORY LANDSCAPE:"]
        for key, framework in REGULATORY_FRAMEWORKS.items():
            lines.append(
                f"• {framework['jurisdiction']}: Penalty up to {framework['penalty']}. "
                f"Key rule: {framework['key_rules'][0]}"
            )
        return "\n".join(lines)
    
    # Match specific jurisdiction
    jurisdiction_lower = jurisdiction.lower()
    for key, framework in REGULATORY_FRAMEWORKS.items():
        if any(w in jurisdiction_lower for w in framework["jurisdiction"].lower().split()):
            lines = [f"REGULATORY FRAMEWORK — {framework['jurisdiction']}:"]
            for rule in framework["key_rules"]:
                lines.append(f"  • {rule}")
            lines.append(f"  Penalty: {framework['penalty']}")
            return "\n".join(lines)
    
    return ""
