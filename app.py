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

    def calculate_final_score(self):
        w = {'ytm': 0.20, 'rating': 0.15, 'duration': 0.15, 'nd_ebitda': 0.25, 'current': 0.15, 'coverage': 0.10}
        final_score = (self.score_ytm() * w['ytm'] + self.score_rating() * w['rating'] + 
                       self.score_duration() * w['duration'] + self.score_net_debt_ebitda() * w['nd_ebitda'] + 
                       self.score_current_ratio() * w['current'] + self.score_coverage() * w['coverage'])
        return round(final_score, 2)

# ============================================================
# שלב 2: פונקציות AI (OpenAI)
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
    אתה אנליסט פיננסי בכיר. עליך לחלץ מהטקסט של הדוח הכספי את הנתונים הבאים ולהחזיר אך ורק JSON תקין.
    המפתחות הנדרשים: "Total_Debt", "Cash", "EBITDA", "Current_Assets", "Current_Liabilities", "Operating_Profit", "Interest_Expense".
    דגשים: מספרים בלבד. אם נתון חסר, רשום 0.
    טקסט הדוח:
    """ + text[:25000]

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "system", "content": "You are a professional financial data extractor."},
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

# ============================================================
# שלב 4: UI ראשי
# ============================================================
def main():
    st.set_page_config(page_title="Pro Bond Analyzer", layout="wide")
    st.markdown("""<style>
    .stApp { direction: rtl; background: #0f1117; color: #e8eaf0; text-align: right; }
    div[data-testid="stSidebar"] { direction: rtl; text-align: right; }
    p, div, label, h1, h2, h3, span { text-align: right !important; }
    </style>""", unsafe_allow_html=True)

    # וידוא קיום מפתח ב-Secrets
    if "OPENAI_API_KEY" not in st.secrets:
        st.error("⚠️ מפתח OpenAI לא נמצא ב-Secrets של Streamlit. אנא הוסף אותו תחת השם OPENAI_API_KEY.")
        st.stop()

    with st.sidebar:
        st.header("נתוני שוק")
        ytm = st.number_input("תשואה לפדיון (%)", value=4.5, format="%.2f")
        duration = st.number_input("מח\"מ (שנים)", value=3.0, step=0.01, format="%.2f")
        rating = st.selectbox("דירוג אשראי", ['AAA','AA','A','BBB','BB','B','CCC','CC','C','D','NR'], index=3)

    st.title("📊 מערכת Pro לניתוח אג\"ח (GPT-4o)")
    
    tab_ai, tab_manual = st.tabs(["🤖 ניתוח PDF חכם (AI)", "✏️ הזנה ידנית"])

    with tab_ai:
        pdf_file = st.file_uploader("העלה דוח PDF של החברה", type=["pdf"])
        if pdf_file:
            with st.spinner("🧠 ה-AI מנתח את הדוח הכספי..."):
                try:
                    text = extract_text_from_pdf(pdf_file)
                    ai_data = analyze_pdf_with_openai(text)
                    st.success("הנתונים חולצו בהצלחה!")
                    
                    nd = (ai_data["Total_Debt"] - ai_data["Cash"]) / ai_data["EBITDA"] if ai_data.get("EBITDA", 0) > 0 else 5
                    cr = ai_data["Current_Assets"] / ai_data["Current_Liabilities"] if ai_data.get("Current_Liabilities", 0) > 0 else 0
                    cov = ai_data["Operating_Profit"] / ai_data["Interest_Expense"] if ai_data.get("Interest_Expense", 0) > 0 else 0
                    
                    analyzer = AdvancedBondAnalyzer(ytm, duration, rating, nd, cr, cov)
                    score = analyzer.calculate_final_score()
                    
                    # הצגת תוצאות
                    m1, m2, m3 = st.columns(3)
                    m1.metric("חוב נטו / EBITDA", round(nd, 2))
                    m2.metric("יחס שוטף", round(cr, 2))
                    m3.metric("יחס כיסוי ריבית", round(cov, 2))
                    
                    g1, g2 = st.columns(2)
                    with g1: st.plotly_chart(create_gauge_chart(score), use_container_width=True)
                    with g2: st.plotly_chart(create_radar_chart(analyzer), use_container_width=True)
                except Exception as e:
                    st.error(f"שגיאה בניתוח: {e}")

    with tab_manual:
        st.info("כאן ניתן להזין נתונים ידנית ללא צורך ב-AI.")
        # ... (שדות הזנה ידנית כפי שהיו קודם)

if __name__ == "__main__":
    main()
