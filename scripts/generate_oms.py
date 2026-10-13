#!/usr/bin/env python3
"""Generate 3 fictional offering memorandums (OMs) as PDFs, plus ground-truth JSON.

Everything is invented: fictional properties, brokers, numbers. The generator
defines one constants dict per OM, renders it into a PDF, and dumps the SAME
constants as ground truth — so the eval can never disagree with the document.

Usage:
    python scripts/generate_oms.py
Output:
    data/oms/*.pdf              (gitignored — regenerate any time)
    data/ground_truth/*.json    (tracked — documents expected values)
"""

import json
import os

from reportlab.lib import colors
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (PageBreak, Paragraph, SimpleDocTemplate,
                                Spacer, Table, TableStyle)

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OMS_DIR = os.path.join(BASE, "data", "oms")
GT_DIR = os.path.join(BASE, "data", "ground_truth")

STYLES = getSampleStyleSheet()
TITLE = ParagraphStyle("CoverTitle", parent=STYLES["Title"], fontSize=26,
                       spaceAfter=12, textColor=colors.HexColor("#1a2b4a"))
H1 = ParagraphStyle("H1", parent=STYLES["Heading1"], fontSize=16,
                    spaceBefore=14, spaceAfter=8,
                    textColor=colors.HexColor("#1a2b4a"))
H2 = ParagraphStyle("H2", parent=STYLES["Heading2"], fontSize=12,
                    spaceBefore=10, spaceAfter=6)
BODY = ParagraphStyle("Body2", parent=STYLES["BodyText"], fontSize=10,
                      leading=14, spaceAfter=6)
SMALL = ParagraphStyle("Small", parent=STYLES["BodyText"], fontSize=8,
                       leading=11, textColor=colors.HexColor("#555555"))
BULLET = ParagraphStyle("Bullet", parent=BODY, leftIndent=18,
                        bulletIndent=8, spaceAfter=3)
BANNER = ParagraphStyle("Banner", parent=STYLES["BodyText"], fontSize=9,
                        leading=12, textColor=colors.HexColor("#8a6d1b"),
                        alignment=1, spaceAfter=8)


def money(v):
    return f"${v:,.0f}"


def pct(v):
    return f"{v:.2f}%"


class OMBuilder:
    """Accumulates pages; records which page each ground-truth field lands on."""

    def __init__(self, om_id):
        self.om_id = om_id
        self.pages = []          # list of flowable-lists, one per page
        self._current = []
        self.gt_fields = {}      # field -> {"value":..., "page":...}

    def page(self, title=None):
        if self._current or title:
            self.pages.append(self._current)
        self._current = []
        if title:
            self._current.append(Paragraph(title, H1))

    def p(self, text, style=BODY):
        self._current.append(Paragraph(text, style))

    def add(self, *flowables):
        """Append raw flowables (tables, spacers) to the current page."""
        self._current.extend(flowables)

    def bullets(self, items):
        for it in items:
            self._current.append(Paragraph(it, BULLET, bulletText="\u2022"))

    def field(self, name, value, page=None):
        """Record a ground-truth field on the current (1-indexed) page."""
        self.gt_fields[name] = {
            "value": value,
            "page": page or (len(self.pages) + 1),
        }

    def table(self, headers, rows, widths=None):
        data = [[Paragraph(f"<b>{h}</b>", BODY) for h in headers]]
        for r in rows:
            data.append([Paragraph(str(c), BODY) for c in r])
        t = Table(data, colWidths=widths, repeatRows=1)
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a2b4a")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        self._current.append(t)
        self._current.append(Spacer(1, 8))

    def finish(self, filename):
        self.pages.append(self._current)
        path = os.path.join(OMS_DIR, filename)
        doc = SimpleDocTemplate(path, pagesize=LETTER,
                                leftMargin=0.9 * inch, rightMargin=0.9 * inch,
                                topMargin=0.8 * inch, bottomMargin=0.8 * inch,
                                title=f"Confidential Offering Memorandum - {self.om_id}")
        story = []
        for i, pg in enumerate(self.pages):
            if i:
                story.append(PageBreak())
            story.extend(pg)
        doc.build(story)
        print(f"wrote {path} ({len(self.pages)} pages)")
        return path


# --------------------------------------------------------------------------
# OM A — Maple Grove Apartments (clean digital multifamily)
# --------------------------------------------------------------------------

def build_maple_grove():
    b = OMBuilder("maple_grove")
    mix = [
        {"unit_type": "1 Bedroom", "count": 40, "avg_rent": 1050},
        {"unit_type": "2 Bedroom", "count": 60, "avg_rent": 1350},
        {"unit_type": "3 Bedroom", "count": 20, "avg_rent": 1650},
    ]
    total_units = sum(m["count"] for m in mix)
    avg_rent = round(sum(m["count"] * m["avg_rent"] for m in mix) / total_units, 2)
    gpr = 1872000
    vacancy = 112320
    other_income = 96000
    egi = gpr - vacancy + other_income
    expenses = {"Property Taxes": 210000, "Insurance": 68000,
                "Management": 92784, "Maintenance": 145000,
                "Utilities": 128000, "Payroll": 100216}
    total_exp = sum(expenses.values())
    t12_noi = egi - total_exp
    proforma_noi = 1245000
    price = 16500000
    cap = round(t12_noi / price * 100, 2)

    # p1 cover
    b.page()
    b.p("CONFIDENTIAL OFFERING MEMORANDUM", SMALL)
    b.p("Maple Grove Apartments", TITLE)
    b.p("1420 Elm Street, Dayton, OH 45402", BODY)
    b.p("120-Unit Garden-Style Multifamily Community", BODY)
    b.p("Exclusively marketed by BlueSky Realty Advisors", SMALL)
    b.p("October 2026", SMALL)

    # p2 overview / fact sheet
    b.page("Property Overview")
    b.p("Maple Grove Apartments is a 120-unit garden-style multifamily community "
        "built in 1987 and renovated in 2019. The property sits on 6.4 acres with "
        "8 two-story buildings, a leasing office, and 210 surface parking spaces.")
    b.p("PROPERTY FACT SHEET", H2)
    b.p("Property Name: Maple Grove Apartments")
    b.p("Property Address: 1420 Elm Street, Dayton, OH 45402")
    b.p(f"Total Units: {total_units}")
    b.p("Year Built / Renovated: 1987 / 2019")
    b.field("property_name", "Maple Grove Apartments")
    b.field("address", "1420 Elm Street, Dayton, OH 45402")
    b.field("total_units", total_units)

    # p3 unit mix
    b.page("Unit Mix")
    b.table(["Unit Type", "Count", "Avg. Rent / Mo"],
            [[m["unit_type"], m["count"], money(m["avg_rent"])] for m in mix],
            widths=[2.2 * inch, 1.2 * inch, 1.8 * inch])
    for m in mix:
        b.p(f"{m['unit_type']} \u2014 {m['count']} units \u2014 "
            f"{money(m['avg_rent'])}/mo avg rent")
    b.p(f"Average Rent: {money(avg_rent)} per month "
        f"(weighted average across unit mix)")
    b.field("unit_mix", mix)
    b.field("avg_rent", avg_rent)

    # p4 rent roll summary
    b.page("Rent Roll Summary")
    b.p("Occupancy: 94.0% (113 of 120 units leased)")
    b.p("In-place rents average 3% below the submarket for comparable "
        "1980s-vintage product, indicating organic upside on turnover.")
    b.field("occupancy_pct", 94.0)

    # p5 T-12
    b.page("Trailing Twelve Month Operating Statement")
    b.p(f"Gross Potential Rent: {money(gpr)}")
    b.p(f"Less: Vacancy &amp; Collection Loss: {money(vacancy)}")
    b.p(f"Other Income: {money(other_income)}")
    b.p(f"<b>Effective Gross Income: {money(egi)}</b>")
    b.p("OPERATING EXPENSES", H2)
    for k, v in expenses.items():
        b.p(f"{k}: {money(v)}")
    b.p(f"<b>Total Operating Expenses: {money(total_exp)}</b>")
    b.p(f"<b>T-12 Net Operating Income (NOI): {money(t12_noi)}</b>")
    b.field("expenses_breakdown", expenses)
    b.field("total_expenses", total_exp)
    b.field("t12_noi", t12_noi)

    # p6 pro forma
    b.page("Pro Forma (Year 1)")
    b.bullets([
        "4% rent growth on turnover units; 2% on renewals",
        "Expense growth of 2.5% across controllable line items",
        "Stabilized occupancy of 95%",
    ])
    b.p(f"<b>Pro Forma Net Operating Income (Year 1): {money(proforma_noi)}</b>")
    b.field("proforma_noi", proforma_noi)

    # p7 pricing & terms
    b.page("Pricing &amp; Sale Terms")
    b.p(f"<b>Asking Price: {money(price)}</b>")
    b.p(f"<b>Capitalization Rate: {pct(cap)} (based on T-12 NOI)</b>")
    b.p("SALE TERMS", H2)
    b.bullets([
        "All-cash offers preferred; seller will cooperate with 1031 exchange at no cost to seller.",
        "$500,000 earnest money deposit, hard after due diligence.",
        "60-day due diligence period; closing 30 days thereafter.",
    ])
    b.field("asking_price", price)
    b.field("cap_rate_pct", cap)
    b.field("sale_terms", "All-cash offers preferred. $500,000 earnest money deposit, hard after due diligence. 60-day due diligence period; closing 30 days thereafter. Seller will cooperate with 1031 exchange at no cost to seller.")

    # p8 disclaimer
    b.page("Disclaimer")
    b.p("This Offering Memorandum is confidential and furnished solely for the "
        "purpose of considering the acquisition of the property. All financial "
        "figures are unaudited. Prospective purchasers should conduct their own "
        "due diligence.", SMALL)
    b.p("Contact: Dana Whitfield, BlueSky Realty Advisors, "
        "(937) 555-0142", SMALL)

    b.finish("maple_grove_apartments.pdf")
    return b


# --------------------------------------------------------------------------
# OM B — Harbor Point (messy mixed-use, nested expenses, scanned page)
# --------------------------------------------------------------------------

def build_harbor_point():
    b = OMBuilder("harbor_point")
    mix = [
        {"unit_type": "Studio", "count": 12, "avg_rent": 1150},
        {"unit_type": "1 Bedroom", "count": 24, "avg_rent": 1450},
        {"unit_type": "2 Bedroom", "count": 12, "avg_rent": 1850},
    ]
    total_units = sum(m["count"] for m in mix)
    avg_rent = round(sum(m["count"] * m["avg_rent"] for m in mix) / total_units, 2)
    res_gpr, res_vac, other_income, retail_income = 849600, 76464, 42000, 168000
    egi = res_gpr - res_vac + other_income + retail_income
    expenses = {
        "Property Taxes": {"County": 96000, "City": 46000},
        "Insurance": {"Property & Casualty": 41000, "General Liability": 13500},
        "Management": {"Residential": 49388, "Retail": 9600},
        "Maintenance & Repairs": {"Routine": 58000, "Turnover": 38400},
        "Utilities": {"Water/Sewer": 44000, "Common Electric": 18200, "Trash": 9000},
        "Payroll": {"On-site Manager": 52000, "Maintenance Tech": 36000},
    }
    exp_totals = {k: sum(v.values()) for k, v in expenses.items()}
    total_exp = sum(exp_totals.values())
    t12_noi = egi - total_exp
    proforma_noi = 545000
    price = 8900000
    cap = round(t12_noi / price * 100, 2)

    # p1 cover
    b.page()
    b.p("CONFIDENTIAL OFFERING MEMORANDUM", SMALL)
    b.p("Harbor Point", TITLE)
    b.p("88 Harbor Drive, Tampa, FL 33602", BODY)
    b.p("48-Unit Multifamily + 6-Bay Retail \u2014 Mixed-Use", BODY)
    b.p("Exclusively marketed by GulfCoast Commercial Realty", SMALL)

    # p2 overview
    b.page("Property Overview")
    b.p("Harbor Point pairs 48 garden apartments with six ground-floor retail "
        "bays along Harbor Drive. Five of six retail bays are leased at an "
        "average of $2,800/mo NNN; one bay (1,900 SF) is vacant and marketed.")
    b.p("PROPERTY FACT SHEET", H2)
    b.p("Property Name: Harbor Point")
    b.p("Property Address: 88 Harbor Drive, Tampa, FL 33602")
    b.p(f"Total Units: {total_units} (residential)")
    b.field("property_name", "Harbor Point")
    b.field("address", "88 Harbor Drive, Tampa, FL 33602")
    b.field("total_units", total_units)

    # p3 unit mix
    b.page("Residential Unit Mix")
    b.table(["Unit Type", "Count", "Avg. Rent / Mo"],
            [[m["unit_type"], m["count"], money(m["avg_rent"])] for m in mix],
            widths=[2.2 * inch, 1.2 * inch, 1.8 * inch])
    for m in mix:
        b.p(f"{m['unit_type']} \u2014 {m['count']} units \u2014 "
            f"{money(m['avg_rent'])}/mo avg rent")
    b.p(f"Weighted average rent: {money(avg_rent)} per month")
    b.field("unit_mix", mix)
    b.field("avg_rent", avg_rent)

    # p4 rent roll — SCANNED page
    b.page("Rent Roll Detail")
    scanned = [
        Paragraph("\u2014 SCANNED COPY \u2014 ORIGINAL ON FILE WITH BROKER \u2014",
                  BANNER),
        Paragraph("Residential occupancy is 91% as of September 2026 "
                  "(44 of 48 units).", BODY),
        Paragraph("Sample rent roll lines (full schedule on file):", BODY),
        Paragraph("Unit 101 \u2014 1 Bedroom \u2014 $1,450/mo \u2014 Leased", BODY),
        Paragraph("Unit 102 \u2014 1 Bedroom \u2014 $1,450/mo \u2014 Leased", BODY),
        Paragraph("Unit 201 \u2014 2 Bedroom \u2014 $1,850/mo \u2014 Leased", BODY),
        Paragraph("Unit 305 \u2014 Studio \u2014 $1,150/mo \u2014 Vacant", BODY),
        Paragraph("Occupancy: 91.0% residential", BODY),
    ]
    wrap = Table([[scanned]], colWidths=[6.3 * inch])
    wrap.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f2f0e8")),
        ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#c9c2a8")),
        ("LEFTPADDING", (0, 0), (-1, -1), 14),
        ("RIGHTPADDING", (0, 0), (-1, -1), 14),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
    ]))
    b.add(wrap)
    b.field("occupancy_pct", 91.0)

    # p5 T-12 nested expenses
    b.page("Trailing Twelve Month Operating Statement")
    b.p(f"Residential Gross Potential Rent: {money(res_gpr)}")
    b.p(f"Less: Vacancy (9%): {money(res_vac)}")
    b.p(f"Other Income: {money(other_income)}")
    b.p(f"Retail Income (5 bays NNN): {money(retail_income)}")
    b.p(f"<b>Effective Gross Income: {money(egi)}</b>")
    b.p("OPERATING EXPENSES (detailed)", H2)
    for cat, subs in expenses.items():
        b.p(f"{cat}: {money(exp_totals[cat])}")
        for sk, sv in subs.items():
            b.p(f"\u2022 {sk}: {money(sv)}", BULLET)
    b.p(f"<b>Total Operating Expenses: {money(total_exp)}</b>")
    b.p(f"<b>T-12 Net Operating Income (NOI): {money(t12_noi)}</b>")
    b.field("expenses_breakdown", exp_totals)
    b.field("total_expenses", total_exp)
    b.field("t12_noi", t12_noi)

    # p6 pro forma
    b.page("Pro Forma (Year 1)")
    b.bullets([
        "Lease-up of vacant retail bay at $2,900/mo NNN",
        "3% residential rent growth; expenses +2%",
    ])
    b.p(f"<b>Pro Forma Net Operating Income (Year 1): {money(proforma_noi)}</b>")
    b.field("proforma_noi", proforma_noi)

    # p7 pricing
    b.page("Pricing &amp; Sale Terms")
    b.p(f"<b>Offered at {money(price)}</b>")
    b.p(f"<b>Cap Rate: {pct(cap)} on T-12 NOI</b>")
    b.p("SALE TERMS", H2)
    b.bullets([
        "Seller will consider seller financing with 40% down payment at market rates.",
        "$250,000 earnest money deposit.",
        "45-day study period; closing 21 days thereafter.",
    ])
    b.field("asking_price", price)
    b.field("cap_rate_pct", cap)
    b.field("sale_terms", "Seller will consider seller financing with 40% down payment at market rates. $250,000 earnest money deposit. 45-day study period; closing 21 days thereafter.")

    # p8 disclaimer
    b.page("Disclaimer")
    b.p("Confidential. Figures unaudited; buyer to verify independently.",
        SMALL)
    b.p("Contact: Marco Reyes, GulfCoast Commercial Realty, "
        "(813) 555-0190", SMALL)

    b.finish("harbor_point_mixed_use.pdf")
    return b


# --------------------------------------------------------------------------
# OM C — Ironworks Industrial Park (deliberate gaps)
# --------------------------------------------------------------------------

def build_ironworks():
    b = OMBuilder("ironworks")
    total_sf, leased_sf = 84000, 78500
    occupancy = round(leased_sf / total_sf * 100, 1)
    t12_noi = 402300
    total_exp = 168400
    proforma_noi = 438000
    price = 5750000

    # p1 cover
    b.page()
    b.p("CONFIDENTIAL OFFERING MEMORANDUM", SMALL)
    b.p("Ironworks Industrial Park", TITLE)
    b.p("2500 Foundry Avenue, Gary, IN 46406", BODY)
    b.p("6-Building Light Industrial Park \u2014 84,000 SF", BODY)
    b.p("Exclusively marketed by Calumet Industrial Partners", SMALL)

    # p2 overview
    b.page("Property Overview")
    b.p("Ironworks is a six-building light industrial park totaling 84,000 "
        "rentable square feet. Current tenancy is a mix of manufacturing and "
        "warehouse/distribution users on triple-net leases.")
    b.p("PROPERTY FACT SHEET", H2)
    b.p("Property Name: Ironworks Industrial Park")
    b.p("Property Address: 2500 Foundry Avenue, Gary, IN 46406")
    b.p("Buildings: 6 \u2014 Total Rentable SF: 84,000")
    b.field("property_name", "Ironworks Industrial Park")
    b.field("address", "2500 Foundry Avenue, Gary, IN 46406")
    b.field("total_units", None)   # not applicable: industrial
    b.field("unit_mix", None)      # not applicable: industrial

    # p3 tenancy
    b.page("Tenancy &amp; Occupancy")
    b.p(f"Leased: {leased_sf:,} SF of {total_sf:,} SF "
        f"({occupancy}% leased)")
    b.p("Average rent: $6.75 per square foot per year (NNN)")
    b.p("Weighted average remaining lease term: 3.2 years")
    b.field("occupancy_pct", occupancy)
    b.field("avg_rent", 6.75)

    # p4 T-12 (sparse)
    b.page("Trailing Twelve Month Summary")
    b.p(f"T-12 Net Operating Income: {money(t12_noi)}")
    b.p(f"Total operating expenses: {money(total_exp)}. "
        f"Detailed expense breakdown available upon request.")
    b.p("Rent roll and estoppels available in the data room upon executed CA.")
    b.field("t12_noi", t12_noi)
    b.field("total_expenses", total_exp)
    b.field("expenses_breakdown", None)   # deliberately missing

    # p5 pricing & terms
    b.page("Pricing &amp; Sale Terms")
    b.p(f"<b>Priced at {money(price)}</b>")
    b.p("Capitalization rate to be determined by the market. "
        "Broker encourages buyers to underwrite to their own return targets.")
    b.p("SALE TERMS", H2)
    b.bullets([
        "$200,000 earnest money deposit.",
        "30-day due diligence period.",
        "Seller to deliver estoppels within 15 days of acceptance.",
    ])
    b.field("asking_price", price)
    b.field("cap_rate_pct", None)   # deliberately not stated
    b.field("proforma_noi", proforma_noi)
    b.field("sale_terms", "$200,000 earnest money deposit. 30-day due diligence period. Seller to deliver estoppels within 15 days of acceptance.")
    b.p(f"Pro forma NOI (Year 1, broker estimate): {money(proforma_noi)}")

    # p6 disclaimer
    b.page("Disclaimer")
    b.p("Confidential. All figures unaudited.", SMALL)
    b.p("Contact: Priya Natarajan, Calumet Industrial Partners, "
        "(219) 555-0117", SMALL)

    b.finish("ironworks_industrial.pdf")
    return b


def main():
    os.makedirs(OMS_DIR, exist_ok=True)
    os.makedirs(GT_DIR, exist_ok=True)
    builders = [build_maple_grove(), build_harbor_point(), build_ironworks()]
    for b in builders:
        gt = {"om_id": b.om_id, "fields": b.gt_fields}
        path = os.path.join(GT_DIR, f"{b.om_id}.json")
        with open(path, "w") as f:
            json.dump(gt, f, indent=2)
        print(f"wrote {path}")


if __name__ == "__main__":
    main()
