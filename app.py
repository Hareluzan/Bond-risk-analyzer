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
            {"פרמטר": "תשואה לפדיון (YTM)",        "ערך גולמי": f"{self.ytm}%", "ציון": self.score_ytm(), "משקל": f"{int(w['ytm']*100)}%"},
            {"פרמטר": "מח\"מ", "ערך גולמי": f"{self.duration} שנים", "ציון": self.score_duration(), "משקל": f"{int(w['duration']*100)}%"},
            {"פרמטר": "דירוג אשראי", "ערך גולמי": self.rating, "ציון": self.score_rating(), "משקל": f"{int(w['rating']*100)}%"},
            {"פרמטר": "חוב נטו / EBITDA", "ערך גולמי": f"{round(self.net_debt_ebitda,2)}x", "ציון": self.score_net_debt_ebitda(), "משקל": f"{int(w['nd_ebitda']*100)}%"},
            {"פרמטר": "יחס שוטף", "ערך גולמי": f"{round(self.current_ratio,2)}x", "ציון": self.score_current_ratio(), "משקל": f"{int(w['current']*100)}%"},
            {"פרמטר": "יחס כיסוי ריבית", "ערך גולמי": f"{round(self.coverage_ratio,2)}x", "ציון": self.score_coverage(), "משקל": f"{int(w['coverage']*100)}%"},
        ]
        return pd.DataFrame(rows)

# ============================================================
# שלב 2: בינה מלאכותית (Gemini)
# ============================================================
def setup_ai():
    try:
        api_key = st.secrets["GEMINI_API_KEY"]
        genai.configure(api_key=api_key)
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
    # שימוש בקידומת המלאה models/ כדי למנוע שגיאת 404
    model = genai.GenerativeModel('models/gemini-1.5-flash')
    prompt = """
    אנליסט פיננסי: חלץ מהטקסט את הנתונים הבאים בפורמט JSON בלבד.
    "Total_Debt", "Cash", "EBITDA", "Current_Assets", "Current_Liabilities", "Operating_Profit", "Interest_Expense".
    החזר רק את ה-JSON. אם נתון חסר, רשום 0.
    טקסט:
    """ + text[:30000]
    
    response = model.generate_content(prompt)
    clean_text = response.text.replace("```json", "").replace("```", "").strip()
    return json.loads(clean_text)

# ============================================================
# שלב 3: ויזואליזציה (אותו קוד גרפים)
# ============================================================
def create_gauge_chart(score):
    fig = go.Figure(go.Indicator(
        mode="gauge", value=score, domain={'x': [0, 1], 'y': [0, 1]},
        title={'text': "מדד סיכון משוקלל", 'font': {'size': 22}},
        gauge={'axis': {'range': [1, 5], 'tickvals': [1, 2, 3, 4, 5], 'ticktext': ['1','2','3','4','5']},
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
    st.subheader(f"תוצאות: {bond_name}")
    m1, m2, m3 = st.columns(3)
    m1.metric("חוב נטו / EBITDA", round(nd_ebitda, 2))
    m2.metric("יחס שוטף", round(curr_ratio, 2))
    m3.metric("יחס כיסוי ריבית", round(cov_ratio, 2))
    
    g1, g2 = st.columns(2)
    with g1: st.plotly_chart(create_gauge_chart(final_score), use_container_width=True)
    with g2: st.plotly_chart(create_radar_chart(analyzer), use_container_width=True)
    
    st.markdown("### פירוט ציונים")
    st.dataframe(analyzer.get_score_breakdown(), use_container_width=True, hide_index=True)

# ============================================================
# UI ראשי
# ============================================================
def main():
    st.set_page_config(page_title="מערכת Pro לניתוח אג\"ח", layout="wide")
    st.markdown("""<style>
    .stApp { direction: rtl; background: #0f1117; color: #e8eaf0; text-align: right; }
    div[data-testid="stSidebar"] { direction: rtl; text-align: right; }
    p, div, label, h1, h2, h3, span { text-align: right !important; }
    </style>""", unsafe_allow_html=True)

    with st.sidebar:
        st.header("נתוני שוק")
        ytm = st.number_input("תשואה לפדיון (%)", value=4.5, format="%.2f")
        duration = st.number_input("מח\"מ (שנים)", value=3.0, step=0.01, format="%.2f")
        rating = st.selectbox("דירוג אשראי", ['AAA','AA','A','BBB','BB','B','CCC','CC','C','D','NR'], index=3)
        st.divider()
        with st.expander("⚙️ משקלות"):
            st.session_state['w_ytm'] = st.slider("תשואה", 0, 50, 20) / 100
            st.session_state['w_rating'] = st.slider("דירוג", 0, 50, 15) / 100
            st.session_state['w_duration'] = st.slider("מח\"מ", 0, 50, 15) / 100
            st.session_state['w_nd_ebitda'] = st.slider("מינוף", 0, 50, 25) / 100
            st.session_state['w_current'] = st.slider("נזילות", 0, 50, 15) / 100
            st.session_state['w_coverage'] = st.slider("כיסוי", 0, 50, 10) / 100

    st.title("📊 מערכת Pro לניתוח סיכוני אג\"ח")
    ai_ready = setup_ai()
    
    tab_ai, tab_manual = st.tabs(["🤖 ניתוח PDF חכם (AI)", "✏️ הזנה ידנית"])

    with tab_ai:
        pdf_file = st.file_uploader("העלה דוח PDF", type=["pdf"])
        if pdf_file and ai_ready:
            with st.spinner("מחלץ נתונים..."):
                try:
                    text = extract_text_from_pdf(pdf_file)
                    ai_data = analyze_pdf_with_ai(text)
                    st.success("הנתונים חולצו!")
                    
                    nd = (ai_data.get("Total_Debt", 0) - ai_data.get("Cash", 0)) / ai_data.get("EBITDA", 1) if ai_data.get("EBITDA", 0) > 0 else 99
                    cr = ai_data.get("Current_Assets", 0) / ai_data.get("Current_Liabilities", 1) if ai_data.get("Current_Liabilities", 0) > 0 else 0
                    cov = ai_data.get("Operating_Profit", 0) / ai_data.get("Interest_Expense", 1) if ai_data.get("Interest_Expense", 0) > 0 else 99
                    
                    analyzer = AdvancedBondAnalyzer(ytm, duration, rating, nd, cr, cov)
                    _render_results(analyzer, analyzer.calculate_final_score(), nd, cr, cov, "ניתוח PDF")
                except Exception as e:
                    st.error(f"שגיאה: {e}")

    with tab_manual:
        c1, c2 = st.columns(2)
        with c1:
            m_debt = st.number_input("סך חוב", value=1000.0)
            m_cash = st.number_input("מזומן", value=200.0)
            m_ebitda = st.number_input("EBITDA", value=300.0)
        with c2:
            m_assets = st.number_input("נכסים שוטפים", value=500.0)
            m_liab = st.number_input("התחייבויות שוטפות", value=400.0)
            m_op = st.number_input("רווח תפעולי", value=150.0)
            m_int = st.number_input("הוצאות ריבית", value=50.0)
        
        if st.button("חשב"):
            nd = (m_debt - m_cash) / m_ebitda if m_ebitda > 0 else 99
            cr = m_assets / m_liab if m_liab > 0 else 0
            cov = m_op / m_int if m_int > 0 else 99
            analyzer = AdvancedBondAnalyzer(ytm, duration, rating, nd, cr, cov)
            _render_results(analyzer, analyzer.calculate_final_score(), nd, cr, cov, "הזנה ידנית")

if __name__ == "__main__":
    main()
