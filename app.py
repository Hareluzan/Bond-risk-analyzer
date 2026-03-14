import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import io
import json
import google.generativeai as genai
from pypdf import PdfReader

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
        ratings_map = {'AAA': 1, 'AA': 1, 'A': 2, 'BBB': 3, 'BB': 4, 'B': 4, 'CCC': 5, 'CC': 5, 'C': 5, 'D': 5, 'NR': 5}
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
        final_score = (self.score_ytm() * w['ytm'] + self.score_rating() * w['rating'] + 
                       self.score_duration() * w['duration'] + self.score_net_debt_ebitda() * w['nd_ebitda'] + 
                       self.score_current_ratio() * w['current'] + self.score_coverage() * w['coverage'])
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
# שלב 2: בינה מלאכותית (Gemini) לחילוץ נתונים
# ============================================================
def setup_ai():
    try:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        return True
    except Exception:
        return False

def extract_text_from_pdf(pdf_file):
    reader = PdfReader(pdf_file)
    text = ""
    for page in reader.pages:
        text += page.extract_text() + "\n"
    return text

def analyze_pdf_with_ai(text):
    model = genai.GenerativeModel('gemini-1.5-flash')
    prompt = """
    אתה אנליסט פיננסי מומחה. קרא את הטקסט הבא (שנלקח מדוח כספי) וחלץ ממנו את 7 הנתונים הבאים במספרים בלבד.
    אם לא מצאת נתון מדויק, עשה את ההערכה המושכלת ביותר על בסיס נהלי חשבונאות, או החזר 0.
    החזר אך ורק פורמט JSON תקין (ללא טקסט מקדים, ללא הסברים, ללא סימני markdown).
    השתמש בדיוק במפתחות האלה באנגלית:
    "Total_Debt", "Cash", "EBITDA", "Current_Assets", "Current_Liabilities", "Operating_Profit", "Interest_Expense".
    
    הטקסט:
    """ + text[:35000] # מגביל את כמות הטקסט כדי למנוע עומס
    
    response = model.generate_content(prompt)
    
    # ניקוי התשובה מסימני קוד כדי לקבל JSON נקי
    clean_text = response.text.replace("```json", "").replace("```", "").strip()
    return json.loads(clean_text)

# ============================================================
# פונקציות תצוגה (גרפים וחישובים קודמים)
# ============================================================
def create_gauge_chart(score):
    fig = go.Figure(go.Indicator(
        mode="gauge", value=score, domain={'x': [0, 1], 'y': [0, 1]},
        title={'text': "מדד סיכון משוקלל", 'font': {'size': 22}},
        gauge={'axis': {'range': [1, 5], 'tickwidth': 1, 'tickcolor': "#aaa", 'tickvals': [1, 2, 3, 4, 5], 'ticktext': ['1<br><sub>בטוח</sub>', '2', '3', '4', '5<br><sub>מסוכן</sub>']},
               'bar': {'color': "rgba(0,0,0,0)"}, 'bgcolor': "rgba(0,0,0,0)", 'borderwidth': 2, 'bordercolor': "gray",
               'steps': [{'range': [1, 2.5], 'color': "#00cc96"}, {'range': [2.5, 3.8], 'color': "#FFA15A"}, {'range': [3.8, 5], 'color': "#EF553B"}]}
    ))
    fig.add_annotation(x=0.5, y=0.28, text=f"<b>{score}</b>", showarrow=False, font=dict(size=52, color="white"))
    fig.update_layout(height=350, margin=dict(l=20, r=20, t=60, b=20), paper_bgcolor="rgba(0,0,0,0)")
    return fig

def create_radar_chart(analyzer):
    categories = ['תשואה', 'מח"מ', 'דירוג', 'מינוף\n(Net Debt/EBITDA)', 'נזילות\n(יחס שוטף)', 'כיסוי ריבית']
    values = [analyzer.score_ytm(), analyzer.score_duration(), analyzer.score_rating(), analyzer.score_net_debt_ebitda(), analyzer.score_current_ratio(), analyzer.score_coverage()]
    values_closed = values + [values[0]]; cats_closed = categories + [categories[0]]
    fig = go.Figure(data=go.Scatterpolar(r=values_closed, theta=cats_closed, fill='toself', fillcolor='rgba(99, 110, 250, 0.4)', line=dict(color='#636EFA', width=2), marker=dict(size=7, color='#636EFA')))
    fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 5], tickfont=dict(size=10)), angularaxis=dict(tickfont=dict(size=13))), showlegend=False, height=420, margin=dict(l=50, r=50, t=40, b=40), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
    return fig

def compute_ratios(data_dict):
    net_debt_ebitda = (data_dict["Total_Debt"] - data_dict["Cash"]) / data_dict["EBITDA"] if data_dict.get("EBITDA", 0) > 0 else 99
    current_ratio = data_dict["Current_Assets"] / data_dict["Current_Liabilities"] if data_dict.get("Current_Liabilities", 0) > 0 else 0
    coverage_ratio = data_dict["Operating_Profit"] / data_dict["Interest_Expense"] if data_dict.get("Interest_Expense", 0) > 0 else 99
    return net_debt_ebitda, current_ratio, coverage_ratio

def _render_results(analyzer, final_score, nd_ebitda, curr_ratio, cov_ratio, bond_name):
    st.divider()
    st.subheader(f"תוצאות הניתוח: {bond_name}")
    m1, m2, m3 = st.columns(3)
    m1.metric("חוב נטו / EBITDA", round(nd_ebitda, 2), "מעל 4 = מסוכן" if nd_ebitda > 4 else "✅ תקין", delta_color="inverse")
    m2.metric("יחס שוטף (נזילות)", round(curr_ratio, 2), "מתחת ל-1 = סכנה" if curr_ratio < 1 else "✅ תקין")
    m3.metric("יחס כיסוי ריבית", round(cov_ratio, 2), "מתחת ל-1.5 = חלש" if cov_ratio < 1.5 else "✅ תקין")
    st.markdown("<br>", unsafe_allow_html=True)
    g1, g2 = st.columns(2)
    with g1:
        st.markdown("### ציון סיכון סופי")
        st.plotly_chart(create_gauge_chart(final_score), use_container_width=True)
    with g2:
        st.markdown("### פרופיל סיכון רב-ממדי")
        st.plotly_chart(create_radar_chart(analyzer), use_container_width=True)

# ============================================================
# UI ראשי
# ============================================================
def main():
    st.set_page_config(page_title="מערכת Pro לניתוח אג\"ח", layout="wide", page_icon="📊")
    st.markdown("""<style>
    @import url('https://fonts.googleapis.com/css2?family=Heebo:wght@300;400;700;900&display=swap');
    html, body, [class*="css"] { font-family: 'Heebo', sans-serif !important; }
    .stApp { direction: rtl; background: #0f1117; color: #e8eaf0; }
    p, div, input, label, h1, h2, h3, h4, h5, h6, span { text-align: right !important; }
    div[data-testid="stSidebar"] { direction: rtl; background: #161b27; border-left: 1px solid #2a3045; }
    div[data-testid="metric-container"] { background: #1c2233; border: 1px solid #2a3045; border-radius: 12px; padding: 16px; box-shadow: 0 4px 20px rgba(0,0,0,0.3); }
    .stAlert > div { direction: rtl; text-align: right; border-radius: 10px; }
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] { background: #1c2233; border-radius: 8px 8px 0 0; border: 1px solid #2a3045; color: #aab; font-weight: 600; padding: 8px 20px; }
    .stTabs [aria-selected="true"] { background: #2563eb !important; color: white !important; border-color: #2563eb !important; }
    </style>""", unsafe_allow_html=True)

    with st.sidebar:
        st.title("נתוני שוק")
        ytm = st.number_input("תשואה לפדיון (%)", value=4.5, step=0.1)
        duration = st.number_input("מח\"מ (שנים)", value=3.0, step=0.1)
        rating = st.selectbox("דירוג אשראי", ['AAA','AA','A','BBB','BB','B','CCC','CC','C','D','NR'], index=3)
        st.divider()
        with st.expander("⚙️ כוונון משקלות"):
            st.session_state['w_ytm'] = st.slider("תשואה לפדיון", 0, 50, 20) / 100
            st.session_state['w_rating'] = st.slider("דירוג אשראי", 0, 50, 15) / 100
            st.session_state['w_duration'] = st.slider("מח\"מ", 0, 50, 15) / 100
            st.session_state['w_nd_ebitda'] = st.slider("חוב נטו / EBITDA", 0, 50, 25) / 100
            st.session_state['w_current'] = st.slider("יחס שוטף", 0, 50, 15) / 100
            st.session_state['w_coverage'] = st.slider("כיסוי ריבית", 0, 50, 10) / 100

    st.markdown("# 📊 מערכת Pro לניתוח סיכוני אג\"ח")
    
    # בדיקת חיבור ל-API
    ai_ready = setup_ai()
    if not ai_ready:
        st.warning("⚠️ מערכת ה-AI כרגע מנותקת. ודא שהכנסת מפתח API בהגדרות Streamlit (Secrets).")

    tab_ai, tab_manual = st.tabs(["🤖 ניתוח חכם מדוח PDF (AI)", "✏️ הזנה ידנית"])

    with tab_ai:
        st.markdown('<h3>העלה דוח כספי (PDF) לחילוץ אוטומטי של נתונים</h3>', unsafe_allow_html=True)
        pdf_file = st.file_uploader("בחר קובץ PDF", type=["pdf"])
        
        if pdf_file and ai_ready:
            with st.spinner("🧠 קורא את הדוח ומחלץ נתונים בעזרת בינה מלאכותית... (זה עשוי לקחת חצי דקה)"):
                try:
                    text = extract_text_from_pdf(pdf_file)
                    ai_data = analyze_pdf_with_ai(text)
                    
                    st.success("✅ הנתונים חולצו בהצלחה מהדוח!")
                    st.json(ai_data) # מציג את המספרים שחולצו
                    
                    nd, cr, cov = compute_ratios(ai_data)
                    analyzer = AdvancedBondAnalyzer(ytm, duration, rating, nd, cr, cov)
                    final_score = analyzer.calculate_final_score()
                    
                    _render_results(analyzer, final_score, nd, cr, cov, "אג\"ח מנותח (PDF)")
                except Exception as e:
                    st.error(f"❌ שגיאה בחילוץ הנתונים מה-PDF. נסה דוח אחר או הזן ידנית. ({e})")

    with tab_manual:
        st.markdown('<h3>הזן נתונים ידנית</h3>', unsafe_allow_html=True)
        col_a, col_b = st.columns(2)
        with col_a:
            m_total_debt = st.number_input("סך חוב", value=1200.0)
            m_cash = st.number_input("מזומן", value=150.0)
            m_ebitda = st.number_input("EBITDA", value=280.0)
        with col_b:
            m_curr_assets = st.number_input("נכסים שוטפים", value=620.0)
            m_curr_liab = st.number_input("התחייבויות שוטפות", value=390.0)
            m_op_profit = st.number_input("רווח תפעולי", value=200.0)
            m_interest = st.number_input("הוצאות ריבית", value=45.0)

        if st.button("🔎 חשב ציון"):
            nd = (m_total_debt - m_cash) / m_ebitda if m_ebitda > 0 else 99
            cr = m_curr_assets / m_curr_liab if m_curr_liab > 0 else 0
            cov = m_op_profit / m_interest if m_interest > 0 else 99
            analyzer = AdvancedBondAnalyzer(ytm, duration, rating, nd, cr, cov)
            final_score = analyzer.calculate_final_score()
            _render_results(analyzer, final_score, nd, cr, cov, "אג\"ח ידני")

if __name__ == "__main__":
    main()
