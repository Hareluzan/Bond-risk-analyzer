import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import json
import os

# ============================================================
# מסד נתונים מקומי
# ============================================================
DB_FILE = 'saved_bonds_db.json'

def load_saved_bonds():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return []
    return []

def save_bonds_to_db(bonds_list):
    with open(DB_FILE, 'w', encoding='utf-8') as f:
        json.dump(bonds_list, f, ensure_ascii=False, indent=4)

# ============================================================
# מנוע האנליזה
# ============================================================
class BondProAnalyzer:
    RATING_MAP = {'AAA':1,'AA':1.5,'A':2,'BBB':3,'BB':4,'B':4.5,'CCC':5,'NR':4.5}
    COLLATERAL_DISCOUNT = {
        "ללא ביטחונות (Unsecured)": 0,
        "שעבוד צף על כלל הנכסים (Floating)": 0.3,
        "ערבות חברת אם (Parent Guarantee)": 0.4,
        "שעבוד מניות סחירות (Shares)": 0.6,
        "שעבוד ספציפי על נדל\"ן/נכס חזק (Specific Asset)": 1.0
    }

    def __init__(self, data):
        self.data = data

    def score_metric(self, value, thresholds, reverse=False):
        for i, t in enumerate(thresholds):
            if (value <= t if not reverse else value >= t):
                return i + 1
        return 5

    def calc_company_risk(self):
        nd  = self.data['nd_ebitda']
        cr  = self.data['current_ratio']
        cov = self.data['coverage']
        s_nd  = self.score_metric(nd,  [2, 3.5, 5, 7])
        s_cr  = self.score_metric(cr,  [2, 1.5, 1, 0.8], reverse=True)
        s_cov = self.score_metric(cov, [5, 3, 1.5, 1],   reverse=True)
        return (s_nd * 0.5) + (s_cr * 0.25) + (s_cov * 0.25)

    def calc_bond_risk(self):
        s_spread = self.score_metric(self.data['spread'],   [1.0, 2.5, 4.0, 6.0])
        s_dur    = self.score_metric(self.data['duration'], [2, 4, 7, 10])
        s_rat    = self.RATING_MAP.get(self.data['rating'], 5)
        raw      = (s_spread * 0.45) + (s_rat * 0.35) + (s_dur * 0.20)
        discount = self.COLLATERAL_DISCOUNT.get(self.data['collateral'], 0)
        return max(1.0, min(raw - discount, 5.0))

    def get_final_score(self):
        return round((self.calc_company_risk() * 0.5) + (self.calc_bond_risk() * 0.5), 2)

    def get_risk_label(self, score):
        if score < 2.0:  return ("נמוך", "#00cc96")
        if score < 3.0:  return ("מתון", "#7EC8A0")
        if score < 3.8:  return ("בינוני", "#FFA15A")
        if score < 4.5:  return ("גבוה",   "#EF553B")
        return ("קריטי", "#c0392b")

    def get_recommendation(self, score):
        if score < 2.0:  return "🟢 מומלץ מאוד — איגרת בסיכון נמוך עם פוטנציאל תשואה-לסיכון טוב."
        if score < 3.0:  return "🟡 מומלץ בתנאי מחיר — פרמיה סבירה לסיכון, ראוי לבחון."
        if score < 3.8:  return "🟠 השקעה ספקולטיבית — דורשת מעקב צמוד ומשקל נמוך בתיק."
        if score < 4.5:  return "🔴 לא מומלץ לרוב המשקיעים — סיכון גבוה, שקלו חלופות."
        return "⛔ אזהרת מצוקה — מתאים למשקיעים מנוסים בלבד עם הכרת הסיכונים."

    def get_metrics_summary(self):
        nd  = self.data['nd_ebitda']
        cr  = self.data['current_ratio']
        cov = self.data['coverage']
        sp  = self.data['spread']
        items = []
        if nd  > 4:   items.append(f"מינוף גבוה ({round(nd,1)}x ND/EBITDA)")
        if cr  < 1.0: items.append(f"נזילות לחוצה (יחס שוטף {round(cr,2)})")
        if cov < 1.5: items.append(f"כיסוי ריבית חלש ({round(cov,2)}x)")
        if sp  > 4.0: items.append(f"מרווח גבוה ({round(sp,2)}%) — שוק מתמחר סיכון")
        return items if items else ["כל המדדים בטווחים תקינים ✓"]

# ============================================================
# ויזואליזציה
# ============================================================
GOLD  = "#C9A96E"
CREAM = "#F5EDD6"
DARK  = "#0B0E14"
PANEL = "#12161F"

def create_gauge(score, title):
    color = "#00cc96" if score < 2.5 else ("#FFA15A" if score < 3.8 else "#EF553B")
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=score,
        domain={'x': [0,1], 'y': [0, 0.80]}, # הגבלת הגובה כדי למנוע דריסת טקסט
        title={'text': title, 'font': {'size': 16, 'color': CREAM, 'family': 'Georgia, serif'}},
        number={'font': {'color': GOLD, 'size': 32, 'family': 'Georgia, serif'}},
        gauge={
            'axis': {'range': [1,5], 'tickwidth': 1, 'tickcolor': GOLD,
                     'tickfont': {'color': CREAM, 'size': 10}},
            'bar': {'color': color, 'thickness': 0.3},
            'bgcolor': PANEL,
            'borderwidth': 1,
            'bordercolor': GOLD,
            'steps': [
                {'range': [1, 2.5], 'color': "rgba(0,204,150,0.12)"},
                {'range': [2.5, 3.8], 'color': "rgba(255,161,90,0.12)"},
                {'range': [3.8, 5],  'color': "rgba(239,85,59,0.12)"}
            ],
            'threshold': {'line': {'color': GOLD, 'width': 2}, 'thickness': 0.8, 'value': score}
        }
    ))
    fig.update_layout(
        height=260,
        margin=dict(l=15, r=15, t=65, b=10), # שוליים מורחבים
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(family='Georgia, serif')
    )
    return fig

def create_comparison_radar(bonds_list):
    categories = ['מרווח ממשלתי', 'מח"מ', 'דירוג', 'מינוף', 'נזילות', 'כיסוי ריבית']
    rating_map  = {'AAA':1,'AA':1.5,'A':2,'BBB':3,'BB':4,'B':4.5,'CCC':5,'NR':4.5}
    palette     = [GOLD, "#C0392B", "#2980B9", "#27AE60", "#8E44AD", "#E67E22"]
    fig = go.Figure()

    for idx, bond in enumerate(bonds_list):
        d = bond['data']
        az = BondProAnalyzer(d)
        vals = [
            az.score_metric(d['spread'],   [1.0,2.5,4.0,6.0]),
            az.score_metric(d['duration'], [2,4,7,10]),
            rating_map.get(d['rating'], 5),
            az.score_metric(d['nd_ebitda'], [2,3.5,5,7]),
            az.score_metric(d['current_ratio'], [2,1.5,1,0.8], True),
            az.score_metric(d['coverage'],  [5,3,1.5,1], True)
        ]
        
        clr = palette[idx % len(palette)]
        
        # המרה בטוחה של צבע Hex ל-RGBA למניעת קריסות
        if clr.startswith("#"):
            h = clr.lstrip("#")
            fill_c = f"rgba({int(h[0:2], 16)}, {int(h[2:4], 16)}, {int(h[4:6], 16)}, 0.15)"
        else:
            fill_c = clr

        fig.add_trace(go.Scatterpolar(
            r=vals + [vals[0]],
            theta=categories + [categories[0]],
            fill='toself',
            name=bond['name'],
            line=dict(color=clr, width=2),
            fillcolor=fill_c
        ))

    fig.update_layout(
        polar=dict(
            bgcolor=PANEL,
            radialaxis=dict(visible=True, range=[0,5], tickfont=dict(color=CREAM, size=9),
                            gridcolor="rgba(201,169,110,0.2)", linecolor="rgba(201,169,110,0.3)"),
            angularaxis=dict(tickfont=dict(color=CREAM, size=11, family='Georgia, serif'),
                             gridcolor="rgba(201,169,110,0.2)", linecolor="rgba(201,169,110,0.3)")
        ),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=CREAM, family='Georgia, serif'),
        legend=dict(orientation="h", yanchor="bottom", y=1.08, xanchor="center", x=0.5,
                    font=dict(color=CREAM), bgcolor="rgba(0,0,0,0)", bordercolor=GOLD, borderwidth=1),
        margin=dict(l=60,r=60,t=60,b=40)
    )
    return fig

# ============================================================
# CSS — עיצוב יוקרתי / Art Deco Finance
# ============================================================
LUXURY_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;600;700&family=Cormorant+Garamond:ital,wght@0,300;0,400;1,300&family=Josefin+Sans:wght@300;400&display=swap');

:root {
  --gold:   #C9A96E;
  --gold2:  #E8D5A3;
  --cream:  #F5EDD6;
  --dark:   #0B0E14;
  --panel:  #12161F;
  --border: rgba(201,169,110,0.35);
}

/* Base */
.stApp {
  direction: rtl !important;
  background: var(--dark) !important;
  color: var(--cream) !important;
  font-family: 'Cormorant Garamond', Georgia, serif !important;
}

/* Header ornament line */
.stApp::before {
  content: '';
  display: block;
  height: 3px;
  background: linear-gradient(90deg, transparent, var(--gold), var(--gold2), var(--gold), transparent);
  position: fixed; top: 0; left: 0; right: 0; z-index: 999;
}

/* Main title */
h1 {
  font-family: 'Playfair Display', Georgia, serif !important;
  font-weight: 700 !important;
  font-size: 2.4rem !important;
  color: var(--gold) !important;
  letter-spacing: 0.04em !important;
  text-align: center !important;
  padding-bottom: 0.4em !important;
  border-bottom: 1px solid var(--border) !important;
  margin-bottom: 1.5rem !important;
}

h2, h3 {
  font-family: 'Playfair Display', Georgia, serif !important;
  color: var(--gold2) !important;
  letter-spacing: 0.03em !important;
  text-align: right !important;
}

p, div, label, span, .stMarkdown {
  text-align: right !important;
  font-family: 'Cormorant Garamond', Georgia, serif !important;
}

/* Sidebar */
div[data-testid="stSidebar"] {
  background: var(--panel) !important;
  border-left: 1px solid var(--border) !important;
  direction: rtl !important;
}

/* Tabs */
.stTabs [data-baseweb="tab-list"] {
  gap: 0 !important;
  border-bottom: 1px solid var(--border) !important;
  background: transparent !important;
  justify-content: center !important;
}
.stTabs [data-baseweb="tab"] {
  font-family: 'Josefin Sans', sans-serif !important;
  font-size: 0.82rem !important;
  letter-spacing: 0.15em !important;
  text-transform: uppercase !important;
  color: #7a7060 !important;
  padding: 12px 28px !important;
  background: transparent !important;
  border: none !important;
  border-bottom: 2px solid transparent !important;
  transition: all 0.25s ease !important;
}
.stTabs [aria-selected="true"] {
  color: var(--gold) !important;
  border-bottom: 2px solid var(--gold) !important;
  background: rgba(201,169,110,0.04) !important;
}

/* Input fields */
.stTextInput input, .stNumberInput input, .stSelectbox select {
  background: var(--panel) !important;
  border: 1px solid var(--border) !important;
  border-radius: 2px !important;
  color: var(--cream) !important;
  font-family: 'Cormorant Garamond', Georgia, serif !important;
  font-size: 1rem !important;
  padding: 8px 14px !important;
  transition: border-color 0.2s ease !important;
  text-align: right !important;
}
.stTextInput input:focus, .stNumberInput input:focus {
  border-color: var(--gold) !important;
  box-shadow: 0 0 0 1px rgba(201,169,110,0.3) !important;
}

/* Labels */
.stTextInput label, .stNumberInput label, .stSelectbox label {
  color: var(--gold2) !important;
  font-family: 'Josefin Sans', sans-serif !important;
  font-size: 0.76rem !important;
  letter-spacing: 0.12em !important;
  text-transform: uppercase !important;
}

/* Divider */
hr {
  border: none !important;
  border-top: 1px solid var(--border) !important;
  margin: 1.5rem 0 !important;
}

/* Metric cards */
[data-testid="stMetric"] {
  background: var(--panel) !important;
  border: 1px solid var(--border) !important;
  border-top: 2px solid var(--gold) !important;
  border-radius: 2px !important;
  padding: 18px 20px !important;
}
[data-testid="stMetricLabel"] {
  font-family: 'Josefin Sans', sans-serif !important;
  font-size: 0.72rem !important;
  letter-spacing: 0.12em !important;
  text-transform: uppercase !important;
  color: #7a7060 !important;
}
[data-testid="stMetricValue"] {
  font-family: 'Playfair Display', Georgia, serif !important;
  font-size: 1.8rem !important;
  color: var(--cream) !important;
}

/* Primary button */
.stButton > button[kind="primary"] {
  background: linear-gradient(135deg, #B8935A, #C9A96E) !important;
  border: 1px solid var(--gold) !important;
  border-radius: 2px !important;
  color: var(--dark) !important;
  font-family: 'Josefin Sans', sans-serif !important;
  font-size: 0.78rem !important;
  letter-spacing: 0.15em !important;
  text-transform: uppercase !important;
  font-weight: 600 !important;
  padding: 12px 28px !important;
  transition: all 0.25s ease !important;
}
.stButton > button[kind="primary"]:hover {
  background: linear-gradient(135deg, #C9A96E, #E8D5A3) !important;
  transform: translateY(-1px) !important;
  box-shadow: 0 4px 20px rgba(201,169,110,0.35) !important;
}

/* Secondary button */
.stButton > button {
  background: #2b313e !important;
  border: 1px solid #4a5568 !important;
  border-radius: 6px !important;
}
.stButton > button p {
  color: #ffffff !important;
  font-weight: 600 !important;
  font-family: 'Josefin Sans', sans-serif !important;
  letter-spacing: 0.1em !important;
}
.stButton > button:hover {
  background: #1e2430 !important;
  border-color: #00cc96 !important;
}
.stButton > button:hover p {
  color: #00cc96 !important;
}

/* Expander */
.streamlit-expanderHeader {
  font-family: 'Josefin Sans', sans-serif !important;
  font-size: 0.8rem !important;
  letter-spacing: 0.1em !important;
  color: var(--gold2) !important;
  border: 1px solid var(--border) !important;
  background: var(--panel) !important;
}

/* Dataframe */
.stDataFrame {
  border: 1px solid var(--border) !important;
}

/* Alert / info */
.stAlert {
  background: rgba(201,169,110,0.07) !important;
  border: 1px solid var(--border) !important;
  border-left: 3px solid var(--gold) !important;
  border-radius: 2px !important;
  color: var(--cream) !important;
}

/* Section card helper */
.luxury-card {
  background: var(--panel);
  border: 1px solid var(--border);
  border-top: 2px solid var(--gold);
  border-radius: 2px;
  padding: 24px 28px;
  margin-bottom: 20px;
}
.luxury-section-title {
  font-family: 'Josefin Sans', sans-serif;
  font-size: 0.72rem;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  color: var(--gold);
  margin-bottom: 14px;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--border);
}
.risk-badge {
  display: inline-block;
  font-family: 'Josefin Sans', sans-serif;
  font-size: 0.72rem;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  padding: 4px 14px;
  border-radius: 1px;
}
.recommendation-box {
  background: rgba(201,169,110,0.06);
  border: 1px solid var(--border);
  border-right: 3px solid var(--gold);
  padding: 16px 20px;
  border-radius: 2px;
  font-family: 'Cormorant Garamond', Georgia, serif;
  font-size: 1.05rem;
  color: var(--cream);
  margin-top: 16px;
}
.warning-item {
  color: #FFA15A;
  font-family: 'Josefin Sans', sans-serif;
  font-size: 0.78rem;
  letter-spacing: 0.06em;
  padding: 4px 0;
}
.ok-item {
  color: #00cc96;
  font-family: 'Josefin Sans', sans-serif;
  font-size: 0.78rem;
  letter-spacing: 0.06em;
  padding: 4px 0;
}
</style>
"""

# ============================================================
# ממשק ראשי
# ============================================================
def main():
    st.set_page_config(page_title='מערכת Pro לניתוח אג"ח', layout="wide", page_icon="⚜️")
    st.markdown(LUXURY_CSS, unsafe_allow_html=True)

    if 'saved_bonds' not in st.session_state:
        st.session_state.saved_bonds = load_saved_bonds()

    # כותרת ראשית עם קישוט
    st.markdown("""
    <div style='text-align:center; padding: 2rem 0 1rem; direction: ltr;'>
      <div style='font-family:"Josefin Sans",sans-serif; font-size:0.72rem; letter-spacing:0.22em;
                  text-transform:uppercase; color:#7a7060; margin-bottom:10px;'>
        BOND ANALYTICS PLATFORM
      </div>
      <h1 style='font-family:"Playfair Display",Georgia,serif; color:#C9A96E;
                 font-size:2.4rem; margin:0; letter-spacing:0.04em;'>
        מערכת Pro לניתוח אג"ח
      </h1>
      <div style='width:80px; height:1px; background:linear-gradient(90deg,transparent,#C9A96E,transparent);
                  margin: 14px auto 0;'></div>
    </div>
    """, unsafe_allow_html=True)

    tab_input, tab_results, tab_compare = st.tabs([
        "  ✦  הזנת נתונים  ",
        "  ✦  ניתוח סיכונים  ",
        "  ✦  מעבדת השוואות  "
    ])

    # ──────────────── TAB 1: קלט ────────────────
    with tab_input:
        st.markdown("<div class='luxury-section-title'>פרטי האיגרת</div>", unsafe_allow_html=True)
        bond_name = st.text_input("שם / זיהוי האג\"ח", "אג\"ח דוגמה")
        st.markdown("<br>", unsafe_allow_html=True)

        col1, col2 = st.columns(2, gap="large")

        with col1:
            st.markdown("<div class='luxury-section-title'>🏛 נתוני החברה המנפיקה</div>", unsafe_allow_html=True)
            m_debt  = st.number_input("סך חוב פיננסי", value=1000.0, help="כלל ההתחייבויות נושאות הריבית")
            m_cash  = st.number_input("מזומן ונזילות", value=200.0,  help="מזומנים, שווי מזומנים, השקעות לטווח קצר")
            m_ebitda= st.number_input("EBITDA", value=300.0, help="רווח תפעולי לפני פחת והפחתות")
            st.divider()
            m_assets= st.number_input("נכסים שוטפים", value=500.0)
            m_liab  = st.number_input("התחייבויות שוטפות", value=400.0)
            m_op    = st.number_input("רווח תפעולי", value=150.0)
            m_int   = st.number_input("הוצאות מימון (ריבית)", value=50.0)

        with col2:
            st.markdown("<div class='luxury-section-title'>📋 נתוני האיגרת</div>", unsafe_allow_html=True)
            c1, c2 = st.columns(2)
            with c1: ytm    = st.number_input("תשואה לפדיון (%)", value=4.5, step=0.1)
            with c2: spread = st.number_input("מרווח ממשלתי (%)", value=2.0, step=0.1)

            duration   = st.number_input("מח\"מ (שנים)", value=3.0, step=0.1)
            rating     = st.selectbox("דירוג אשראי", ['AAA','AA','A','BBB','BB','B','CCC','NR'], index=3)
            st.divider()
            st.markdown("<div class='luxury-section-title'>🛡 בטחונות</div>", unsafe_allow_html=True)
            collateral = st.selectbox("סוג הבטוחה", [
                "ללא ביטחונות (Unsecured)",
                "שעבוד צף על כלל הנכסים (Floating)",
                "ערבות חברת אם (Parent Guarantee)",
                "שעבוד מניות סחירות (Shares)",
                "שעבוד ספציפי על נדל\"ן/נכס חזק (Specific Asset)"
            ])

    # ──── חישובים (חוצה טאבים) ────
    nd  = (m_debt - m_cash) / m_ebitda if m_ebitda > 0 else 99
    cr  = m_assets / m_liab if m_liab > 0 else 0
    cov = m_op / m_int     if m_int   > 0 else 99

    current_data = {
        'ytm': ytm, 'spread': spread, 'duration': duration,
        'rating': rating, 'collateral': collateral,
        'nd_ebitda': nd, 'current_ratio': cr, 'coverage': cov
    }
    analyzer  = BondProAnalyzer(current_data)
    comp_risk = analyzer.calc_company_risk()
    bond_risk = analyzer.calc_bond_risk()
    final_score = analyzer.get_final_score()
    risk_label, risk_color = analyzer.get_risk_label(final_score)

    # ──────────────── TAB 2: תוצאות ────────────────
    with tab_results:
        st.markdown(f"""
        <div style='display:flex; align-items:center; justify-content:space-between;
                    margin-bottom:1.5rem; direction:rtl;'>
          <div>
            <div style='font-family:"Josefin Sans",sans-serif; font-size:0.72rem;
                        letter-spacing:0.18em; text-transform:uppercase; color:#7a7060;'>
              דוח ניתוח
            </div>
            <div style='font-family:"Playfair Display",Georgia,serif; font-size:1.7rem;
                        color:#F5EDD6; margin-top:4px;'>{bond_name}</div>
          </div>
          <div style='text-align:left;'>
            <div class="risk-badge" style="background:rgba(201,169,110,0.1);
              border:1px solid {risk_color}; color:{risk_color}; font-size:0.78rem; padding:6px 18px;">
              סיכון {risk_label}
            </div>
            <div style='font-family:"Playfair Display",serif; font-size:2.8rem;
                        color:{risk_color}; text-align:left; margin-top:4px;'>
              {final_score}
            </div>
            <div style='font-family:"Josefin Sans",sans-serif; font-size:0.65rem;
                        letter-spacing:0.1em; color:#7a7060; text-align:left;'>
              ציון 1–5
            </div>
          </div>
        </div>
        """, unsafe_allow_html=True)

        g1, g2, g3 = st.columns(3)
        with g1: st.plotly_chart(create_gauge(comp_risk,  "סיכון מנפיק"), use_container_width=True)
        with g2: st.plotly_chart(create_gauge(bond_risk,  "סיכון האג\"ח"), use_container_width=True)
        with g3: st.plotly_chart(create_gauge(final_score,"ציון סופי"),   use_container_width=True)

        st.divider()

        st.markdown("<div class='luxury-section-title'>מדדים מחושבים</div>", unsafe_allow_html=True)
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("מרווח ממשלתי",   f"{round(spread,2)}%",
                  "⚠ מרווח גבוה" if spread > 4 else "✓ תקין", delta_color="inverse")
        m2.metric("חוב נטו / EBITDA", f"{round(nd,2)}x",
                  "⚠ מינוף גבוה" if nd > 4     else "✓ תקין", delta_color="inverse")
        m3.metric("יחס שוטף",        f"{round(cr,2)}x",
                  "⚠ נזילות לחוצה" if cr < 1   else "✓ תקין")
        m4.metric("כיסוי ריבית",     f"{round(cov,2)}x",
                  "⚠ כיסוי חלש"   if cov < 1.5 else "✓ תקין")

        st.divider()

        rec_col, warn_col = st.columns([3, 2])

        with rec_col:
            st.markdown("<div class='luxury-section-title'>המלצה</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='recommendation-box'>{analyzer.get_recommendation(final_score)}</div>",
                        unsafe_allow_html=True)

        with warn_col:
            st.markdown("<div class='luxury-section-title'>נקודות לתשומת לב</div>", unsafe_allow_html=True)
            for item in analyzer.get_metrics_summary():
                cls = "ok-item" if "✓" in item else "warning-item"
                st.markdown(f"<div class='{cls}'>› {item}</div>", unsafe_allow_html=True)

        st.divider()

        if st.button("⊕  שמור איגרת חוב למעבדה", type="primary"):
            st.session_state.saved_bonds = [
                b for b in st.session_state.saved_bonds if b['name'] != bond_name
            ]
            st.session_state.saved_bonds.append({
                "name": bond_name,
                "data": current_data,
                "score": final_score
            })
            save_bonds_to_db(st.session_state.saved_bonds)
            st.success(f"האג\"ח '{bond_name}' נשמר בהצלחה ✓")
            st.rerun() 

    # ──────────────── TAB 3: השוואות ────────────────
    with tab_compare:
        st.markdown("<div class='luxury-section-title'>מעבדת השוואות</div>", unsafe_allow_html=True)

        if not st.session_state.saved_bonds:
            st.markdown("""
            <div class='recommendation-box' style='text-align:center; padding:32px;'>
              אין איגרות חוב שמורות.<br>
              <span style='font-size:0.85rem; color:#7a7060; font-family:"Josefin Sans",sans-serif;
                           letter-spacing:0.1em;'>
                הוסף איגרות מטאב ניתוח הסיכונים
              </span>
            </div>""", unsafe_allow_html=True)
        else:
            with st.expander("⚙️ ניהול האיגרות השמורות", expanded=False):
                bond_names_list = [b['name'] for b in st.session_state.saved_bonds]
                
                bonds_to_delete = st.multiselect(
                    "בחר איגרות להסרה מהמעבדה:", 
                    options=bond_names_list,
                    placeholder="בחר מרשימת האיגרות..." 
                )
                
                st.markdown("<br>", unsafe_allow_html=True)
                
                cd1, cd2, cd3 = st.columns([1, 1, 2])
                with cd1:
                    if st.button("הסר נבחרים", use_container_width=True):
                        if bonds_to_delete:
                            st.session_state.saved_bonds = [
                                b for b in st.session_state.saved_bonds
                                if b['name'] not in bonds_to_delete
                            ]
                            save_bonds_to_db(st.session_state.saved_bonds)
                            st.rerun()
                with cd2:
                    if st.button("נקה מסד נתונים", use_container_width=True):
                        st.session_state.saved_bonds = []
                        save_bonds_to_db([])
                        st.rerun()

            if st.session_state.saved_bonds:
                st.divider()
                c1, c2 = st.columns([3,2], gap="large")

                with c1:
                    st.markdown("<div class='luxury-section-title'>פיזור סיכונים — רדאר</div>",
                                unsafe_allow_html=True)
                    st.plotly_chart(create_comparison_radar(st.session_state.saved_bonds),
                                   use_container_width=True)

                with c2:
                    st.markdown("<div class='luxury-section-title'>טבלת סיכום</div>",
                                unsafe_allow_html=True)
                    df_compare = pd.DataFrame([{
                        "שם האג\"ח":       b['name'],
                        "ציון":            b['score'],
                        "רמת סיכון":       BondProAnalyzer(b['data']).get_risk_label(b['score'])[0],
                        "מרווח":           f"{round(b['data']['spread'],2)}%",
                        "תשואה לפדיון":   f"{b['data']['ytm']}%",
                        "דירוג":           b['data']['rating'],
                        "ביטחונות":        b['data']['collateral'].split("(")[0].strip()
                    } for b in st.session_state.saved_bonds])
                    st.dataframe(df_compare, hide_index=True, use_container_width=True)


if __name__ == "__main__":
    main()
