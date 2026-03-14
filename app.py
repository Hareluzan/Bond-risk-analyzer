import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import io
import json
from openai import OpenAI
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
            {"פרמטר": "תשואה לפדיון (YTM)", "ערך גולמי": f"{self.ytm}%", "ציון": self.score_ytm(), "משקל": f"{int(w['ytm']*100)}%"},
            {"פרמטר": "מח\"מ", "ערך גולמי": f"{self.duration} שנים", "ציון": self.score_duration(), "משקל": f"{int(w['duration']*100)}%"},
            {"פרמטר": "דירוג אשראי", "ערך גולמי": self.rating, "ציון": self.score_rating(), "משקל": f"{int(w['rating']*100)}%"},
            {"פרמטר": "חוב נטו / EBITDA", "ערך גולמי": f"{round(self.net_debt_ebitda,2)}x", "ציון": self.score_net_debt_ebitda(), "משקל": f"{int(w['nd_ebitda']*100)}%"},
            {"פרמטר": "יחס שוטף", "ערך גולמי": f"{round(self.current_ratio,2)}x", "ציון": self.score_current_ratio(), "משקל": f"{int(w['current']*100)}%"},
            {"פרמטר": "יחס כיסוי ריבית", "ערך גולמי": f"{round(self.coverage_ratio,2)}x", "ציון": self.score_coverage(), "משקל": f"{int(w['coverage']*100)}%"},
        ]
        return pd.DataFrame(rows)

# ============================================================
# שלב 2: פונקציות ה-AI המקצועיות (OpenAI)
# ============================================================
def extract_text_from_pdf(pdf_file):
    reader = PdfReader(pdf_file)
    text = ""
    for page in reader.pages:
        text += page.extract_text() + "\n"
    return text

def analyze_pdf_with_openai(text):
    client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
    
    prompt = """
    אתה אנליסט אשראי מומחה. עליך לקרוא את הטקסט מתוך הדוח הכספי (בעברית או אנגלית), לחלץ ולחשב את הנתונים הפיננסיים הבאים. 
    החזר אך ורק פורמט JSON תקין עם המפתחות המדויקים באנגלית.
    
    חוקי החישוב:
    1. "Total_Debt" (סך חוב): סכום של אשראי בנקאי לזמן קצר + חלויות שוטפות + אג"ח לזמן ארוך + הלוואות לזמן ארוך + התחייבויות חכירה. אין לכלול ספקים וזכאים.
    2. "Cash" (מזומנים ונזילות): מזומן ושווי מזומן + פיקדונות + ניירות ערך סחירים/השקעות לזמן קצר.
    3. "EBITDA": אם לא מפורש, קח "רווח תפעולי" (Operating Profit) והוסף לו "פחת והפחתות" (Depreciation & Amortization) מדוח תזרים המזומנים.
    4. "Current_Assets": סך כל הנכסים השוטפים.
    5. "Current_Liabilities": סך כל ההתחייבויות השוטפות.
    6. "Operating_Profit": רווח תפעולי לפני הוצאות מימון ומסים.
    7. "Interest_Expense": הוצאות מימון נטו (יש להחזיר תמיד כמספר חיובי בערך מוחלט).

    החזר JSON במבנה הזה בלבד (אם נתון חסר לחלוטין, שים 0):
    {"Total_Debt": 0, "Cash": 0, "EBITDA": 0, "Current_Assets": 0, "Current_Liabilities": 0, "Operating_Profit": 0, "Interest_Expense": 0}
    
    טקסט הדוח:
    """ + text[-300000:] # קורא את ה-300,000 התווים האחרונים של הדוח (היכן שהדוחות הכספיים נמצאים)

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "system", "content": "You are a senior financial analyst and a JSON output machine."},
                  {"role": "user", "content": prompt}],
        response_format={ "type": "json_object" }
    )
    return json.loads(response.choices[0].message.content)

# ============================================================
# שלב 3: ויזואליזציה 
# ============================================================
def create_gauge_chart(score):
    fig = go.Figure(go.Indicator(
        mode="gauge", value=score, domain={'x': [0, 1], 'y': [0, 1]},
        title={'text': "מדד סיכון משוקלל", 'font': {'size': 22}},
        gauge={'axis': {'range': [1, 5], 'tickvals': [1, 2, 3, 4, 5]},
               'bar': {'color': "rgba(0,0,0,0)"}, 'bgcolor': "rgba(0,0,0,0)", 'borderwidth': 2,
               'steps': [{'range': [1, 2.5], 'color': "#00cc96"}, {'range': [2.5, 3.8], 'color': "#FFA15A"}, {'range': [3.8, 5], 'color': "#EF553B"}]}
    ))
    fig.add_annotation(x=0.5, y=0.3, text=f"<b>{score}</b>", showarrow=False, font=dict(size=45, color="white"))
    fig.update_layout(height=350, margin=dict(l=20, r=20, t=50, b=20), paper_bgcolor="rgba(0,0,0,0)")
    return fig

def create_radar_chart(analyzer):
    categories = ['תשואה', 'מח"מ', 'דירוג', 'מינוף', 'נזילות', 'כיסוי']
    values = [analyzer.score_ytm(), analyzer.score_duration(), analyzer.score_rating(), analyzer.score_net_debt_ebitda(), analyzer.score_current_ratio(), analyzer.score_coverage()]
    values += [values[0]]; categories += [categories[0]]
    fig = go.Figure(data=go.Scatterpolar(r=values, theta=categories, fill='toself', fillcolor='rgba(99, 110, 250, 0.4)', line=dict(color='#636EFA')))
    fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 5])), showlegend=False, height=400, paper_bgcolor="rgba(0,0,0,0)")
    return fig

def _render_results(analyzer, final_score, nd_ebitda, curr_ratio, cov_ratio, bond_name):
    st.divider()
    st.subheader(f"תוצאות הניתוח: {bond_name}")
    
    m1, m2, m3 = st.columns(3)
    m1.metric("חוב נטו / EBITDA", round(nd_ebitda, 2), "מעל 4 = מסוכן" if nd_ebitda > 4 else "תקין", delta_color="inverse")
    m2.metric("יחס שוטף", round(curr_ratio, 2), "מתחת ל-1 = סכנה" if curr_ratio < 1 else "תקין")
    m3.metric("יחס כיסוי ריבית", round(cov_ratio, 2), "מתחת ל-1.5 = חלש" if cov_ratio < 1.5 else "תקין")
    
    g1, g2 = st.columns(2)
    with g1: st.plotly_chart(create_gauge_chart(final_score), use_container_width=True)
    with g2: st.plotly_chart(create_radar_chart(analyzer), use_container_width=True)
    
    st.markdown("### 🗂️ פירוט ציונים ומשקלות")
    st.dataframe(analyzer.get_score_breakdown(), use_container_width=True, hide_index=True)

# ============================================================
# שלב 4: ממשק המשתמש (UI)
# ============================================================
def main():
    st.set_page_config(page_title="מערכת Pro לניתוח אג\"ח", layout="wide")
    st.markdown("""<style>
    .stApp { direction: rtl; background: #0f1117; color: #e8eaf0; text-align: right; font-family: sans-serif; }
    div[data-testid="stSidebar"] { direction: rtl; text-align: right; background: #161b27; }
    p, div, label, h1, h2, h3, span { text-align: right !important; }
    .stTabs [data-baseweb="tab"] { font-size: 1.1rem; }
    </style>""", unsafe_allow_html=True)

    if "OPENAI_API_KEY" not in st.secrets:
        st.error("⚠️ מפתח OpenAI חסר. הוסף ל-Secrets את: OPENAI_API_KEY")
        st.stop()

    with st.sidebar:
        st.header("1. נתוני שוק חברתיים")
        ytm = st.number_input("תשואה לפדיון (%)", value=4.5, format="%.2f")
        duration = st.number_input("מח\"מ (שנים)", value=3.0, step=0.01, format="%.2f")
        rating = st.selectbox("דירוג אשראי", ['AAA','AA','A','BBB','BB','B','CCC','CC','C','D','NR'], index=3)
        st.divider()
        with st.expander("⚙️ כוונון משקלות הניתוח"):
            st.session_state['w_ytm'] = st.slider("תשואה", 0, 50, 20) / 100
            st.session_state['w_rating'] = st.slider("דירוג", 0, 50, 15) / 100
            st.session_state['w_duration'] = st.slider("מח\"מ", 0, 50, 15) / 100
            st.session_state['w_nd_ebitda'] = st.slider("מינוף (Net Debt/EBITDA)", 0, 50, 25) / 100
            st.session_state['w_current'] = st.slider("נזילות (יחס שוטף)", 0, 50, 15) / 100
            st.session_state['w_coverage'] = st.slider("כיסוי ריבית", 0, 50, 10) / 100

    st.title("📊 מערכת Pro לניתוח אג\"ח (AI Powered)")
    st.write("מערכת משולבת לחילוץ נתוני דוחות כספיים בעזרת בינה מלאכותית (GPT) וניתוח סיכונים פונדמנטלי.")
    
    tab_ai, tab_manual = st.tabs(["🤖 העלאת דוח PDF", "✏️ הזנת נתונים ידנית"])

    with tab_ai:
        pdf_file = st.file_uploader("העלה את הדוח הכספי של החברה לכאן (קובץ PDF)", type=["pdf"])
        if pdf_file:
            with st.spinner("🧠 ה-AI קורא את הדוח ומחלץ נתונים פיננסיים (זה לוקח כ-15-30 שניות)..."):
                try:
                    text = extract_text_from_pdf(pdf_file)
                    ai_data = analyze_pdf_with_openai(text)
                    st.success("✅ הנתונים חולצו בהצלחה מתוך הדוח!")
                    
                    with st.expander("לחץ כאן כדי לראות את המספרים הגולמיים שה-AI מצא"):
                        st.json(ai_data)
                    
                    # חישוב מתמטי סופי מתוך הנתונים שחולצו
                    total_debt = ai_data.get("Total_Debt", 0)
                    cash = ai_data.get("Cash", 0)
                    ebitda = ai_data.get("EBITDA", 1) # מניעת חלוקה באפס
                    curr_assets = ai_data.get("Current_Assets", 0)
                    curr_liab = ai_data.get("Current_Liabilities", 1)
                    op_profit = ai_data.get("Operating_Profit", 0)
                    int_exp = ai_data.get("Interest_Expense", 1)
                    
                    nd = (total_debt - cash) / ebitda if ebitda > 0 else 99
                    cr = curr_assets / curr_liab if curr_liab > 0 else 0
                    cov = op_profit / int_exp if int_exp > 0 else 99
                    
                    analyzer = AdvancedBondAnalyzer(ytm, duration, rating, nd, cr, cov)
                    _render_results(analyzer, analyzer.calculate_final_score(), nd, cr, cov, "אג\"ח מנותח (PDF)")
                    
                except Exception as e:
                    error_msg = str(e)
                    if "insufficient_quota" in error_msg or "429" in error_msg:
                        st.error("❌ שגיאת תקציב ב-OpenAI: הקרדיט במפתח ה-API שלך נגמר או שלא הוזן אמצעי תשלום. יש להטעין מינימום 5$ באתר OpenAI כדי שהניתוח יעבוד.")
                    else:
                        st.error(f"❌ שגיאה בניתוח: {error_msg}")

    with tab_manual:
        st.write("במידה ואין ברשותך קובץ PDF, תוכל להזין את המספרים מתוך המאזן ודוח רווח והפסד באופן ידני:")
        c1, c2 = st.columns(2)
        with c1:
            m_debt = st.number_input("סך חוב ברוטו", value=1000.0)
            m_cash = st.number_input("מזומן ושווי מזומן", value=200.0)
            m_ebitda = st.number_input("EBITDA (רווח תפעולי תזרימי)", value=300.0)
        with c2:
            m_assets = st.number_input("נכסים שוטפים", value=500.0)
            m_liab = st.number_input("התחייבויות שוטפות", value=400.0)
            m_op = st.number_input("רווח תפעולי", value=150.0)
            m_int = st.number_input("הוצאות מימון", value=50.0)
        
        if st.button("🔎 חשב ציון סופי", type="primary"):
            nd = (m_debt - m_cash) / m_ebitda if m_ebitda > 0 else 99
            cr = m_assets / m_liab if m_liab > 0 else 0
            cov = m_op / m_int if m_int > 0 else 99
            analyzer = AdvancedBondAnalyzer(ytm, duration, rating, nd, cr, cov)
            _render_results(analyzer, analyzer.calculate_final_score(), nd, cr, cov, "הזנה ידנית")

if __name__ == "__main__":
    main()
