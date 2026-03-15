import json
import os
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# ============================================================
# קונפיגורציה כללית
# ============================================================
DB_FILE = "saved_israeli_bonds_db.json"

RATING_OPTIONS = [
    "AAA", "AA+", "AA", "AA-", "A+", "A", "A-",
    "BBB+", "BBB", "BBB-", "BB+", "BB", "BB-",
    "B+", "B", "B-", "CCC", "CC", "C", "NR"
]

SECTOR_OPTIONS = [
    "נדל\"ן מניב",
    "יזום נדל\"ן",
    "חברת החזקות",
    "תעשייה/שירותים",
    "אנרגיה/תשתיות",
    "פיננסים חוץ בנקאיים",
    "כללי"
]

OUTLOOK_OPTIONS = ["חיובי", "יציב", "שלילי", "בבחינה"]
LINKAGE_OPTIONS = ["שקלי", "צמוד מדד", "משתנה", "אחר"]
COLLATERAL_OPTIONS = [
    "ללא בטוחה",
    "שעבוד צף",
    "ערבות חברת אם",
    "שעבוד מניות",
    "שעבוד ספציפי על נכס",
    "שעבוד חזק עם יחס כיסוי גבוה"
]
SENIORITY_OPTIONS = ["רגילה", "בכירה", "נחותה"]
COVENANT_OPTIONS = ["חלש", "בינוני", "חזק"]
MARKET_LIQUIDITY_OPTIONS = ["נמוכה", "בינונית", "גבוהה"]

SECTOR_FIELD_CONFIG = {
    "נדל\"ן מניב": {
        "show_ffo": True,
        "show_ebitda": True,
        "show_operating_profit": True,
        "show_interest_expense": True,
        "show_ltv": True,
        "show_debt_to_nav": False,
        "show_equity_ratio": False,
        "show_equity_to_assets": False,
        "show_unused_credit_lines": True,
        "show_capex": True,
        "show_dividends": True,
        "label_cashflow": "FFO חזוי ל-12 חודשים",
        "sector_metric_label": "LTV (%)",
    },
    "יזום נדל\"ן": {
        "show_ffo": True,
        "show_ebitda": True,
        "show_operating_profit": True,
        "show_interest_expense": True,
        "show_ltv": False,
        "show_debt_to_nav": False,
        "show_equity_ratio": True,
        "show_equity_to_assets": False,
        "show_unused_credit_lines": True,
        "show_capex": True,
        "show_dividends": True,
        "label_cashflow": "תזרים חזוי / FFO ל-12 חודשים",
        "sector_metric_label": "שיעור הון עצמי (%)",
    },
    "חברת החזקות": {
        "show_ffo": False,
        "show_ebitda": True,
        "show_operating_profit": True,
        "show_interest_expense": True,
        "show_ltv": False,
        "show_debt_to_nav": True,
        "show_equity_ratio": False,
        "show_equity_to_assets": False,
        "show_unused_credit_lines": True,
        "show_capex": False,
        "show_dividends": True,
        "label_cashflow": "דיבידנדים / מקורות חזויים ל-12 חודשים",
        "sector_metric_label": "חוב ל-NAV (%)",
    },
    "תעשייה/שירותים": {
        "show_ffo": False,
        "show_ebitda": True,
        "show_operating_profit": True,
        "show_interest_expense": True,
        "show_ltv": False,
        "show_debt_to_nav": False,
        "show_equity_ratio": False,
        "show_equity_to_assets": False,
        "show_unused_credit_lines": True,
        "show_capex": True,
        "show_dividends": True,
        "label_cashflow": "תזרים תפעולי / חזוי ל-12 חודשים",
        "sector_metric_label": "",
    },
    "אנרגיה/תשתיות": {
        "show_ffo": False,
        "show_ebitda": True,
        "show_operating_profit": True,
        "show_interest_expense": True,
        "show_ltv": False,
        "show_debt_to_nav": False,
        "show_equity_ratio": False,
        "show_equity_to_assets": False,
        "show_unused_credit_lines": True,
        "show_capex": True,
        "show_dividends": True,
        "label_cashflow": "תזרים חזוי ל-12 חודשים",
        "sector_metric_label": "",
    },
    "פיננסים חוץ בנקאיים": {
        "show_ffo": False,
        "show_ebitda": False,
        "show_operating_profit": True,
        "show_interest_expense": True,
        "show_ltv": False,
        "show_debt_to_nav": False,
        "show_equity_ratio": False,
        "show_equity_to_assets": True,
        "show_unused_credit_lines": True,
        "show_capex": False,
        "show_dividends": True,
        "label_cashflow": "מקורות חזויים ל-12 חודשים",
        "sector_metric_label": "הון למאזן (%)",
    },
    "כללי": {
        "show_ffo": False,
        "show_ebitda": True,
        "show_operating_profit": True,
        "show_interest_expense": True,
        "show_ltv": False,
        "show_debt_to_nav": False,
        "show_equity_ratio": False,
        "show_equity_to_assets": False,
        "show_unused_credit_lines": True,
        "show_capex": True,
        "show_dividends": True,
        "label_cashflow": "תזרים חזוי ל-12 חודשים",
        "sector_metric_label": "",
    },
}

# ============================================================
# שכבת נתונים
# ============================================================
@dataclass
class BondInputs:
    name: str
    sector: str
    rating: str
    rating_outlook: str
    linkage_type: str
    expected_inflation: float 
    collateral_type: str
    seniority: str
    covenant_strength: str
    market_liquidity: str

    ytm: float
    spread: float
    duration: float

    total_debt: float
    cash: float
    ebitda: Optional[float]
    operating_profit: Optional[float]
    interest_expense: Optional[float]

    debt_due_12m: float
    expected_cashflow_12m: float
    unused_credit_lines: float
    capex_12m: float
    dividends_12m: float

    ltv: Optional[float] = None
    debt_to_nav: Optional[float] = None
    equity_ratio: Optional[float] = None
    equity_to_assets: Optional[float] = None
    qualitative_risk: float = 3.0

@dataclass
class BondRecord:
    name: str
    created_at: str
    inputs: Dict[str, Any]
    derived: Dict[str, Any]
    scores: Dict[str, Any]

def safe_float(value: Any) -> Optional[float]:
    try:
        if value in ("", None):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None

def load_saved_bonds() -> List[Dict[str, Any]]:
    if not os.path.exists(DB_FILE):
        return []
    try:
        with open(DB_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError):
        return []

def save_bonds_to_db(bonds_list: List[Dict[str, Any]]) -> None:
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(bonds_list, f, ensure_ascii=False, indent=2)

def upsert_bond_record(record: Dict[str, Any], saved_bonds: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    cleaned = [b for b in saved_bonds if b.get("name") != record.get("name")]
    cleaned.append(record)
    return cleaned

def delete_bonds_by_name(saved_bonds: List[Dict[str, Any]], names_to_delete: List[str]) -> List[Dict[str, Any]]:
    return [b for b in saved_bonds if b.get("name") not in set(names_to_delete)]

# ============================================================
# מנוע אנליזה
# ============================================================
class IsraeliBondAnalyzer:
    RATING_MAP = {
        "AAA": 1.0, "AA+": 1.2, "AA": 1.4, "AA-": 1.6,
        "A+": 1.9, "A": 2.1, "A-": 2.4,
        "BBB+": 2.8, "BBB": 3.1, "BBB-": 3.4,
        "BB+": 3.8, "BB": 4.1, "BB-": 4.3,
        "B+": 4.5, "B": 4.7, "B-": 4.8,
        "CCC": 5.0, "CC": 5.0, "C": 5.0, "NR": 4.6
    }

    OUTLOOK_ADJUSTMENT = {
        "חיובי": -0.15, "יציב": 0.0, "שלילי": 0.20, "בבחינה": 0.30
    }

    COLLATERAL_SCORE = {
        "ללא בטוחה": 5.0, "שעבוד צף": 4.2, "ערבות חברת אם": 3.4,
        "שעבוד מניות": 3.0, "שעבוד ספציפי על נכס": 2.2, "שעבוד חזק עם יחס כיסוי גבוה": 1.5
    }

    SENIORITY_SCORE = {
        "בכירה": 1.5, "רגילה": 2.8, "נחותה": 4.5
    }

    COVENANT_SCORE = {
        "חזק": 1.8, "בינוני": 3.0, "חלש": 4.4
    }

    MARKET_LIQUIDITY_SCORE = {
        "גבוהה": 1.8, "בינונית": 3.0, "נמוכה": 4.4
    }

    LEVERAGE_THRESHOLDS_BY_SECTOR = {
        "נדל\"ן מניב": [7.0, 9.0, 11.0, 13.0],
        "יזום נדל\"ן": [3.0, 5.0, 7.0, 9.0],
        "חברת החזקות": [2.0, 3.5, 5.0, 7.0],
        "תעשייה/שירותים": [2.0, 3.5, 5.0, 7.0],
        "אנרגיה/תשתיות": [3.5, 5.0, 6.5, 8.0],
        "פיננסים חוץ בנקאיים": [2.0, 3.0, 4.0, 5.0],
        "כללי": [2.5, 4.0, 5.5, 7.0],
    }

    COVERAGE_THRESHOLDS_BY_SECTOR = {
        "נדל\"ן מניב": [4.0, 3.0, 2.0, 1.2],
        "יזום נדל\"ן": [5.0, 3.0, 1.8, 1.0],
        "חברת החזקות": [3.0, 2.0, 1.5, 1.0],
        "תעשייה/שירותים": [6.0, 4.0, 2.5, 1.5],
        "אנרגיה/תשתיות": [4.5, 3.2, 2.2, 1.4],
        "פיננסים חוץ בנקאיים": [3.5, 2.5, 1.8, 1.1],
        "כללי": [5.0, 3.0, 1.8, 1.0],
    }

    SPREAD_THRESHOLDS_BY_DURATION = {
        "short": [0.8, 1.8, 3.0, 4.5],
        "mid": [1.2, 2.5, 4.0, 6.0],
        "long": [1.6, 3.0, 4.8, 7.0],
    }

    def __init__(self, inputs: BondInputs):
        self.inputs = inputs
        self.derived = self.build_derived_metrics()

    @staticmethod
    def score_metric(value: Optional[float], thresholds: List[float], reverse: bool = False, missing_score: float = 5.0) -> float:
        if value is None:
            return missing_score
        for i, t in enumerate(thresholds):
            if (value <= t and not reverse) or (value >= t and reverse):
                return float(i + 1)
        return 5.0

    def build_derived_metrics(self) -> Dict[str, Optional[float]]:
        net_debt = self.inputs.total_debt - self.inputs.cash

        nd_ebitda = None
        if self.inputs.ebitda is not None and self.inputs.ebitda > 0:
            nd_ebitda = net_debt / self.inputs.ebitda

        coverage = None
        if self.inputs.interest_expense is not None and self.inputs.interest_expense > 0 and self.inputs.operating_profit is not None:
            coverage = self.inputs.operating_profit / self.inputs.interest_expense

        cash_to_st_debt = None
        if self.inputs.debt_due_12m > 0:
            cash_to_st_debt = self.inputs.cash / self.inputs.debt_due_12m

        uses_12m = self.inputs.debt_due_12m + self.inputs.capex_12m + self.inputs.dividends_12m
        liquidity_sources = self.inputs.cash + self.inputs.expected_cashflow_12m + self.inputs.unused_credit_lines
        sources_to_uses_12m = None if uses_12m <= 0 else liquidity_sources / uses_12m

        if self.inputs.linkage_type == "צמוד מדד":
            real_rate = self.inputs.ytm / 100.0
            inflation = self.inputs.expected_inflation / 100.0
            nominal_ytm = ((1 + real_rate) * (1 + inflation) - 1) * 100.0
        else:
            nominal_ytm = self.inputs.ytm

        return {
            "net_debt": round(net_debt, 2),
            "nd_ebitda": None if nd_ebitda is None else round(nd_ebitda, 2),
            "coverage": None if coverage is None else round(coverage, 2),
            "cash_to_st_debt": None if cash_to_st_debt is None else round(cash_to_st_debt, 2),
            "sources_to_uses_12m": None if sources_to_uses_12m is None else round(sources_to_uses_12m, 2),
            "liquidity_sources_12m": round(liquidity_sources, 2),
            "uses_12m": round(uses_12m, 2),
            "nominal_ytm": round(nominal_ytm, 2), 
        }

    def spread_bucket(self) -> str:
        if self.inputs.duration <= 2: return "short"
        if self.inputs.duration <= 5: return "mid"
        return "long"

    def sector_specific_metric_score(self) -> Tuple[float, str]:
        sector = self.inputs.sector
        if sector == "נדל\"ן מניב": return self.score_metric(self.inputs.ltv, [45, 55, 65, 75], reverse=False, missing_score=4.0), "LTV"
        if sector == "חברת החזקות": return self.score_metric(self.inputs.debt_to_nav, [15, 25, 35, 50], reverse=False, missing_score=4.0), "חוב ל-NAV"
        if sector == "יזום נדל\"ן": return self.score_metric(self.inputs.equity_ratio, [40, 30, 22, 15], reverse=True, missing_score=4.0), "שיעור הון עצמי"
        if sector == "פיננסים חוץ בנקאיים": return self.score_metric(self.inputs.equity_to_assets, [28, 22, 16, 12], reverse=True, missing_score=4.0), "הון למאזן"
        return 3.0, "מדד ענפי"

    def calc_fundamental_risk(self) -> float:
        sector = self.inputs.sector
        leverage_thresholds = self.LEVERAGE_THRESHOLDS_BY_SECTOR.get(sector, self.LEVERAGE_THRESHOLDS_BY_SECTOR["כללי"])
        coverage_thresholds = self.COVERAGE_THRESHOLDS_BY_SECTOR.get(sector, self.COVERAGE_THRESHOLDS_BY_SECTOR["כללי"])

        s_leverage = self.score_metric(self.derived["nd_ebitda"], leverage_thresholds)
        s_coverage = self.score_metric(self.derived["coverage"], coverage_thresholds, reverse=True)
        s_sector_metric, _ = self.sector_specific_metric_score()

        return round(min(max((s_leverage * 0.40) + (s_coverage * 0.35) + (s_sector_metric * 0.25), 1.0), 5.0), 2)

    def calc_liquidity_refinancing_risk(self) -> float:
        s_cash_st = self.score_metric(self.derived["cash_to_st_debt"], [1.5, 1.0, 0.7, 0.4], reverse=True)
        s_sources_uses = self.score_metric(self.derived["sources_to_uses_12m"], [1.6, 1.2, 1.0, 0.8], reverse=True)
        s_market_liq = self.MARKET_LIQUIDITY_SCORE.get(self.inputs.market_liquidity, 3.0)

        return round(min(max((s_cash_st * 0.30) + (s_sources_uses * 0.50) + (s_market_liq * 0.20), 1.0), 5.0), 2)

    def calc_structural_risk(self) -> float:
        s_collateral = self.COLLATERAL_SCORE.get(self.inputs.collateral_type, 4.0)
        s_seniority = self.SENIORITY_SCORE.get(self.inputs.seniority, 2.8)
        s_covenant = self.COVENANT_SCORE.get(self.inputs.covenant_strength, 3.0)

        return round(min(max((s_collateral * 0.45) + (s_seniority * 0.20) + (s_covenant * 0.35), 1.0), 5.0), 2)

    def calc_market_pricing_risk(self) -> float:
        s_rating = self.RATING_MAP.get(self.inputs.rating, 4.6)
        s_rating += self.OUTLOOK_ADJUSTMENT.get(self.inputs.rating_outlook, 0.0)
        s_spread = self.score_metric(self.inputs.spread, self.SPREAD_THRESHOLDS_BY_DURATION[self.spread_bucket()])
        s_duration = self.score_metric(self.inputs.duration, [2, 4, 6, 8])

        return round(min(max((s_rating * 0.40) + (s_spread * 0.40) + (s_duration * 0.20), 1.0), 5.0), 2)

    def calc_qualitative_risk(self) -> float:
        return round(min(max(self.inputs.qualitative_risk, 1.0), 5.0), 2)

    def get_final_score(self) -> float:
        score = (
            self.calc_fundamental_risk() * 0.35
            + self.calc_liquidity_refinancing_risk() * 0.25
            + self.calc_structural_risk() * 0.18
            + self.calc_market_pricing_risk() * 0.12
            + self.calc_qualitative_risk() * 0.10
        )
        return round(min(max(score, 1.0), 5.0), 2)

    @staticmethod
    def get_risk_label(score: float) -> Tuple[str, str]:
        if score < 2.0: return "נמוך", "#00cc96"
        if score < 2.8: return "מתון", "#7BC8A4"
        if score < 3.5: return "בינוני", "#FFA15A"
        if score < 4.2: return "גבוה", "#EF553B"
        return "קריטי", "#C0392B"

    def get_recommendation(self, score: float) -> str:
        if score < 2.0: return "🟢 מומלץ: האיגרת מציגה פרופיל סיכון-תשואה טוב ומבנה אשראי סביר."
        if score < 2.8: return "🟡 ראוי לבחינה: האיגרת יכולה להתאים בתנאי שהתמחור נשאר סביר."
        if score < 3.5: return "🟠 השקעה ספקולטיבית: דורשת בחינה זהירה ומעקב צמוד (לוח סילוקין, בטוחות)."
        if score < 4.2: return "🔴 רמת סיכון גבוהה: מתאימה רק לאחר בדיקה מעמיקה של מקורות ושימושים והיתכנות מחזור."
        return "⛔ אזהרת מצוקה (Distress): נדרשת הבנה מעמיקה של תרחישי קיצון והסדרי חוב אפשריים."

    def get_metrics_summary(self) -> List[str]:
        items = []
        nd = self.derived["nd_ebitda"]
        cov = self.derived["coverage"]
        su = self.derived["sources_to_uses_12m"]
        cs = self.derived["cash_to_st_debt"]

        if nd is not None and nd > 5: items.append(f"מינוף מהותי: חוב נטו ל-EBITDA של {nd:.2f}x")
        if cov is not None and cov < 2: items.append(f"כיסוי ריבית חלש יחסית: {cov:.2f}x")
        if su is not None and su < 1.0: items.append(f"מקורות לשימושים 12 חודשים מתחת ל-1: {su:.2f}x")
        if cs is not None and cs < 0.7: items.append(f"מזומן מול חלויות 12 חודשים חלש: {cs:.2f}x")
        if self.inputs.spread > 4: items.append(f"מרווח גבוה לשוק המקומי: {self.inputs.spread:.2f}%")
        if self.inputs.rating_outlook in ["שלילי", "בבחינה"]: items.append(f"אופק דירוג מאותת על לחץ: {self.inputs.rating_outlook}")
        if self.inputs.market_liquidity == "נמוכה": items.append("סחירות נמוכה יחסית עלולה להקשות על כניסה ויציאה")
        if self.inputs.covenant_strength == "חלש": items.append("חבילת אמות המידה חלשה יחסית")

        if not items: items.append("לא זוהו כרגע נורות אזהרה חריגות במודל הבסיסי")
        return items

    def get_score_breakdown(self) -> Dict[str, float]:
        return {
            "פונדמנטלי": self.calc_fundamental_risk(),
            "נזילות ומיחזור": self.calc_liquidity_refinancing_risk(),
            "מבנה סדרה": self.calc_structural_risk(),
            "תמחור שוק": self.calc_market_pricing_risk(),
            "איכותני": self.calc_qualitative_risk(),
            "ציון סופי": self.get_final_score(),
        }

    def build_record(self) -> Dict[str, Any]:
        final_score = self.get_final_score()
        risk_label, risk_color = self.get_risk_label(final_score)
        return asdict(BondRecord(
            name=self.inputs.name,
            created_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            inputs=asdict(self.inputs),
            derived=self.derived,
            scores={**self.get_score_breakdown(), "risk_label": risk_label, "risk_color": risk_color}
        ))


CREAM = "#F5EDD6"
GOLD = "#C9A96E"
PANEL = "#12161F"

def create_gauge(score: float, title: str) -> go.Figure:
    if score < 2.0: color = "#00cc96"
    elif score < 3.5: color = "#FFA15A"
    else: color = "#EF553B"

    fig = go.Figure(
        go.Indicator(
            mode="gauge",
            value=score,
            domain={"x": [0, 1], "y": [0, 0.85]},
            title={"text": title, "font": {"size": 15, "color": CREAM}},
            gauge={
                "axis": {"range": [1, 5], "tickwidth": 1, "tickcolor": GOLD},
                "bar": {"color": color, "thickness": 0.3},
                "bgcolor": PANEL,
                "borderwidth": 1,
                "bordercolor": GOLD,
                "steps": [
                    {"range": [1, 2], "color": "rgba(0,204,150,0.13)"},
                    {"range": [2, 3.5], "color": "rgba(255,161,90,0.13)"},
                    {"range": [3.5, 5], "color": "rgba(239,85,59,0.13)"},
                ],
                "threshold": {"line": {"color": GOLD, "width": 3}, "thickness": 0.85, "value": score},
            },
        )
    )
    fig.add_annotation(x=0.5, y=0.18, text=f"{score:.2f}", showarrow=False, font=dict(size=34, color=GOLD))
    fig.update_layout(height=230, margin=dict(l=10, r=10, t=35, b=10), paper_bgcolor="rgba(0,0,0,0)")
    return fig

def create_comparison_radar(records: List[Dict[str, Any]]) -> go.Figure:
    categories = ["פונדמנטלי", "נזילות ומיחזור", "מבנה סדרה", "תמחור שוק", "איכותני"]
    palette = [GOLD, "#C0392B", "#2980B9", "#27AE60", "#8E44AD", "#E67E22", "#16A085"]

    fig = go.Figure()
    for idx, record in enumerate(records):
        scores = record.get("scores", {})
        vals = [scores.get(cat, 3.0) for cat in categories]
        vals_loop = vals + [vals[0]]
        theta_loop = categories + [categories[0]]
        color = palette[idx % len(palette)]

        fill_c = color
        if color.startswith("#"):
            h = color.lstrip("#")
            fill_c = f"rgba({int(h[0:2], 16)}, {int(h[2:4], 16)}, {int(h[4:6], 16)}, 0.15)"

        fig.add_trace(go.Scatterpolar(
            r=vals_loop, theta=theta_loop, fill="toself",
            name=record.get("name", f"איגרת {idx + 1}"),
            line=dict(color=color, width=2),
            fillcolor=fill_c
        ))

    fig.update_layout(
        polar=dict(
            bgcolor=PANEL,
            radialaxis=dict(visible=True, range=[1, 5], tickfont=dict(color=CREAM, size=9),
                            gridcolor="rgba(201,169,110,0.2)", linecolor="rgba(201,169,110,0.3)"),
            angularaxis=dict(tickfont=dict(color=CREAM, size=11),
                             gridcolor="rgba(201,169,110,0.2)", linecolor="rgba(201,169,110,0.3)")
        ),
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color=CREAM),
        showlegend=False, 
        margin=dict(l=50, r=50, t=30, b=30),
    )
    return fig

APP_CSS = """
<style>
:root {
  --gold: #C9A96E;
  --cream: #F5EDD6;
  --dark: #0B0E14;
  --panel: #12161F;
  --border: rgba(201,169,110,0.35);
}

.stApp, .stApp > header, [data-testid="stAppViewContainer"] {
  background-color: var(--dark) !important;
  color: var(--cream) !important;
}

/* ביטול ההשפעה הדורסנית של RTL על אייקונים מובנים */
p, div, label, h1, h2, h3, .stMarkdown {
  direction: rtl !important;
  text-align: right !important;
  color: var(--cream) !important;
}

/* הגנה על אייקוני נגישות ו-Dropdowns של Streamlit */
span.material-symbols-rounded {
  direction: ltr !important;
  font-family: "Material Symbols Rounded" !important;
  color: var(--gold) !important;
}
.st-visually-hidden, .visually-hidden { 
    display: none !important; 
}

/* עיצוב רקעים של תיבות בחירה נפתחות (Dropdowns) */
[data-baseweb="popover"] > div, [data-baseweb="menu"], div[role="listbox"], ul[role="listbox"] {
  background-color: var(--panel) !important;
}
li[role="option"] {
  background-color: var(--panel) !important;
}
li[role="option"]:hover, li[aria-selected="true"] {
  background-color: #1e2430 !important;
}
li[role="option"] span {
  color: var(--cream) !important;
}

[data-testid="stMetricValue"] div { color: var(--cream) !important; }
[data-testid="stMetricLabel"] * { color: #A8A8A8 !important; }
[data-testid="stMetricDelta"] svg { display: none !important; }

.block-title {
  font-size: 0.83rem;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--gold) !important;
  margin-bottom: 10px;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--border);
}
.card {
  background: rgba(18,22,31,0.8);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 16px 18px;
  margin-bottom: 10px;
}
.recommendation-box {
  background: rgba(201,169,110,0.06);
  border: 1px solid var(--border);
  border-right: 4px solid var(--gold);
  border-radius: 10px;
  padding: 16px;
  margin-top: 8px;
}
.risk-badge {
  display: inline-block;
  padding: 6px 14px;
  border-radius: 999px;
  font-size: 0.9rem;
  border: 1px solid var(--border);
}
.small-muted {
  color: #A8A8A8 !important;
  font-size: 0.92rem;
}
[data-testid="stMetric"] {
  background: var(--panel) !important;
  border: 1px solid var(--border) !important;
  border-radius: 10px !important;
  padding: 10px 14px !important;
}
.stButton > button[kind="primary"] {
  background: linear-gradient(135deg, #B8935A, #C9A96E) !important;
  color: #0B0E14 !important;
  border: 1px solid var(--gold) !important;
  border-radius: 10px !important;
  font-weight: 700 !important;
}
.stButton > button {
  border-radius: 10px !important;
}

/* טבלת HTML מותאמת לגלילה RTL */
.table-container {
    overflow-x: auto;
    width: 100%;
    direction: rtl;
    margin-bottom: 15px;
}
.custom-table {
    width: 100%;
    border-collapse: collapse;
    color: var(--cream);
}
.custom-table th {
    color: var(--gold);
    border-bottom: 1px solid var(--border);
    padding: 12px 15px;
    text-align: right;
    white-space: nowrap;
    background: rgba(18,22,31,0.9);
}
.custom-table td {
    border-bottom: 1px solid rgba(255,255,255,0.05);
    padding: 10px 15px;
    text-align: right;
    white-space: nowrap;
}
.custom-table tr:hover {
    background: rgba(255,255,255,0.03);
}
</style>
"""

def fmt_ratio(value: Optional[float], suffix: str = "x") -> str:
    if value is None: return "לא זמין"
    return f"{value:.2f}{suffix}"

def fmt_pct(value: Optional[float]) -> str:
    if value is None: return "לא זמין"
    return f"{value:.2f}%"

def build_input_object(values: Dict[str, Any]) -> BondInputs:
    return BondInputs(
        name=values["name"].strip(), sector=values["sector"], rating=values["rating"],
        rating_outlook=values["rating_outlook"], linkage_type=values["linkage_type"],
        expected_inflation=values["expected_inflation"], collateral_type=values["collateral_type"],
        seniority=values["seniority"], covenant_strength=values["covenant_strength"], 
        market_liquidity=values["market_liquidity"], ytm=float(values["ytm"]), 
        spread=float(values["spread"]), duration=float(values["duration"]),
        total_debt=float(values["total_debt"]), cash=float(values["cash"]),
        ebitda=safe_float(values.get("ebitda")), operating_profit=safe_float(values.get("operating_profit")),
        interest_expense=safe_float(values.get("interest_expense")), debt_due_12m=float(values["debt_due_12m"]),
        expected_cashflow_12m=float(values["expected_cashflow_12m"]), unused_credit_lines=float(values["unused_credit_lines"]),
        capex_12m=float(values["capex_12m"]), dividends_12m=float(values["dividends_12m"]),
        ltv=safe_float(values.get("ltv")), debt_to_nav=safe_float(values.get("debt_to_nav")),
        equity_ratio=safe_float(values.get("equity_ratio")), equity_to_assets=safe_float(values.get("equity_to_assets")),
        qualitative_risk=float(values["qualitative_risk"]),
    )

def input_validation_errors(values: Dict[str, Any]) -> List[str]:
    errors = []
    sector = values["sector"]
    config = SECTOR_FIELD_CONFIG[sector]

    if not values["name"].strip(): errors.append("יש להזין שם אג\"ח.")
    if values["duration"] < 0: errors.append("מח\"מ לא יכול להיות שלילי.")
    if values["spread"] < 0: errors.append("מרווח לא יכול להיות שלילי.")
    if values["ytm"] < -10: errors.append("תשואה לפדיון נראית חריגה מאוד.")
    if values["total_debt"] < 0 or values["cash"] < 0 or values["debt_due_12m"] < 0:
        errors.append("חוב, מזומן וחלויות לא יכולים להיות שליליים.")
    if values["unused_credit_lines"] < 0 or values["capex_12m"] < 0 or values["dividends_12m"] < 0:
        errors.append("קווי אשראי, Capex ודיבידנדים לא יכולים להיות שליליים.")
    if values["qualitative_risk"] < 1 or values["qualitative_risk"] > 5:
        errors.append("ציון איכותני חייב להיות בין 1 ל-5.")

    if config["show_ebitda"] and values.get("ebitda") is None: errors.append("יש להזין EBITDA עבור הסקטור שנבחר.")
    if config["show_operating_profit"] and values.get("operating_profit") is None: errors.append("יש להזין רווח תפעולי עבור הסקטור שנבחר.")
    if config["show_interest_expense"] and values.get("interest_expense") is None: errors.append("יש להזין הוצאות מימון עבור הסקטור שנבחר.")
    if values.get("expected_cashflow_12m") is None: errors.append("יש להזין תזרים / מקורות חזויים ל-12 חודשים.")

    if config["show_ltv"] and values.get("ltv") is None: errors.append("יש להזין LTV עבור נדל\"ן מניב.")
    if config["show_debt_to_nav"] and values.get("debt_to_nav") is None: errors.append("יש להזין חוב ל-NAV עבור חברת החזקות.")
    if config["show_equity_ratio"] and values.get("equity_ratio") is None: errors.append("יש להזין שיעור הון עצמי עבור יזום נדל\"ן.")
    if config["show_equity_to_assets"] and values.get("equity_to_assets") is None: errors.append("יש להזין הון למאזן עבור פיננסים חוץ בנקאיים.")

    return errors

def build_compare_dataframe(records: List[Dict[str, Any]]) -> pd.DataFrame:
    rows = []
    for record in records:
        inputs = record.get("inputs", {})
        derived = record.get("derived", {})
        scores = record.get("scores", {})

        rows.append({
            "שם האג\"ח": record.get("name"),
            "סקטור": inputs.get("sector"),
            "הצמדה": inputs.get("linkage_type"),
            "דירוג": inputs.get("rating"),
            "תשואה נומינלית (חזויה)": fmt_pct(derived.get("nominal_ytm")),
            "מרווח": fmt_pct(inputs.get("spread")),
            "מח\"מ": f"{inputs.get('duration', 0):.2f}",
            "חוב נטו/EBITDA": fmt_ratio(derived.get("nd_ebitda")),
            "כיסוי ריבית": fmt_ratio(derived.get("coverage")),
            "מקורות/שימושים": fmt_ratio(derived.get("sources_to_uses_12m")),
            "בטוחה": inputs.get("collateral_type"),
            "ציון סופי": f"{scores.get('ציון סופי'):.2f}",
            "רמת סיכון": scores.get("risk_label"),
        })
    return pd.DataFrame(rows)

def main() -> None:
    st.set_page_config(page_title="מערכת Pro לניתוח אג\"ח ישראליות", layout="wide", page_icon="⚜️")
    st.markdown(APP_CSS, unsafe_allow_html=True)

    if "saved_bonds" not in st.session_state:
        st.session_state.saved_bonds = load_saved_bonds()

    st.markdown("""
    <div style='text-align:center; padding: 1.2rem 0 1.0rem;'>
        <div style='font-size:0.82rem; letter-spacing:0.18em; color:#A59068; text-align:center !important;'>
            ISRAELI CORPORATE BOND ANALYTICS
        </div>
        <h1 style='color:#C9A96E; text-align:center !important; margin-top:8px;'>
            מערכת Pro לניתוח אג"ח ישראליות
        </h1>
        <div style='color:#A8A8A8; text-align:center !important; margin-top:4px;'>
            מודל ייעודי לשוק המקומי עם דגש על נזילות, מיחזור חוב, בטוחות ותמחור
        </div>
    </div>
    """, unsafe_allow_html=True)

    tab_input, tab_results, tab_compare = st.tabs(["הזנת נתונים", "ניתוח אשראי", "מעבדת השוואות"])

    with tab_input:
        values: Dict[str, Any] = {}
        st.markdown("<div class='block-title'>פרטי אג\"ח בסיסיים</div>", unsafe_allow_html=True)
        t1, t2, t3, t4 = st.columns(4)
        with t1: values["name"] = st.text_input("שם / זיהוי האג\"ח", value="אג\"ח דוגמה").strip()
        with t2: values["sector"] = st.selectbox("סקטור", SECTOR_OPTIONS, index=0)
        with t3: 
            values["linkage_type"] = st.selectbox("סוג הצמדה", LINKAGE_OPTIONS, index=0)
        with t4:
            if values["linkage_type"] == "צמוד מדד":
                values["expected_inflation"] = st.number_input("ציפיית אינפלציה (%)", value=2.5, step=0.1)
            else:
                values["expected_inflation"] = 0.0
                st.number_input("ציפיית אינפלציה (%)", value=0.0, disabled=True, help="רלוונטי רק לאג\"ח צמוד")

        config = SECTOR_FIELD_CONFIG[values["sector"]]
        c1, c2, c3 = st.columns(3, gap="large")

        with c1:
            st.markdown("<div class='block-title'>תמחור ומבנה סדרה</div>", unsafe_allow_html=True)
            values["ytm"] = st.number_input(f"תשואה לפדיון ({'ריאלית' if values['linkage_type']=='צמוד מדד' else 'נומינלית'}) %", value=4.50, step=0.10)
            values["spread"] = st.number_input("מרווח ממשלתי (%)", value=2.00, step=0.10)
            values["duration"] = st.number_input("מח\"מ (שנים)", value=3.00, step=0.10)
            values["rating"] = st.selectbox("דירוג", RATING_OPTIONS, index=8)
            values["rating_outlook"] = st.selectbox("אופק דירוג", OUTLOOK_OPTIONS, index=1)
            values["collateral_type"] = st.selectbox("בטוחות", COLLATERAL_OPTIONS, index=0)
            values["seniority"] = st.selectbox("מעמד הסדרה", SENIORITY_OPTIONS, index=0)
            values["covenant_strength"] = st.selectbox("איכות אמות מידה פיננסיות", COVENANT_OPTIONS, index=1)
            values["market_liquidity"] = st.selectbox("סחירות בשוק", MARKET_LIQUIDITY_OPTIONS, index=1)

        with c2:
            st.markdown("<div class='block-title'>נתוני אשראי עיקריים</div>", unsafe_allow_html=True)
            values["total_debt"] = st.number_input("סך חוב פיננסי", min_value=0.0, value=2000.0, step=50.0)
            values["cash"] = st.number_input("מזומן ונזילות", min_value=0.0, value=350.0, step=25.0)
            values["ebitda"] = None
            if config["show_ebitda"]: values["ebitda"] = st.number_input("EBITDA", value=280.0, step=10.0)
            values["operating_profit"] = None
            if config["show_operating_profit"]: values["operating_profit"] = st.number_input("רווח תפעולי", value=180.0, step=10.0)
            values["interest_expense"] = None
            if config["show_interest_expense"]: values["interest_expense"] = st.number_input("הוצאות מימון", min_value=0.0, value=75.0, step=5.0)

        with c3:
            st.markdown("<div class='block-title'>נזילות, מיחזור ו-12 חודשים קדימה</div>", unsafe_allow_html=True)
            values["debt_due_12m"] = st.number_input("חלויות חוב ב-12 חודשים", min_value=0.0, value=280.0, step=10.0)
            values["expected_cashflow_12m"] = st.number_input(config["label_cashflow"], min_value=0.0, value=220.0, step=10.0)
            values["unused_credit_lines"] = 0.0
            if config["show_unused_credit_lines"]: values["unused_credit_lines"] = st.number_input("קווי אשראי לא מנוצלים", min_value=0.0, value=150.0, step=10.0)
            values["capex_12m"] = 0.0
            if config["show_capex"]: values["capex_12m"] = st.number_input("Capex חזוי ל-12 חודשים", min_value=0.0, value=60.0, step=5.0)
            values["dividends_12m"] = 0.0
            if config["show_dividends"]: values["dividends_12m"] = st.number_input("דיבידנדים / חלוקות חזויות", min_value=0.0, value=20.0, step=5.0)
            values["qualitative_risk"] = st.slider("ציון איכותני ידני", 1.0, 5.0, 3.0, 0.5)

        st.divider()
        st.markdown("<div class='block-title'>מדד ענפי רלוונטי</div>", unsafe_allow_html=True)
        values["ltv"] = None
        values["debt_to_nav"] = None
        values["equity_ratio"] = None
        values["equity_to_assets"] = None

        sp1, sp2, sp3, sp4 = st.columns(4)
        with sp1:
            if config["show_ltv"]: values["ltv"] = st.number_input("LTV (%)", min_value=0.0, max_value=100.0, value=52.0, step=1.0)
        with sp2:
            if config["show_debt_to_nav"]: values["debt_to_nav"] = st.number_input("חוב ל-NAV (%)", min_value=0.0, max_value=100.0, value=24.0, step=1.0)
        with sp3:
            if config["show_equity_ratio"]: values["equity_ratio"] = st.number_input("שיעור הון עצמי (%)", min_value=0.0, max_value=100.0, value=28.0, step=1.0)
        with sp4:
            if config["show_equity_to_assets"]: values["equity_to_assets"] = st.number_input("הון למאזן (%)", min_value=0.0, max_value=100.0, value=18.0, step=1.0)

        if not any([config["show_ltv"], config["show_debt_to_nav"], config["show_equity_ratio"], config["show_equity_to_assets"]]):
            st.info("לסקטור שנבחר אין כרגע שדה ענפי ייעודי במודל, והניתוח יתבסס על הפרמטרים הכלליים.")

    errors = input_validation_errors(values)
    if errors:
        with tab_results:
            for error in errors: st.error(error)
        with tab_compare:
            st.info("השלם את כל השדות הנדרשים בטאב הזנת נתונים.")
        return

    inputs = build_input_object(values)
    analyzer = IsraeliBondAnalyzer(inputs)
    record = analyzer.build_record()
    derived = record["derived"]
    scores = record["scores"]
    final_score = scores["ציון סופי"]
    risk_label = scores["risk_label"]
    risk_color = scores["risk_color"]

    with tab_results:
        st.markdown(f"""
        <div class='card'>
            <div style='display:flex; justify-content:space-between; align-items:flex-start; gap:20px;'>
                <div>
                    <div class='small-muted'>ניתוח אשראי ותמחור</div>
                    <div style='font-size:1.7rem; color:#F5EDD6; margin-top:6px;'>{inputs.name}</div>
                    <div class='small-muted' style='margin-top:6px;'>
                        {inputs.sector} | {inputs.rating} | {inputs.linkage_type}
                    </div>
                </div>
                <div style='text-align:left !important;'>
                    <div class='risk-badge' style='border-color:{risk_color}; color:{risk_color};'>
                        רמת סיכון: {risk_label}
                    </div>
                    <div style='font-size:2.7rem; color:{risk_color}; margin-top:8px;'>
                        {final_score:.2f}
                    </div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        g1, g2, g3 = st.columns(3)
        with g1: st.plotly_chart(create_gauge(scores["פונדמנטלי"], "סיכון פונדמנטלי"), use_container_width=True)
        with g2: st.plotly_chart(create_gauge(scores["נזילות ומיחזור"], "נזילות ומיחזור"), use_container_width=True)
        with g3: st.plotly_chart(create_gauge(final_score, "ציון סופי"), use_container_width=True)

        st.divider()
        st.markdown("<div class='block-title'>מדדים מרכזיים</div>", unsafe_allow_html=True)

        nd_val = derived["nd_ebitda"] or 0
        cov_val = derived["coverage"] or 999
        cs_val = derived["cash_to_st_debt"] or 999
        su_val = derived["sources_to_uses_12m"] or 999

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("חוב נטו / EBITDA", fmt_ratio(derived["nd_ebitda"]), delta="🔴 גבוה" if nd_val > 5 else "🟢 סביר", delta_color="off")
        m2.metric("כיסוי ריבית", fmt_ratio(derived["coverage"]), delta="🔴 חלש" if cov_val < 2 else "🟢 סביר", delta_color="off")
        m3.metric("מזומן / חלויות 12ח", fmt_ratio(derived["cash_to_st_debt"]), delta="🔴 לחוץ" if cs_val < 0.7 else "🟢 סביר", delta_color="off")
        m4.metric("מקורות / שימושים 12ח", fmt_ratio(derived["sources_to_uses_12m"]), delta="🔴 מתחת ל-1" if su_val < 1.0 else "🟢 סביר", delta_color="off")

        st.divider()
        st.markdown("<div class='block-title'>פירוט ציונים</div>", unsafe_allow_html=True)
        b1, b2, b3, b4, b5 = st.columns(5)
        b1.metric("פונדמנטלי", f"{scores['פונדמנטלי']:.2f}")
        b2.metric("נזילות ומיחזור", f"{scores['נזילות ומיחזור']:.2f}")
        b3.metric("מבנה סדרה", f"{scores['מבנה סדרה']:.2f}")
        b4.metric("תמחור שוק", f"{scores['תמחור שוק']:.2f}")
        b5.metric("איכותני", f"{scores['איכותני']:.2f}")

        st.divider()
        left, right = st.columns([1.6, 1.0], gap="large")
        with left:
            st.markdown("<div class='block-title'>הערכת מצב</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='recommendation-box'>{analyzer.get_recommendation(final_score)}</div>", unsafe_allow_html=True)

        with right:
            st.markdown("<div class='block-title'>נקודות לתשומת לב</div>", unsafe_allow_html=True)
            for item in analyzer.get_metrics_summary():
                st.markdown(f"<div class='card' style='padding:10px 14px; margin-bottom:8px;'>{item}</div>", unsafe_allow_html=True)

        st.divider()
        st.markdown("<div class='block-title'>נתוני רקע משלימים</div>", unsafe_allow_html=True)
        
        extra_rows = [
            {"שדה": "תשואה לפדיון (הוזנה)", "ערך": fmt_pct(inputs.ytm)},
            {"שדה": "תשואה נומינלית מותאמת", "ערך": fmt_pct(derived["nominal_ytm"])},
            {"שדה": "מרווח ממשלתי", "ערך": fmt_pct(inputs.spread)},
            {"שדה": "מח\"מ", "ערך": f"{inputs.duration:.2f}"},
            {"שדה": "בטוחה", "ערך": inputs.collateral_type},
            {"שדה": "מעמד", "ערך": inputs.seniority},
            {"שדה": "קובננטים", "ערך": inputs.covenant_strength},
            {"שדה": "סחירות בשוק", "ערך": inputs.market_liquidity},
            {"שדה": "מקורות ל-12 חודשים", "ערך": f"{derived['liquidity_sources_12m']:.2f}"},
            {"שדה": "שימושים ל-12 חודשים", "ערך": f"{derived['uses_12m']:.2f}"},
        ]
        
        st.markdown("<div class='table-container'>" + pd.DataFrame(extra_rows).to_html(index=False, classes="custom-table") + "</div>", unsafe_allow_html=True)

        save_col, export_col = st.columns([1, 1])
        with save_col:
            if st.button("שמור איגרת למעבדה", type="primary", use_container_width=True):
                st.session_state.saved_bonds = upsert_bond_record(record, st.session_state.saved_bonds)
                save_bonds_to_db(st.session_state.saved_bonds)
                st.success(f"האיגרת '{inputs.name}' נשמרה בהצלחה.")

        with export_col:
            single_df = pd.DataFrame([{
                "שם האג\"ח": inputs.name, "סקטור": inputs.sector, "הצמדה": inputs.linkage_type,
                "דירוג": inputs.rating, "אופק": inputs.rating_outlook, "תשואה (מוזנת)": inputs.ytm,
                "תשואה נומינלית מותאמת": derived["nominal_ytm"],
                "מרווח": inputs.spread, "מח\"מ": inputs.duration, "חוב נטו/EBITDA": derived["nd_ebitda"],
                "כיסוי ריבית": derived["coverage"], "מזומן/חלויות 12ח": derived["cash_to_st_debt"],
                "מקורות/שימושים 12ח": derived["sources_to_uses_12m"], "ציון פונדמנטלי": scores["פונדמנטלי"],
                "ציון נזילות": scores["נזילות ומיחזור"], "ציון מבנה סדרה": scores["מבנה סדרה"],
                "ציון תמחור": scores["תמחור שוק"], "ציון איכותני": scores["איכותני"],
                "ציון סופי": scores["ציון סופי"], "רמת סיכון": scores["risk_label"],
            }])
            st.download_button(
                label="ייצא ניתוח נוכחי ל-CSV",
                data=single_df.to_csv(index=False).encode("utf-8-sig"),
                file_name=f"{inputs.name}_bond_analysis.csv",
                mime="text/csv",
                use_container_width=True,
            )

    with tab_compare:
        st.markdown("<div class='block-title'>מעבדת השוואות</div>", unsafe_allow_html=True)
        saved_records = st.session_state.saved_bonds

        if not saved_records:
            st.info("אין עדיין איגרות שמורות במעבדה.")
        else:
            with st.expander("⚙️ ניהול איגרות שמורות", expanded=False):
                names = [r.get("name", "") for r in saved_records]
                selected_delete = st.multiselect("בחר איגרות להסרה", options=names, placeholder=" ")

                c_btn1, c_btn2 = st.columns(2)
                with c_btn1:
                    if st.button("הסר נבחרות", use_container_width=True):
                        if selected_delete:
                            st.session_state.saved_bonds = delete_bonds_by_name(saved_records, selected_delete)
                            save_bonds_to_db(st.session_state.saved_bonds)
                            st.success("האיגרות הוסרו.")
                            st.rerun()

                with c_btn2:
                    if st.button("נקה את כל המאגר", use_container_width=True):
                        st.session_state.saved_bonds = []
                        save_bonds_to_db([])
                        st.success("המאגר נוקה.")
                        st.rerun()

            st.divider()
            st.markdown("<div class='block-title'>טבלת השוואה</div>", unsafe_allow_html=True)
            df_compare = build_compare_dataframe(saved_records)
            
            st.markdown("<div class='table-container'>" + df_compare.to_html(index=False, classes="custom-table") + "</div>", unsafe_allow_html=True)

            st.download_button(
                label="ייצא טבלת השוואה ל-CSV",
                data=df_compare.to_csv(index=False).encode("utf-8-sig"),
                file_name="israeli_bonds_comparison.csv",
                mime="text/csv"
            )

            st.divider()
            c_left, c_right = st.columns([1.2, 1], gap="large")
            with c_left:
                st.markdown("<div class='block-title'>השוואת פרופיל סיכון</div>", unsafe_allow_html=True)
                st.plotly_chart(create_comparison_radar(saved_records), use_container_width=True)
                
                palette = [GOLD, "#C0392B", "#2980B9", "#27AE60", "#8E44AD", "#E67E22", "#16A085"]
                legend_html = "<div style='display: flex; justify-content: center; flex-wrap: wrap; gap: 15px; margin-top: 5px;'>"
                for idx, record in enumerate(saved_records):
                    color = palette[idx % len(palette)]
                    bond_name_legend = record.get("name", f"איגרת {idx + 1}")
                    legend_html += f"<div style='display: flex; align-items: center; gap: 8px;'><span style='color:{color} !important; font-size:1.5rem;'>■</span> <span style='color: var(--cream) !important; font-size: 1rem; font-weight: bold;'>{bond_name_legend}</span></div>"
                legend_html += "</div>"
                st.markdown(legend_html, unsafe_allow_html=True)

            with c_right:
                st.markdown("<div class='block-title'>מיון מהיר לפי ציון סופי</div>", unsafe_allow_html=True)
                df_rank = df_compare[["שם האג\"ח", "רמת סיכון", "ציון סופי"]].copy()
                df_rank["ציון סופי"] = pd.to_numeric(df_rank["ציון סופי"], errors="coerce")
                df_rank = df_rank.sort_values("ציון סופי", ascending=True)
                st.markdown("<div class='table-container'>" + df_rank.to_html(index=False, classes="custom-table") + "</div>", unsafe_allow_html=True)

if __name__ == "__main__":
    main()
