"""
GreenLens Knowledge Base — Greenwashing Intelligence

This module provides curated domain knowledge about greenwashing:
- Real enforcement cases with fines (for credible comparisons)
- The 7 Sins of Greenwashing framework
- Key regulations and what they require
- Common industry-specific greenwashing patterns
- Certification verification guidance

This context is injected into the system prompt to give the AI
deep, specific domain expertise beyond what the LLM's training data provides.
"""

GREENWASH_KNOWLEDGE = """
=== GREENWASHING INTELLIGENCE DATABASE ===
(Use this knowledge to enrich your analysis with real-world comparisons and regulatory context)

## MAJOR ENFORCEMENT CASES (cite these when relevant comparisons exist)

1. VOLKSWAGEN (2015-ongoing): $34.69B total penalties across multiple countries. Used "defeat device" software to fake emissions test results. Lesson: if a company's environmental data comes ONLY from internal systems without third-party verification, that's a red flag.

2. EU CAR MAKERS CARTEL (2025): €600M fine. 15 car makers made false claims about recycled vehicle content. Lesson: industry-wide claims without independent verification often indicate coordinated greenwashing.

3. DWS/Deutsche Bank Asset Management (2025): €25M fine. Made misleading statements about ESG integration in investment decisions. Lesson: claiming ESG integration without documented decision-making processes is greenwashing.

4. SHEIN (2024): €1M fine from Italian AGCM. "evoluSHEIN by Design" collection used vague, generic, and misleading environmental claims. Lesson: "sustainable collections" that represent <1% of production while the core business is fast fashion = textbook hidden trade-off.

5. VANGUARD/Active Super/Mercer (2023-2024): ASIC (Australia) enforcement. Financial products labeled "sustainable" or "green" without matching investment criteria. Lesson: labels without substance.

6. SANTOS (2024): Australian Federal Court found Santos's claim of "clean energy" was misleading because natural gas extraction produces significant emissions. Lesson: relative improvements ≠ absolute claims.

7. KEURIG (2022): $3M penalty (US). "Recyclable" K-Cup pods were not actually recyclable in most municipal programs. Lesson: theoretical recyclability ≠ practical recyclability.

8. H&M Conscious Collection (2022): Netherlands ASA ruling. "Conscious Choice" labels on fast fashion items with minimal actual sustainability improvements. Lesson: sustainability sub-brands within inherently unsustainable business models.

9. NESTLÉ WATERS (2021): $570K settlement (US). "100% recycled" claims on water bottles when actual recycled content was only 5-25%. Lesson: "100%" is an absolute claim that requires absolute proof.

10. BP (2019-ongoing): UK Advertising Standards Authority banned BP ads for misrepresenting climate action. Company spent more on green advertising than actual renewable investment. Lesson: ad spend vs. investment ratio is a key credibility indicator.

PENALTY SCALE (for context — what's at stake):
- EU: Up to 4% of annual global turnover per violation
- UK: Up to 10% of global annual turnover (from April 2025, CMA direct enforcement)
- US (FTC): Per-violation fines + corrective advertising orders
- Australia: Up to AUD$50M per contravention for corporations

## THE 7 SINS OF GREENWASHING (TerraChoice Framework)
When analyzing claims, check for these patterns:

1. SIN OF THE HIDDEN TRADE-OFF: Claiming greenness based on one attribute while ignoring greater environmental harm elsewhere (e.g., "recycled paper" from clear-cut forests)

2. SIN OF NO PROOF: Environmental claims without accessible supporting evidence or third-party certification (e.g., "50% more recycled content" with no verification)

3. SIN OF VAGUENESS: Broad, undefined claims that consumers can't verify (e.g., "all-natural," "eco-friendly," "green," "sustainable" without specifics)

4. SIN OF IRRELEVANCE: Technically true but unhelpful claims (e.g., "CFC-free" when CFCs are banned by law anyway)

5. SIN OF LESSER OF TWO EVILS: Claims that are true within the product category but distract from the category's overall impact (e.g., "organic" cigarettes, "fuel-efficient" SUVs)

6. SIN OF FIBBING: Outright false environmental claims or fake certifications

7. SIN OF WORSHIPING FALSE LABELS: Using fake certification logos or implying third-party endorsement that doesn't exist

## KEY REGULATIONS (cite specific requirements when relevant)

### FTC GREEN GUIDES (USA)
- Unqualified "recyclable" claims must apply to the ENTIRE product, not just packaging
- "Carbon neutral" claims must clearly disclose what's included/excluded
- "Biodegradable" claims require evidence of decomposition within 1 year
- General environmental benefit claims ("eco-friendly") are inherently deceptive without qualification
- Comparative claims must clearly state the basis for comparison

### EU GREEN CLAIMS DIRECTIVE (2024-2026)
- ALL environmental claims must be substantiated by recognized scientific evidence
- Claims must take a LIFE-CYCLE perspective (not just one stage)
- Carbon offsetting alone cannot justify "carbon neutral" or "climate neutral" claims
- Environmental labels must be based on third-party certification schemes
- Penalties: up to 4% of annual global turnover
- Generic claims ("green," "eco," "sustainable") will be BANNED without proof

### UK CMA GREEN CLAIMS CODE (2025)
- Claims must be truthful and accurate
- Claims must be clear and unambiguous
- Claims must not omit or hide important relevant information
- Comparisons must be fair and meaningful
- Claims must consider the full life cycle
- Claims must be substantiated
- Penalties: up to 10% of global annual turnover (from April 2025)

### ACCC (AUSTRALIA)
- Has made greenwashing a top enforcement priority since 2022
- Eight categories of concern: net-zero claims, use of terms like "green/clean/sustainable," recycling claims, carbon neutral claims, sustainability certifications, use of trust marks, supply chain claims, product-specific environmental claims
- Active intervention: 35+ greenwashing investigations in 2023-2024

## INDUSTRY-SPECIFIC GREENWASHING PATTERNS

### FASHION / TEXTILES
- "Sustainable collection" = usually <5% of total production
- "Organic cotton" in blended fabrics = the non-organic 60% is still conventional
- "Recycled polyester" still sheds microplastics
- "Carbon neutral delivery" = offset-based, not emission-eliminated
- Shein produces 900x more products than a traditional store (Greenpeace 2025) — claiming sustainability while operating at this scale is inherently contradictory
- H&M "Conscious Collection" — investigated by Netherlands ASA, found to overstate sustainability on scorecards
- Fast fashion "take-back" schemes: Greenpeace investigation found most clothes collected are downcycled, burned, or shipped to landfills in Ghana/Chile/Kenya
- Gen Z is the primary target of fast fashion greenwashing (TikTok/Instagram marketing with green messaging)
- Greenpeace: fast fashion business model (100+ new styles/week) is "fundamentally incompatible with true sustainability" regardless of material choices
- Red flag: any fast-fashion brand claiming to be "sustainable" while producing millions of garments
- Red flag: "take-back" or "recycling" programs without transparency on what actually happens to returned clothes

### ENERGY / OIL & GAS
- "Transitioning to renewables" while 90%+ revenue from fossil fuels
- "Net zero by 2050" with no interim targets or capital allocation
- "Clean energy" for natural gas (still emits CO2)
- "Carbon capture" projects at tiny scale vs. actual emissions
- Big Oil spends ~$750M/year collectively on green PR campaigns (InfluenceMap research)
- Shell: 70% of communications about green energy, but only 10% of capital expenditure on low-carbon (highest discourse-action gap)
- BP doubled its green-image Facebook/Instagram ad spend after UK government warned about misleading claims (Global Witness 2023)
- Study (Li et al. 2022, PLOS ONE): BP, Chevron, ExxonMobil, Shell ALL show "mismatch between discourse, actions and investments" — green transition "is not occurring"
- Climate Integrity Center (2025): Big Oil has pushed deceptive climate ads for 25+ years
- Red flag: renewable energy investment highlighted but fossil expansion hidden
- Red flag: "Net zero" targets that rely entirely on unproven carbon removal technology rather than actual emission cuts

### FOOD & BEVERAGE
- "Natural" has no legal definition in most jurisdictions
- "Farm fresh" / "free range" with minimal actual difference in conditions
- "Recyclable packaging" when local infrastructure doesn't support recycling
- "Sustainably sourced" without certifications (Rainforest Alliance, MSC, etc.)
- Red flag: green packaging imagery without corresponding product changes

### TECH / ELECTRONICS
- "Carbon neutral operations" covering only offices, not manufacturing/supply chain
- "Made from recycled materials" when it's only the box
- "E-waste program" that actually ships waste to developing countries
- "Energy efficient" comparisons against own previous products only
- Red flag: Scope 1-only carbon claims when Scope 3 is 90%+ of footprint

### FINANCE / BANKING
- "Green bonds" funding projects with minimal environmental benefit
- "ESG integrated" without documented decision-making criteria
- "Sustainable fund" holding fossil fuel companies
- "Climate-aligned portfolio" without Paris Agreement temperature pathway
- Red flag: ESG label without exclusion criteria or engagement policies

## CERTIFICATION CREDIBILITY GUIDE
When a document cites certifications, verify:

CREDIBLE (third-party, rigorous):
- B Corp (B Lab certified, holistic company assessment)
- Cradle to Cradle (material health + circularity)
- FSC (Forest Stewardship Council — forestry)
- Fair Trade (labor + environmental standards)
- Science Based Targets initiative (SBTi — climate commitments)
- ISO 14001 (environmental management system — NOTE: covers processes, not outcomes)
- Gold Standard (carbon credits with co-benefits)
- GOTS (Global Organic Textile Standard)
- EU Ecolabel (life-cycle based)
- Energy Star (energy efficiency — government-backed)

LESS CREDIBLE (self-declared or minimal standards):
- "Carbon Neutral" certifications from small offset providers without additionality proof
- Industry self-certification schemes (e.g., RSPO roundtable — has improvement plans but allows palm oil with caveats)
- Single-attribute labels that ignore broader impacts
- Company's own "green" certification or internal scoring

RED FLAGS (likely meaningless):
- Certifications with no publicly searchable database
- Logos that look official but link to the company's own website
- "Certified by [company name]" (self-certification)
- Expired certifications still displayed
- Certifications covering only one product line but implied for the whole brand

## HOW STUDENTS CAN USE THIS INFORMATION

For school projects:
- Reference specific cases (with dates and fine amounts) for credibility
- Use the 7 Sins framework to categorize claims you find
- Compare company claims against regulatory requirements (FTC/EU/ACCC)
- Check if cited certifications are in the "credible" category above

For activism:
- File complaints with relevant authorities (FTC in US, ACCC in Australia, national consumer agencies in EU)
- Document specific claims with dates, screenshots, and the regulation they potentially violate
- Use social media to create awareness — tag the regulators

For consumer choices:
- Look for SPECIFIC numbers, not vague claims
- Check if claims are third-party verified
- Be skeptical of claims that sound too good ("100% sustainable," "zero impact")
- A good claim: "27% recycled PET in our bottles, verified by [certifier], target 50% by 2027"
- A bad claim: "We care about the planet" (means nothing, proves nothing)
"""


def get_greenwash_knowledge() -> str:
    """Return the full greenwashing knowledge base for injection into system prompts."""
    return GREENWASH_KNOWLEDGE
