import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import io

# ============================================================
# שלב 1: מנוע האנליזה הפיננסית
# ============================================================

class AdvancedBondAnalyzer:
    def __init__(self, ytm, duration, rating, net_debt_ebitda, current_ratio, coverage_ratio):
        self.ytm = ytm
        self.duration = duration
        self.rating = rating.upper()
        self.net_debt_ebitda = net_debt_ebitda
        self.current_ratio = current_ratio
        self.coverage_ratio = coverage_ratio

    def score_ytm(self):
        if self.ytm < 3.0:    return 1
        elif self.ytm <= 5.0: return 2
        elif self.ytm <= 8.0: return 3
        elif self.ytm <= 12.0:return 4
        else:                 return 5

    def score_duration(self):
        if self.duration < 2.0:    return 1
        elif self.duration <= 4.0: return 2
        elif self.duration <= 7.0: return 3
        elif self.duration <= 10.0:return 4
        else:                      return 5

    def score_rating(self):
        ratings_map = {
            'AAA': 1, 'AA': 1, 'A': 2, 'BBB': 3,
            'BB': 4, 'B': 4, 'CCC': 5, 'CC': 5, 'C': 5, 'D': 5, 'NR': 5
        }
        return ratings_map.get(self.rating, 5)

    def score_net_debt_ebitda(self):
        if self.net_debt_ebitda <= 2.0:   return 1
        elif self.net_debt_ebitda <= 3.5: return 2
        elif self.net_debt_ebitda <= 5.0: return 3
        elif self.net_debt_ebitda <= 7.0: return 4
        else:                             return 5

    def score_current_ratio(self):
        if self.current_ratio >= 2.0:   return 1
        elif self.current_ratio >= 1.5: return 2
        elif self.current_ratio >= 1.0: return 3
        elif self.current_ratio >= 0.8: return 4
        else:                           return 5

    def score_coverage(self):
        if self.coverage_ratio >= 5.0:   return 1
        elif self.coverage_ratio >= 3.0: return 2
        elif self.coverage_ratio >= 1.5: return 3
        elif self.coverage_ratio >= 1.0: return 4
        else:                            return 5

    def get_weights(self):
        return {
            'ytm':      st.session_state.get('w_ytm', 0.20),
            'rating':   st.session_state.get('w_rating', 0.15),
            'duration': st.session_state.get('w_duration', 0.15),
            'nd_ebitda':st.session_state.get('w_nd_ebitda', 0.25),
            'current':  st.session_state.get('w_current', 0.15),
            'coverage': st.session_state.get('w_coverage', 0.10),
        }

    def calculate_final_score(self):
        w = self.get_weights()
        final_score = (
            self.score_ytm()             * w['ytm']      +
            self.score_rating()          * w['rating']   +
            self.score_duration()        * w['duration'] +
            self.score_net_debt_ebitda() * w['nd_ebitda']+
            self.score_current_ratio()   * w['current']  +
            self.score_coverage()        * w['coverage']
        )
        return round(final_score, 2)

    def get_score_breakdown(self):
        w = self.get_weights()
        rows = [
            {"פרמטר": "תשואה לפדיון (YTM)",        "ערך גולמי": f"{self.ytm}%",              "ציון (1–5)": self.score_ytm(),             "משקל": f"{int(w['ytm']*100)}%",       "תרומה לציון": round(self.score_ytm()             * w['ytm'],      2)},
            {"פרמטר": "מח\"מ",                        "ערך גולמי": f"{self.duration} שנים",      "ציון (1–5)": self.score_duration(),        "משקל": f"{int(w['duration']*100)}%",  "תרומה לציון": round(self.score_duration()        * w['duration'], 2)},
            {"פרמטר": "דירוג אשראי",                 "ערך גולמי": self.rating,                  "ציון (1–5)": self.score_rating(),          "משקל": f"{int(w['rating']*100)}%",    "תרומה לציון": round(self.score_rating()          * w['rating'],   2)},
            {"פרמטר": "חוב נטו / EBITDA",            "ערך גולמי": f"{round(self.net_debt_ebitda,2)}x", "ציון (1–5)": self.score_net_debt_ebitda(), "משקל": f"{int(w['nd_ebitda']*100)}%","תרומה לציון": round(self.score_net_debt_ebitda() * w['nd_ebitda'],2)},
            {"פרמטר": "יחס שוטף (נזילות)",           "ערך גולמי": f"{round(self.current_ratio,2)}x",   "ציון (1–5)": self.score_current_ratio(),   "משקל": f"{int(w['current']*100)}%",   "תרומה לציון": round(self.score_current_ratio()   * w['current'],  2)},
            {"פרמטר": "יחס כיסוי ריבית",             "ערך גולמי": f"{round(self.coverage_ratio,2)}x",  "ציון (1–5)": self.score_coverage(),        "משקל": f"{int(w['coverage']*100)}%",  "תרומה לציון": round(self.score_coverage()        * w['coverage'], 2)},
        ]
        return pd.DataFrame(rows)


# ============================================================
# שלב 2: גרפים
# ============================================================

def create_gauge_chart(score):
    fig = go.Figure(go.Indicator(
        mode="gauge",
        value=score,
        domain={'x': [0, 1], 'y': [0, 1]},
        title={'text': "מדד סיכון משוקלל", 'font': {'size': 22}},
        gauge={
            'axis': {'range': [1, 5], 'tickwidth': 1, 'tickcolor': "#aaa",
                     'tickvals': [1, 2, 3, 4, 5],
                     'ticktext': ['1<br><sub>בטוח</sub>', '2', '3', '4', '5<br><sub>מסוכן</sub>']},
            'bar': {'color': "rgba(0,0,0,0)"},
            'bgcolor': "rgba(0,0,0,0)",
            'borderwidth': 2,
            'bordercolor': "gray",
            'steps': [
                {'range': [1, 2.5], 'color': "#00cc96"},
                {'range': [2.5, 3.8], 'color': "#FFA15A"},
                {'range': [3.8, 5], 'color': "#EF553B"},
            ],
        }
    ))
    fig.add_annotation(x=0.5, y=0.28, text=f"<b>{score}</b>", showarrow=False, font=dict(size=52, color="white"))
    fig.update_layout(height=350, margin=dict(l=20, r=20, t=60, b=20), paper_bgcolor="rgba(0,0,0,0)")
    return fig

def create_radar_chart(analyzer):
    categories = ['תשואה', 'מח"מ', 'דירוג', 'מינוף\n(Net Debt/EBITDA)', 'נזילות\n(יחס שוטף)', 'כיסוי ריבית']
    values = [
        analyzer.score_ytm(), analyzer.score_duration(), analyzer.score_rating(),
        analyzer.score_net_debt_ebitda(), analyzer.score_current_ratio(), analyzer.score_coverage()
    ]
    values_closed = values + [values[0]]
    cats_closed   = categories + [categories[0]]

    fig = go.Figure(data=go.Scatterpolar(
        r=values_closed, theta=cats_closed,
        fill='toself',
        fillcolor='rgba(99, 110, 250, 0.4)',
        line=dict(color='#636EFA', width=2),
        marker=dict(size=7, color='#636EFA')
    ))
    fig.update_layout(
        polar=dict(
            radialaxis=dict(visible=True, range=[0, 5], tickfont=dict(size=10)),
            angularaxis=dict(tickfont=dict(size=13))
        ),
        showlegend=False, height=420,
        margin=dict(l=50, r=50, t=40, b=40),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)"
    )
    return fig

def create_comparison_bar(bonds_data):
    """גרף השוואה בין אג״חים"""
    names  = [b['name']  for b in bonds_data]
    scores = [b['score'] for b in bonds_data]
    colors = ['#00cc96' if s <= 2.5 else '#FFA15A' if s <= 3.8 else '#EF553B' for s in scores]

    fig = go.Figure(go.Bar(
        x=names, y=scores, marker_color=colors,
        text=[str(s) for s in scores], textposition='outside',
        textfont=dict(size=16, color='white')
    ))
    fig.update_layout(
        yaxis=dict(range=[0, 5.5], title="ציון סיכון"),
        xaxis=dict(title=""),
        height=350,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=20, r=20, t=30, b=20),
        font=dict(color='white')
    )
    fig.add_hline(y=2.5, line_dash="dot", line_color="#00cc96",  annotation_text="גבול נמוך/בינוני")
    fig.add_hline(y=3.8, line_dash="dot", line_color="#FFA15A",  annotation_text="גבול בינוני/גבוה")
    return fig

# ============================================================
# שלב 3: ולידציה ועיבוד CSV
# ============================================================

REQUIRED_COLUMNS = ["Parameter", "Value"]
REQUIRED_PARAMS  = ["Total_Debt", "Cash", "EBITDA", "Current_Assets", "Current_Liabilities", "Operating_Profit", "Interest_Expense"]

def validate_and_parse_csv(uploaded_file):
    """מחזיר (data_dict, error_message). אחד מהם תמיד None."""
    try:
        df = pd.read_csv(uploaded_file)
    except Exception:
        return None, "❌ לא ניתן לקרוא את הקובץ. ודא שמדובר בקובץ CSV תקין."

    missing_cols = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing_cols:
        return None, f"❌ חסרות עמודות בקובץ: {', '.join(missing_cols)}. השתמש בתבנית המצורפת."

    data_dict = dict(zip(df['Parameter'].astype(str).str.strip(),
                         pd.to_numeric(df['Value'], errors='coerce')))

    missing_params = [p for p in REQUIRED_PARAMS if p not in data_dict]
    if missing_params:
        return None, f"❌ חסרים פרמטרים בקובץ: {', '.join(missing_params)}."

    nan_params = [p for p in REQUIRED_PARAMS if pd.isna(data_dict.get(p))]
    if nan_params:
        return None, f"❌ ערכים לא מספריים עבור: {', '.join(nan_params)}."

    ebitda = data_dict["EBITDA"]
    if ebitda <= 0:
        return None, "❌ EBITDA אפס או שלילי – הניתוח אינו אמין עבור חברה בהפסד תפעולי."

    if data_dict["Interest_Expense"] <= 0:
        return None, "❌ הוצאות ריבית חייבות להיות גדולות מ-0."

    if data_dict["Current_Liabilities"] <= 0:
        return None, "❌ התחייבויות שוטפות חייבות להיות גדולות מ-0."

    return data_dict, None

def compute_ratios(data_dict):
    total_debt          = data_dict["Total_Debt"]
    cash                = data_dict["Cash"]
    ebitda              = data_dict["EBITDA"]
    current_assets      = data_dict["Current_Assets"]
    current_liabilities = data_dict["Current_Liabilities"]
    operating_profit    = data_dict["Operating_Profit"]
    interest_expense    = data_dict["Interest_Expense"]

    net_debt_ebitda = (total_debt - cash) / ebitda
    current_ratio   = current_assets / current_liabilities
    coverage_ratio  = operating_profit / interest_expense
    return net_debt_ebitda, current_ratio, coverage_ratio


# ============================================================
# שלב 4: ייצוא תוצאות ל-CSV
# ============================================================

def build_export_csv(analyzer, final_score, net_debt_ebitda, current_ratio, coverage_ratio, bond_name, ytm, duration, rating):
    summary = {
        "שם האג\"ח":          bond_name,
        "תשואה לפדיון (%)":    ytm,
        "מח\"מ (שנים)":         duration,
        "דירוג אשראי":          rating,
        "חוב נטו / EBITDA":     round(net_debt_ebitda, 3),
        "יחס שוטף":             round(current_ratio,   3),
        "יחס כיסוי ריבית":      round(coverage_ratio,  3),
        "ציון סיכון סופי (1–5)": final_score,
    }
    df_summary = pd.DataFrame([summary]).T.reset_index()
    df_summary.columns = ["פרמטר", "ערך"]
    df_breakdown = analyzer.get_score_breakdown()
    
    buf = io.StringIO()
    buf.write("=== סיכום ===\n")
    df_summary.to_csv(buf, index=False, encoding='utf-8-sig')
    buf.write("\n=== פירוט ציונים ===\n")
    df_breakdown.to_csv(buf, index=False, encoding='utf-8-sig')
    return buf.getvalue().encode('utf-8-sig')

# ============================================================
# פונקציית הצגת תוצאות (משותפת ל-Tab 1 ו-Tab 3)
# ============================================================

def _render_results(analyzer, final_score, nd_ebitda, curr_ratio, cov_ratio, bond_name, ytm, duration, rating):
    st.divider()
    st.subheader(f"תוצאות: {bond_name}")

    # ── מדדים ──
    m1, m2, m3 = st.columns(3)
    m1.metric("חוב נטו / EBITDA",   round(nd_ebitda,  2), "מעל 4 = מסוכן" if nd_ebitda  > 4   else "✅ תקין", delta_color="inverse")
    m2.metric("יחס שוטף (נזילות)", round(curr_ratio, 2), "מתחת ל-1 = סכנה" if curr_ratio < 1  else "✅ תקין")
    m3.metric("יחס כיסוי ריבית",   round(cov_ratio,  2), "מתחת ל-1.5 = חלש" if cov_ratio < 1.5 else "✅ תקין")

    st.markdown("<br>", unsafe_allow_html=True)

    # ── גרפים ──
    g1, g2 = st.columns(2)
    with g1:
        st.markdown("### ציון סיכון סופי")
        st.plotly_chart(create_gauge_chart(final_score), use_container_width=True)
        if final_score <= 2.5:
            st.success("✅ החברה יציבה — סיכון נמוך (השקעה סולידית).")
        elif final_score <= 3.8:
            st.warning("⚠️ סיכון בינוני. בחן את תמחור השוק ותנאים מאקרו-כלכליים.")
        else:
            st.error("🚨 אזהרת סיכון חמורה! פרופיל פיננסי חלש — סכנת חדלות פירעון גבוהה.")
    with g2:
        st.markdown("### פרופיל סיכון רב-ממדי")
        st.caption("1 = בטוח · 5 = מסוכן")
        st.plotly_chart(create_radar_chart(analyzer), use_container_width=True)

    # ── פירוט ציונים ──
    st.markdown("### 🗂️ פירוט ציונים ומשקלות")
    st.dataframe(analyzer.get_score_breakdown(), use_container_width=True, hide_index=True)

    # ── ייצוא ──
    st.divider()
    export_csv = build_export_csv(analyzer, final_score, nd_ebitda, curr_ratio, cov_ratio, bond_name, ytm, duration, rating)
    st.download_button(
        label="📤 הורד תוצאות ניתוח (CSV)",
        data=export_csv,
        file_name=f"bond_analysis_{bond_name}.csv",
        mime="text/csv"
    )

# ============================================================
# שלב 5: UI ראשי
# ============================================================

def main():
    st.set_page_config(page_title="מערכת Pro לניתוח אג\"ח", layout="wide", page_icon="📊")

    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Heebo:wght@300;400;700;900&display=swap');

    html, body, [class*="css"] { font-family: 'Heebo', sans-serif !important; }
    .stApp { direction: rtl; background: #0f1117; color: #e8eaf0; }
    p, div, input, label, h1, h2, h3, h4, h5, h6, span { text-align: right !important; }

    div[data-testid="stSidebar"] {
        direction: rtl;
        background: #161b27;
        border-left: 1px solid #2a3045;
    }
    div[data-testid="metric-container"] {
        background: #1c2233;
        border: 1px solid #2a3045;
        border-radius: 12px;
        padding: 16px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.3);
    }
    .stAlert > div { direction: rtl; text-align: right; border-radius: 10px; }

    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] {
        background: #1c2233;
        border-radius: 8px 8px 0 0;
        border: 1px solid #2a3045;
        color: #aab;
        font-weight: 600;
        padding: 8px 20px;
    }
    .stTabs [aria-selected="true"] {
        background: #2563eb !important;
        color: white !important;
        border-color: #2563eb !important;
    }
    .bond-tag {
        display: inline-block;
        background: #2563eb22;
        border: 1px solid #2563eb55;
        border-radius: 20px;
        padding: 3px 14px;
        font-size: 13px;
        color: #60a5fa;
        margin: 2px;
    }
    .section-header {
        font-size: 1.1rem;
        font-weight: 700;
        color: #93c5fd;
        border-bottom: 1px solid #2a3045;
        padding-bottom: 6px;
        margin-bottom: 14px;
    }
    </style>
    """, unsafe_allow_html=True)

    # ── Sidebar ──────────────────────────────────────────────
    with st.sidebar:
        st.image("https://cdn-icons-png.flaticon.com/512/2474/2474069.png", width=80)
        st.markdown("## נתוני שוק")

        ytm      = st.number_input("תשואה לפדיון (%)", value=4.5, step=0.1, min_value=0.0)
        duration = st.number_input("מח\"מ (שנים)",      value=3.0, step=0.1, min_value=0.0)
        rating   = st.selectbox("דירוג אשראי",
                    ['AAA','AA','A','BBB','BB','B','CCC','CC','C','D','NR'], index=3)

        st.divider()

        # ── משקלות מתקדמות ──────────────────────────────────
        with st.expander("⚙️ כוונון משקלות מתקדם"):
            st.caption("סך המשקלות חייב להיות 100%. שנה לפי צרכיך.")
            w_ytm       = st.slider("תשואה לפדיון",        0, 50, 20, 5, key='w_ytm_slider')
            w_rating    = st.slider("דירוג אשראי",         0, 50, 15, 5, key='w_rating_slider')
            w_duration  = st.slider("מח\"מ",                0, 50, 15, 5, key='w_duration_slider')
            w_nd_ebitda = st.slider("חוב נטו / EBITDA",    0, 50, 25, 5, key='w_nd_ebitda_slider')
            w_current   = st.slider("יחס שוטף",            0, 50, 15, 5, key='w_current_slider')
            w_coverage  = st.slider("כיסוי ריבית",          0, 50, 10, 5, key='w_coverage_slider')

            total_w = w_ytm + w_rating + w_duration + w_nd_ebitda + w_current + w_coverage
            if total_w != 100:
                st.error(f"⚠️ סכום המשקלות = {total_w}% (נדרש: 100%)")
            else:
                st.success("✅ סכום המשקלות תקין")
                st.session_state['w_ytm']       = w_ytm       / 100
                st.session_state['w_rating']    = w_rating    / 100
                st.session_state['w_duration']  = w_duration  / 100
                st.session_state['w_nd_ebitda'] = w_nd_ebitda / 100
                st.session_state['w_current']   = w_current   / 100
                st.session_state['w_coverage']  = w_coverage  / 100

    # ── Header ───────────────────────────────────────────────
    st.markdown("# 📊 מערכת Pro לניתוח סיכוני אג\"ח")
    st.markdown("משלבת נתוני שוק עם ניתוח פונדמנטלי של דוחות כספיים | **ציון 1 = בטוח · ציון 5 = מסוכן**")
    st.divider()

    # ── טאבים ראשיים ─────────────────────────────────────────
    tab_single, tab_compare, tab_manual = st.tabs(["🔍 ניתוח אג\"ח בודד", "⚖️ השוואה בין אג\"חות", "✏️ הזנה ידנית"])

    # ======================================================
    # TAB 1 — ניתוח בודד (CSV)
    # ======================================================
    with tab_single:
        st.markdown('<div class="section-header">העלאת דוח כספי (CSV)</div>', unsafe_allow_html=True)

        template_data = {"Parameter": REQUIRED_PARAMS, "Value": [1200, 150, 280, 620, 390, 200, 45]}
        csv_template = pd.DataFrame(template_data).to_csv(index=False).encode('utf-8-sig')

        col_up, col_dl = st.columns([2, 1])
        with col_dl:
            st.markdown("<br>", unsafe_allow_html=True)
            st.download_button("📥 הורד תבנית CSV", data=csv_template, file_name='bond_template.csv', mime='text/csv')
        with col_up:
            bond_name_single = st.text_input("שם האג\"ח (לתיוק)", value="אג\"ח לדוגמה", key="name_single")
            uploaded_file    = st.file_uploader("העלה קובץ CSV:", type=["csv"])

        if uploaded_file:
            data_dict, err = validate_and_parse_csv(uploaded_file)
            if err:
                st.error(err)
            else:
                nd_ebitda, curr_ratio, cov_ratio = compute_ratios(data_dict)
                analyzer    = AdvancedBondAnalyzer(ytm, duration, rating, nd_ebitda, curr_ratio, cov_ratio)
                final_score = analyzer.calculate_final_score()

                _render_results(analyzer, final_score, nd_ebitda, curr_ratio, cov_ratio, bond_name_single, ytm, duration, rating)


    # ======================================================
    # TAB 2 — השוואה בין אג"חות
    # ======================================================
    with tab_compare:
        
        st.markdown('<div class="section-header">הוסף עד 5 אג\"חות להשוואה</div>', unsafe_allow_html=True)
        st.info("לכל אג\"ח: הזן שם, נתוני שוק, והעלה קובץ CSV נפרד.")

        if 'comparison_bonds' not in st.session_state:
            st.session_state['comparison_bonds'] = []

        with st.expander("➕ הוסף אג\"ח להשוואה", expanded=True):
            c1, c2, c3 = st.columns(3)
            with c1:
                cmp_name     = st.text_input("שם האג\"ח",          key="cmp_name")
                cmp_ytm      = st.number_input("YTM (%)",           key="cmp_ytm",  value=5.0, step=0.1)
            with c2:
                cmp_duration = st.number_input("מח\"מ (שנים)",      key="cmp_dur",  value=3.0, step=0.1)
                cmp_rating   = st.selectbox("דירוג", ['AAA','AA','A','BBB','BB','B','CCC','CC','C','D','NR'], key="cmp_rating", index=3)
            with c3:
                cmp_file = st.file_uploader("קובץ CSV לאג\"ח זה:", type=["csv"], key="cmp_file")

            if st.button("✅ הוסף לרשימה"):
                if not cmp_name:
                    st.error("יש להזין שם לאג\"ח.")
                elif cmp_file is None:
                    st.error("יש להעלות קובץ CSV.")
                elif len(st.session_state['comparison_bonds']) >= 5:
                    st.error("ניתן להשוות עד 5 אג\"חות.")
                else:
                    data_dict, err = validate_and_parse_csv(cmp_file)
                    if err:
                        st.error(err)
                    else:
                        nd, cr, cov = compute_ratios(data_dict)
                        az    = AdvancedBondAnalyzer(cmp_ytm, cmp_duration, cmp_rating, nd, cr, cov)
                        score = az.calculate_final_score()
                        st.session_state['comparison_bonds'].append({
                            'name': cmp_name, 'score': score, 'analyzer': az,
                            'nd': nd, 'cr': cr, 'cov': cov,
                            'ytm': cmp_ytm, 'duration': cmp_duration, 'rating': cmp_rating
                        })
                        st.success(f"✅ {cmp_name} נוסף בהצלחה (ציון: {score})")

        if st.session_state['comparison_bonds']:
            bonds = st.session_state['comparison_bonds']

            tags_html = "".join(f'<span class="bond-tag">{b["name"]} — {b["score"]}</span>' for b in bonds)
            st.markdown(tags_html, unsafe_allow_html=True)
            st.markdown("<br>", unsafe_allow_html=True)

            st.plotly_chart(create_comparison_bar(bonds), use_container_width=True)

            tbl = pd.DataFrame([{
                "שם":             b['name'],
                "YTM (%)":        b['ytm'],
                "מח\"מ":           b['duration'],
                "דירוג":          b['rating'],
                "חוב/EBITDA":     round(b['nd'],  2),
                "יחס שוטף":       round(b['cr'],  2),
                "כיסוי ריבית":    round(b['cov'], 2),
                "ציון סיכון ⬆️":  b['score'],
            } for b in bonds])
            st.dataframe(tbl, use_container_width=True, hide_index=True)

            if st.button("🗑️ נקה רשימת השוואה"):
                st.session_state['comparison_bonds'] = []
                st.rerun()

    # ======================================================
    # TAB 3 — הזנה ידנית (ללא CSV)
    # ======================================================
    with tab_manual:
        st.markdown('<div class="section-header">הזן נתונים ידנית ללא קובץ CSV</div>', unsafe_allow_html=True)

        bond_name_manual = st.text_input("שם האג\"ח", value="אג\"ח ידני", key="name_manual")

        col_a, col_b = st.columns(2)
        with col_a:
            m_total_debt    = st.number_input("סך חוב (Total Debt)",          value=1200.0, step=10.0)
            m_cash          = st.number_input("מזומן (Cash)",                   value=150.0,  step=10.0)
            m_ebitda        = st.number_input("EBITDA",                         value=280.0,  step=10.0)
        with col_b:
            m_curr_assets   = st.number_input("נכסים שוטפים (Current Assets)", value=620.0,  step=10.0)
            m_curr_liab     = st.number_input("התחייבויות שוטפות",              value=390.0,  step=10.0)
            m_op_profit     = st.number_input("רווח תפעולי (Operating Profit)", value=200.0,  step=10.0)
            m_interest      = st.number_input("הוצאות ריבית (Interest Expense)",value=45.0,   step=1.0)

        if st.button("🔎 חשב ציון", type="primary"):
            errors = []
            if m_ebitda <= 0:        errors.append("EBITDA חייב להיות גדול מ-0.")
            if m_curr_liab <= 0:     errors.append("התחייבויות שוטפות חייבות להיות גדולות מ-0.")
            if m_interest <= 0:      errors.append("הוצאות ריבית חייבות להיות גדולות מ-0.")

            if errors:
                for e in errors: st.error(e)
            else:
                nd_ebitda  = (m_total_debt - m_cash) / m_ebitda
                curr_ratio = m_curr_assets / m_curr_liab
                cov_ratio  = m_op_profit   / m_interest

                analyzer    = AdvancedBondAnalyzer(ytm, duration, rating, nd_ebitda, curr_ratio, cov_ratio)
                final_score = analyzer.calculate_final_score()
                _render_results(analyzer, final_score, nd_ebitda, curr_ratio, cov_ratio, bond_name_manual, ytm, duration, rating)


if __name__ == "__main__":
    main()
