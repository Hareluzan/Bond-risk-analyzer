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
    collateral_type: str
    seniority: str
    covenant_strength: str
    market_liquidity: str

    ytm: float
    spread: float
    duration: float

    total_debt: float
    cash: float
    ebitda: float
    operating_profit: float
    interest_expense: float

    debt_due_12m: float
    expected_ffo_12m: float
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
        "AAA": 1.0,
        "AA+": 1.2, "AA": 1.4, "AA-": 1.6,
        "A+": 1.9, "A": 2.1, "A-": 2.4,
        "BBB+": 2.8, "BBB": 3.1, "BBB-": 3.4,
        "BB+": 3.8, "BB": 4.1, "BB-": 4.3,
        "B+": 4.5, "B": 4.7, "B-": 4.8,
        "CCC": 5.0, "CC": 5.0, "C": 5.0, "NR": 4.6
    }

    OUTLOOK_ADJUSTMENT = {
        "חיובי": -0.15,
        "יציב": 0.0,
        "שלילי": 0.20,
        "בבחינה": 0.30
    }

    COLLATERAL_SCORE = {
        "ללא בטוחה": 5.0,
        "שעבוד צף": 4.2,
        "ערבות חברת אם": 3.4,
        "שעבוד מניות": 3.0,
        "שעבוד ספציפי על נכס": 2.2,
        "שעבוד חזק עם יחס כיסוי גבוה": 1.5
    }

    SENIORITY_SCORE = {
        "בכירה": 1.5,
        "רגילה": 2.8,
        "נחותה": 4.5
    }

    COVENANT_SCORE = {
        "חזק": 1.8,
        "בינוני": 3.0,
        "חלש": 4.4
    }

    MARKET_LIQUIDITY_SCORE = {
        "גבוהה": 1.8,
        "בינונית": 3.0,
        "נמוכה": 4.4
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
    def score_metric(
        value: Optional[float],
        thresholds: List[float],
        reverse: bool = False,
        missing_score: float = 5.0,
    ) -> float:
        if value is None:
            return missing_score

        for i, t in enumerate(thresholds):
            if (value <= t and not reverse) or (value >= t and reverse):
                return float(i + 1)
        return 5.0

    def build_derived_metrics(self) -> Dict[str, Optional[float]]:
        net_debt = self.inputs.total_debt - self.inputs.cash
        nd_ebitda = None if self.inputs.ebitda <= 0 else net_debt / self.inputs.ebitda
        coverage = None if self.inputs.interest_expense <= 0 else self.inputs.operating_profit / self.inputs.interest_expense
        cash_to_st_debt = None if self.inputs.debt_due_12m <= 0 else self.inputs.cash / self.inputs.debt_due_12m

        uses_12m = self.inputs.debt_due_12m + self.inputs.capex_12m + self.inputs.dividends_12m
        liquidity_sources = self.inputs.cash + self.inputs.expected_ffo_12m + self.inputs.unused_credit_lines
        sources_to_uses_12m = None if uses_12m <= 0 else liquidity_sources / uses_12m

        return {
            "net_debt": round(net_debt, 2),
            "nd_ebitda": None if nd_ebitda is None else round(nd_ebitda, 2),
            "coverage": None if coverage is None else round(coverage, 2),
            "cash_to_st_debt": None if cash_to_st_debt is None else round(cash_to_st_debt, 2),
            "sources_to_uses_12m": None if sources_to_uses_12m is None else round(sources_to_uses_12m, 2),
            "liquidity_sources_12m": round(liquidity_sources, 2),
            "uses_12m": round(uses_12m, 2),
        }

    def spread_bucket(self) -> str:
        if self.inputs.duration <= 2:
            return "short"
        if self.inputs.duration <= 5:
            return "mid"
        return "long"

    def sector_specific_metric_score(self) -> Tuple[float, str]:
        sector = self.inputs.sector

        if sector == "נדל\"ן מניב":
            score = self.score_metric(self.inputs.ltv, [45, 55, 65, 75], reverse=False, missing_score=4.0)
            return score, "LTV"

        if sector == "חברת החזקות":
            score = self.score_metric(self.inputs.debt_to_nav, [15, 25, 35, 50], reverse=False, missing_score=4.0)
            return score, "חוב ל-NAV"

        if sector == "יזום נדל\"ן":
            score = self.score_metric(self.inputs.equity_ratio, [40, 30, 22, 15], reverse=True, missing_score=4.0)
            return score, "שיעור הון עצמי"

        if sector == "פיננסים חוץ בנקאיים":
            score = self.score_metric(self.inputs.equity_to_assets, [28, 22, 16, 12], reverse=True, missing_score=4.0)
            return score, "הון למאזן"

        score = 3.0
        return score, "מדד ענפי"

    def calc_fundamental_risk(self) -> float:
        sector = self.inputs.sector
        leverage_thresholds = self.LEVERAGE_THRESHOLDS_BY_SECTOR.get(sector, self.LEVERAGE_THRESHOLDS_BY_SECTOR["כללי"])
        coverage_thresholds = self.COVERAGE_THRESHOLDS_BY_SECTOR.get(sector, self.COVERAGE_THRESHOLDS_BY_SECTOR["כללי"])

        s_leverage = self.score_metric(self.derived["nd_ebitda"], leverage_thresholds)
        s_coverage = self.score_metric(self.derived["coverage"], coverage_thresholds, reverse=True)
        s_sector_metric, _ = self.sector_specific_metric_score()

        score = (s_leverage * 0.40) + (s_coverage * 0.35) + (s_sector_metric * 0.25)
        return round(min(max(score, 1.0), 5.0), 2)

    def calc_liquidity_refinancing_risk(self) -> float:
        s_cash_st = self.score_metric(self.derived["cash_to_st_debt"], [1.5, 1.0, 0.7, 0.4], reverse=True)
        s_sources_uses = self.score_metric(self.derived["sources_to_uses_12m"], [1.6, 1.2, 1.0, 0.8], reverse=True)
        s_market_liq = self.MARKET_LIQUIDITY_SCORE.get(self.inputs.market_liquidity, 3.0)

        score = (s_cash_st * 0.30) + (s_sources_uses * 0.50) + (s_market_liq * 0.20)
        return round(min(max(score, 1.0), 5.0), 2)

    def calc_structural_risk(self) -> float:
        s_collateral = self.COLLATERAL_SCORE.get(self.inputs.collateral_type, 4.0)
        s_seniority = self.SENIORITY_SCORE.get(self.inputs.seniority, 2.8)
        s_covenant = self.COVENANT_SCORE.get(self.inputs.covenant_strength, 3.0)

        score = (s_collateral * 0.45) + (s_seniority * 0.20) + (s_covenant * 0.35)
        return round(min(max(score, 1.0), 5.0), 2)

    def calc_market_pricing_risk(self) -> float:
        s_rating = self.RATING_MAP.get(self.inputs.rating, 4.6)
        s_rating += self.OUTLOOK_ADJUSTMENT.get(self.inputs.rating_outlook, 0.0)

        spread_thresholds = self.SPREAD_THRESHOLDS_BY_DURATION[self.spread_bucket()]
        s_spread = self.score_metric(self.inputs.spread, spread_thresholds)
        s_duration = self.score_metric(self.inputs.duration, [2, 4, 6, 8])

        score = (s_rating * 0.40) + (s_spread * 0.40) + (s_duration * 0.20)
        return round(min(max(score, 1.0), 5.0), 2)

    def calc_qualitative_risk(self) -> float:
        return round(min(max(self.inputs.qualitative_risk, 1.0), 5.0), 2)

    def get_final_score(self) -> float:
        fundamental = self.calc_fundamental_risk()
        liquidity = self.calc_liquidity_refinancing_risk()
        structural = self.calc_structural_risk()
        market = self.calc_market_pricing_risk()
        qualitative = self.calc_qualitative_risk()

        score = (
            fundamental * 0.35
            + liquidity * 0.25
            + structural * 0.18
            + market * 0.12
            + qualitative * 0.10
        )
        return round(min(max(score, 1.0), 5.0), 2)

    @staticmethod
    def get_risk_label(score: float) -> Tuple[str, str]:
        if score < 2.0:
            return "נמוך", "#00cc96"
        if score < 2.8:
            return "מתון", "#7BC8A4"
        if score < 3.5:
            return "בינוני", "#FFA15A"
        if score < 4.2:
            return "גבוה", "#EF553B"
        return "קריטי", "#C0392B"

    def get_recommendation(self, score: float) -> str:
        if score < 2.0:
            return "🟢 מומלץ: האיגרת מציגה פרופיל סיכון-תשואה טוב ומבנה אשראי סביר."
        if score < 2.8:
            return "🟡 ראוי לבחינה: האיגרת יכולה להתאים בתנאי שהתמחור נשאר סביר."
        if score < 3.5:
            return "🟠 השקעה ספקולטיבית: דורשת בחינה זהירה ומעקב צמוד (לוח סילוקין, בטוחות)."
        if score < 4.2:
            return "🔴 רמת סיכון גבוהה: מתאימה רק לאחר בדיקה מעמיקה של מקורות ושימושים והיתכנות מחזור."
        return "⛔ אזהרת מצוקה (Distress): נדרשת הבנה מעמיקה של תרחישי קיצון והסדרי חוב אפשריים."

    def get_metrics_summary(self) -> List[str]:
        items: List[str] = []

        nd = self.derived["nd_ebitda"]
        cov = self.derived["coverage"]
        s_u = self.derived["sources_to_uses_12m"]
        c_st = self.derived["cash_to_st_debt"]

        if nd is not None and nd > 5:
            items.append(f"מינוף מהותי: חוב נטו ל-EBITDA של {nd:.2f}x")
        if cov is not None and cov < 2:
            items.append(f"כיסוי ריבית חלש יחסית: {cov:.2f}x")
        if s_u is not None and s_u < 1.0:
            items.append(f"מקורות לשימושים (12 ח') מתחת ל-1: {s_u:.2f}x")
        if c_st is not None and c_st < 0.7:
            items.append(f"מזומן מול חלויות (12 ח') לחוץ: {c_st:.2f}x")
        if self.inputs.spread > 4:
            items.append(f"מרווח גבוה לשוק המקומי: {self.inputs.spread:.2f}%")
        if self.inputs.rating_outlook in ["שלילי", "בבחינה"]:
            items.append(f"אופק דירוג מאותת על לחץ: {self.inputs.rating_outlook}")
        if self.inputs.market_liquidity == "נמוכה":
            items.append("סחירות נמוכה יחסית עלולה להקשות על כניסה ויציאה")
        if self.inputs.covenant_strength == "חלש":
            items.append("חבילת אמות המידה (Covenants) חלשה יחסית")

        if not items:
            items.append("✓ לא זוהו כרגע נורות אזהרה חריגות במודל הבסיסי")

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

        record = BondRecord(
            name=self.inputs.name,
            created_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            inputs=asdict(self.inputs),
            derived=self.derived,
            scores={
                **self.get_score_breakdown(),
                "risk_label": risk_label,
                "risk_color": risk_color,
            },
        )
        return asdict(record)


# ============================================================
# גרפים
# ============================================================
CREAM = "#F5EDD6"
GOLD = "#C9A96E"
PANEL = "#12161F"


def create_gauge(score: float, title: str) -> go.Figure:
    if score < 2.0:
        color = "#00cc96"
    elif score < 3.5:
        color = "#FFA15A"
    else:
        color = "#EF553B"

    # ביטול המספר המובנה והצגתו ידנית כדי למנוע תזוזות במסך
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
                "threshold": {
                    "line": {"color": GOLD, "width": 3},
                    "thickness": 0.85,
                    "value": score
                },
            },
        )
    )

    fig.add_annotation(
        x=0.5,
        y=0.15,
        text=f"{score:.2f}",
        showarrow=False,
        font=dict(size=36, color=GOLD)
    )
    fig.update_layout(
        height=240,
        margin=dict(l=10, r=10, t=35, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
    )
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
        
        clr = palette[idx % len(palette)]
        
        # המרת צבע שקופה בטוחה 
        if clr.startswith("#"):
            h = clr.lstrip("#")
            fill_c = f"rgba({int(h[0:2], 16)}, {int(h[2:4], 16)}, {int(h[4:6], 16)}, 0.15)"
        else:
            fill_c = clr

        fig.add_trace(
            go.Scatterpolar(
                r=vals_loop,
                theta=theta_loop,
                fill="toself",
                name=record.get("name", f"איגרת {idx+1}"),
                line=dict(color=clr, width=2),
                fillcolor=fill_c,
            )
        )

    fig.update_layout(
        polar=dict(
            bgcolor=PANEL,
            radialaxis=dict(
                visible=True,
                range=[1, 5],
                tickfont=dict(color=CREAM, size=9),
                gridcolor="rgba(201,169,110,0.2)",
                linecolor="rgba(201,169,110,0.3)"
            ),
            angularaxis=dict(
                tickfont=dict(color=CREAM, size=11),
                gridcolor="rgba(201,169,110,0.2)",
                linecolor="rgba(201,169,110,0.3)"
            ),
        ),
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color=CREAM),
        legend=dict(
            orientation="h",
            yanchor="top",
            y=-0.12,
            xanchor="center",
            x=0.5,
            bgcolor="rgba(0,0,0,0)"
        ),
        margin=dict(l=60, r=60, t=30, b=70),
    )
    return fig


# ============================================================
# עיצוב
# ============================================================
APP_CSS = """
<style>
:root {
  --gold: #C9A96E;
  --cream: #F5EDD6;
  --dark: #0B0E14;
  --panel: #12161F;
  --border: rgba(201,169,110,0.35);
}

.stApp {
  direction: rtl !important;
  background: var(--dark) !important;
  color: var(--cream) !important;
}

h1, h2, h3, .stMarkdown, label, p, div, span {
  direction: rtl !important;
  text-align: right !important;
}

.st-visually-hidden, .visually-hidden {
    display: none !important;
}

.block-title {
  font-size: 0.83rem;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--gold);
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
  color: #A8A8A8;
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

div[data-testid="stDataFrame"] {
  border: 1px solid var(--border);
  border-radius: 10px;
}
</style>
"""


# ============================================================
# פונקציות עזר UI
# ============================================================
def fmt_ratio(value: Optional[float], suffix: str = "x") -> str:
    if value is None:
        return "לא זמין"
    return f"{value:.2f}{suffix}"


def fmt_pct(value: Optional[float]) -> str:
    if value is None:
        return "לא זמין"
    return f"{value:.2f}%"


def build_input_object(values: Dict[str, Any]) -> BondInputs:
    return BondInputs(
        name=values["name"].strip(),
        sector=values["sector"],
        rating=values["rating"],
        rating_outlook=values["rating_outlook"],
        linkage_type=values["linkage_type"],
        collateral_type=values["collateral_type"],
        seniority=values["seniority"],
        covenant_strength=values["covenant_strength"],
        market_liquidity=values["market_liquidity"],
        ytm=float(values["ytm"]),
        spread=float(values["spread"]),
        duration=float(values["duration"]),
        total_debt=float(values["total_debt"]),
        cash=float(values["cash"]),
        ebitda=float(values["ebitda"]),
        operating_profit=float(values["operating_profit"]),
        interest_expense=float(values["interest_expense"]),
        debt_due_12m=float(values["debt_due_12m"]),
        expected_ffo_12m=float(values["expected_ffo_12m"]),
        unused_credit_lines=float(values["unused_credit_lines"]),
        capex_12m=float(values["capex_12m"]),
        dividends_12m=float(values["dividends_12m"]),
        ltv=safe_float(values.get("ltv")),
        debt_to_nav=safe_float(values.get("debt_to_nav")),
        equity_ratio=safe_float(values.get("equity_ratio")),
        equity_to_assets=safe_float(values.get("equity_to_assets")),
        qualitative_risk=float(values["qualitative_risk"]),
    )


def input_validation_errors(values: Dict[str, Any]) -> List[str]:
    errors = []

    if not values["name"].strip():
        errors.append("יש להזין שם אג\"ח.")
    if values["duration"] < 0:
        errors.append("מח\"מ לא יכול להיות שלילי.")
    if values["spread"] < 0:
        errors.append("מרווח לא יכול להיות שלילי.")
    if values["ytm"] < -10:
        errors.append("תשואה לפדיון נראית חריגה מאוד.")
    if values["debt_due_12m"] < 0 or values["expected_ffo_12m"] < 0 or values["unused_credit_lines"] < 0:
        errors.append("חלויות, FFO וקווי אשראי לא יכולים להיות שליליים.")
    if values["capex_12m"] < 0 or values["dividends_12m"] < 0:
        errors.append("Capex ודיבידנדים חזויים לא יכולים להיות שליליים.")
    if values["qualitative_risk"] < 1 or values["qualitative_risk"] > 5:
        errors.append("ציון איכותני חייב להיות בין 1 ל-5.")

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
            "אופק": inputs.get("rating_outlook"),
            "תשואה": fmt_pct(inputs.get("ytm")),
            "מרווח": fmt_pct(inputs.get("spread")),
            "מח\"מ": f"{inputs.get('duration', 0):.2f}",
            "חוב נטו/EBITDA": fmt_ratio(derived.get("nd_ebitda")),
            "כיסוי ריבית": fmt_ratio(derived.get("coverage")),
            "מקורות/שימושים 12ח": fmt_ratio(derived.get("sources_to_uses_12m")),
            "נזילות שוק": inputs.get("market_liquidity"),
            "בטוחה": inputs.get("collateral_type"),
            "קובננטים": inputs.get("covenant_strength"),
            "ציון סופי": scores.get("ציון סופי"),
            "רמת סיכון": scores.get("risk_label"),
            "עודכן": record.get("created_at"),
        })
    return pd.DataFrame(rows)


# ============================================================
# אפליקציה ראשית
# ============================================================
def main() -> None:
    st.set_page_config(page_title="מערכת Pro לניתוח אג\"ח ישראליות", layout="wide", page_icon="⚜️")
    st.markdown(APP_CSS, unsafe_allow_html=True)

    if "saved_bonds" not in st.session_state:
        st.session_state.saved_bonds = load_saved_bonds()

    st.markdown(
        """
        <div style='text-align:center; padding: 1.2rem 0 1.0rem;'>
            <div style='font-size:0.82rem; letter-spacing:0.18em; color:#A59068; text-align:center;'>
                ISRAELI CORPORATE BOND ANALYTICS
            </div>
            <h1 style='color:#C9A96E; text-align:center; margin-top:8px;'>
                מערכת Pro לניתוח אג"ח ישראליות
            </h1>
            <div style='color:#A8A8A8; text-align:center; margin-top:4px;'>
                מודל ייעודי לשוק המקומי עם דגש על נזילות, מיחזור חוב, בטוחות ותמחור
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    tab_input, tab_results, tab_compare = st.tabs([
        "הזנת נתונים",
        "ניתוח אשראי",
        "מעבדת השוואות"
    ])

    # ------------------------------------------------------------
    # טאב 1 - הזנת נתונים
    # ------------------------------------------------------------
    with tab_input:
        st.markdown("<div class='block-title'>פרטי האיגרת והחברה</div>", unsafe_allow_html=True)

        values: Dict[str, Any] = {}

        c_top1, c_top2, c_top3 = st.columns(3)
        with c_top1:
            values["name"] = st.text_input("שם / זיהוי האג\"ח", value="אג\"ח דוגמה").strip()
        with c_top2:
            values["sector"] = st.selectbox("סקטור", SECTOR_OPTIONS, index=0)
        with c_top3:
            values["linkage_type"] = st.selectbox("סוג הצמדה / ריבית", LINKAGE_OPTIONS, index=0)

        col_left, col_mid, col_right = st.columns(3, gap="large")

        with col_left:
            st.markdown("<div class='block-title'>נתוני תמחור וסדרה</div>", unsafe_allow_html=True)
            values["ytm"] = st.number_input("תשואה לפדיון (%)", value=4.50, step=0.10)
            values["spread"] = st.number_input("מרווח ממשלתי (%)", value=2.00, step=0.10)
            values["duration"] = st.number_input("מח\"מ (שנים)", value=3.00, step=0.10)
            values["rating"] = st.selectbox("דירוג", RATING_OPTIONS, index=8)
            values["rating_outlook"] = st.selectbox("אופק דירוג", OUTLOOK_OPTIONS, index=1)
            values["collateral_type"] = st.selectbox("בטוחות", COLLATERAL_OPTIONS, index=0)
            values["seniority"] = st.selectbox("מעמד הסדרה", SENIORITY_OPTIONS, index=0)
            values["covenant_strength"] = st.selectbox("איכות אמות מידה פיננסיות", COVENANT_OPTIONS, index=1)
            values["market_liquidity"] = st.selectbox("סחירות בשוק", MARKET_LIQUIDITY_OPTIONS, index=1)

        with col_mid:
            st.markdown("<div class='block-title'>נתונים פיננסיים בסיסיים</div>", unsafe_allow_html=True)
            values["total_debt"] = st.number_input("סך חוב פיננסי", min_value=0.0, value=2000.0, step=50.0)
            values["cash"] = st.number_input("מזומן ונזילות", min_value=0.0, value=350.0, step=25.0)
            values["ebitda"] = st.number_input("EBITDA", value=280.0, step=10.0)
            values["operating_profit"] = st.number_input("רווח תפעולי", value=180.0, step=10.0)
            values["interest_expense"] = st.number_input("הוצאות מימון", min_value=0.0, value=75.0, step=5.0)

            st.markdown("<div class='small-muted'>אפשר להזין EBITDA או רווח תפעולי שליליים במידת הצורך. המודל יזהה זאת כגורם סיכון.</div>", unsafe_allow_html=True)

        with col_right:
            st.markdown("<div class='block-title'>נזילות, מיחזור ותחזית 12 חודשים</div>", unsafe_allow_html=True)
            values["debt_due_12m"] = st.number_input("חלויות חוב ב-12 חודשים", min_value=0.0, value=280.0, step=10.0)
            values["expected_ffo_12m"] = st.number_input("FFO / תזרים חזוי ל-12 חודשים", min_value=0.0, value=220.0, step=10.0)
            values["unused_credit_lines"] = st.number_input("קווי אשראי לא מנוצלים", min_value=0.0, value=150.0, step=10.0)
            values["capex_12m"] = st.number_input("Capex חזוי ל-12 חודשים", min_value=0.0, value=60.0, step=5.0)
            values["dividends_12m"] = st.number_input("דיבידנדים / חלוקות חזויות", min_value=0.0, value=20.0, step=5.0)
            values["qualitative_risk"] = st.slider("ציון איכותני ידני", min_value=1.0, max_value=5.0, value=3.0, step=0.5)

        st.divider()
        st.markdown("<div class='block-title'>מדד ענפי רלוונטי</div>", unsafe_allow_html=True)

        sp1, sp2, sp3, sp4 = st.columns(4)
        values["ltv"] = None
        values["debt_to_nav"] = None
        values["equity_ratio"] = None
        values["equity_to_assets"] = None

        with sp1:
            if values["sector"] == "נדל\"ן מניב":
                values["ltv"] = st.number_input("LTV (%)", min_value=0.0, max_value=100.0, value=52.0, step=1.0)
            else:
                st.number_input("LTV (%)", value=0.0, disabled=True, help="רלוונטי לנדל\"ן מניב")

        with sp2:
            if values["sector"] == "חברת החזקות":
                values["debt_to_nav"] = st.number_input("חוב ל-NAV (%)", min_value=0.0, max_value=100.0, value=24.0, step=1.0)
            else:
                st.number_input("חוב ל-NAV (%)", value=0.0, disabled=True, help="רלוונטי לחברות החזקה")

        with sp3:
            if values["sector"] == "יזום נדל\"ן":
                values["equity_ratio"] = st.number_input("שיעור הון עצמי (%)", min_value=0.0, max_value=100.0, value=28.0, step=1.0)
            else:
                st.number_input("שיעור הון עצמי (%)", value=0.0, disabled=True, help="רלוונטי ליזום נדל\"ן")

        with sp4:
            if values["sector"] == "פיננסים חוץ בנקאיים":
                values["equity_to_assets"] = st.number_input("הון למאזן (%)", min_value=0.0, max_value=100.0, value=18.0, step=1.0)
            else:
                st.number_input("הון למאזן (%)", value=0.0, disabled=True, help="רלוונטי לפיננסים חוץ בנקאיים")

    errors = input_validation_errors(values)
    if errors:
        for error in errors:
            st.error(error)
        return

    inputs = build_input_object(values)
    analyzer = IsraeliBondAnalyzer(inputs)
    record = analyzer.build_record()
    derived = record["derived"]
    scores = record["scores"]
    final_score = scores["ציון סופי"]
    risk_label = scores["risk_label"]
    risk_color = scores["risk_color"]

    # ------------------------------------------------------------
    # טאב 2 - ניתוח אשראי
    # ------------------------------------------------------------
    with tab_results:
        st.markdown(
            f"""
            <div class='card'>
                <div style='display:flex; justify-content:space-between; align-items:flex-start; gap:20px;'>
                    <div>
                        <div class='small-muted'>ניתוח אשראי ותמחור</div>
                        <div style='font-size:1.7rem; color:#F5EDD6; margin-top:6px;'>{inputs.name}</div>
                        <div class='small-muted' style='margin-top:6px;'>
                            {inputs.sector} | {inputs.rating} | {inputs.linkage_type}
                        </div>
                    </div>
                    <div style='text-align:left;'>
                        <div class='risk-badge' style='border-color:{risk_color}; color:{risk_color};'>
                            רמת סיכון: {risk_label}
                        </div>
                        <div style='font-size:2.7rem; color:{risk_color}; margin-top:8px; text-align:left;'>
                            {final_score:.2f}
                        </div>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

        g1, g2, g3 = st.columns(3)
        with g1:
            st.plotly_chart(create_gauge(scores["פונדמנטלי"], "סיכון פונדמנטלי"), use_container_width=True)
        with g2:
            st.plotly_chart(create_gauge(scores["נזילות ומיחזור"], "נזילות ומיחזור"), use_container_width=True)
        with g3:
            st.plotly_chart(create_gauge(final_score, "ציון סופי"), use_container_width=True)

        st.divider()
        st.markdown("<div class='block-title'>מדדים מרכזיים</div>", unsafe_allow_html=True)

        # תיקון הצבעים והאייקונים בחיווי של ה-Metrics
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("חוב נטו / EBITDA", fmt_ratio(derived["nd_ebitda"]), 
                  delta="🔴 גבוה" if (derived["nd_ebitda"] or 0) > 5 else "🟢 סביר", delta_color="off")
        m2.metric("כיסוי ריבית", fmt_ratio(derived["coverage"]), 
                  delta="🔴 חלש" if (derived["coverage"] is not None and derived["coverage"] < 2) else "🟢 סביר", delta_color="off")
        m3.metric("מזומן / חלויות 12ח", fmt_ratio(derived["cash_to_st_debt"]), 
                  delta="🔴 לחוץ" if (derived["cash_to_st_debt"] is not None and derived["cash_to_st_debt"] < 0.7) else "🟢 סביר", delta_color="off")
        m4.metric("מקורות / שימושים 12ח", fmt_ratio(derived["sources_to_uses_12m"]), 
                  delta="🔴 מתחת ל-1" if (derived["sources_to_uses_12m"] is not None and derived["sources_to_uses_12m"] < 1.0) else "🟢 סביר", delta_color="off")

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
            {"שדה": "תשואה לפדיון", "ערך": fmt_pct(inputs.ytm)},
            {"שדה": "מרווח ממשלתי", "ערך": fmt_pct(inputs.spread)},
            {"שדה": "מח\"מ", "ערך": f"{inputs.duration:.2f}"},
            {"שדה": "בטוחה", "ערך": inputs.collateral_type},
            {"שדה": "מעמד", "ערך": inputs.seniority},
            {"שדה": "קובננטים", "ערך": inputs.covenant_strength},
            {"שדה": "סחירות בשוק", "ערך": inputs.market_liquidity},
            {"שדה": "מקורות ל-12 חודשים", "ערך": f"{derived['liquidity_sources_12m']:.2f}"},
            {"שדה": "שימושים ל-12 חודשים", "ערך": f"{derived['uses_12m']:.2f}"},
        ]
        st.dataframe(pd.DataFrame(extra_rows), hide_index=True, use_container_width=True)

        save_col, export_col = st.columns([1, 1])
        with save_col:
            if st.button("שמור איגרת למעבדה", type="primary", use_container_width=True):
                st.session_state.saved_bonds = upsert_bond_record(record, st.session_state.saved_bonds)
                save_bonds_to_db(st.session_state.saved_bonds)
                st.success(f"האיגרת '{inputs.name}' נשמרה בהצלחה.")
        with export_col:
            # יישור ייצוא איגרת בודדת כך שיכלול את כל הנתונים, כולל הצמדה
            single_df = pd.DataFrame([{
                "שם האג\"ח": inputs.name,
                "סקטור": inputs.sector,
                "הצמדה": inputs.linkage_type,
                "דירוג": inputs.rating,
                "אופק": inputs.rating_outlook,
                "תשואה": inputs.ytm,
                "מרווח": inputs.spread,
                "מח\"מ": inputs.duration,
                "חוב נטו/EBITDA": derived["nd_ebitda"],
                "כיסוי ריבית": derived["coverage"],
                "מזומן/חלויות 12ח": derived["cash_to_st_debt"],
                "מקורות/שימושים 12ח": derived["sources_to_uses_12m"],
                "ציון פונדמנטלי": scores["פונדמנטלי"],
                "ציון נזילות": scores["נזילות ומיחזור"],
                "ציון מבנה סדרה": scores["מבנה סדרה"],
                "ציון תמחור": scores["תמחור שוק"],
                "ציון איכותני": scores["איכותני"],
                "ציון סופי": scores["ציון סופי"],
                "רמת סיכון": scores["risk_label"],
            }])

            st.download_button(
                label="ייצא ניתוח נוכחי ל-CSV",
                data=single_df.to_csv(index=False).encode("utf-8-sig"),
                file_name=f"{inputs.name}_bond_analysis.csv",
                mime="text/csv",
                use_container_width=True,
            )

    # ------------------------------------------------------------
    # טאב 3 - השוואות
    # ------------------------------------------------------------
    with tab_compare:
        st.markdown("<div class='block-title'>מעבדת השוואות</div>", unsafe_allow_html=True)

        saved_records = st.session_state.saved_bonds

        if not saved_records:
            st.info("אין עדיין איגרות שמורות במעבדה.")
        else:
            with st.expander("ניהול איגרות שמורות", expanded=False):
                names = [r.get("name", "") for r in saved_records]
                
                # העלמת ה-Choose an option המציק באנגלית
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

            c_left, c_right = st.columns([1.2, 1], gap="large")
            with c_left:
                st.markdown("<div class='block-title'>השוואת פרופיל סיכון</div>", unsafe_allow_html=True)
                st.plotly_chart(create_comparison_radar(saved_records), use_container_width=True)

            with c_right:
                st.markdown("<div class='block-title'>טבלת השוואה</div>", unsafe_allow_html=True)
                df_compare = build_compare_dataframe(saved_records)
                st.dataframe(df_compare, hide_index=True, use_container_width=True)

                st.download_button(
                    label="ייצא טבלת השוואה ל-CSV",
                    data=df_compare.to_csv(index=False).encode("utf-8-sig"),
                    file_name="israeli_bonds_comparison.csv",
                    mime="text/csv",
                    use_container_width=True,
                )

            st.divider()
            st.markdown("<div class='block-title'>מיון מהיר לפי ציון סופי</div>", unsafe_allow_html=True)

            df_rank = build_compare_dataframe(saved_records).copy()
            df_rank["ציון סופי"] = pd.to_numeric(df_rank["ציון סופי"], errors="coerce")
            df_rank = df_rank.sort_values("ציון סופי", ascending=True)
            st.dataframe(df_rank, hide_index=True, use_container_width=True)


if __name__ == "__main__":
    main()
