import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import json
import pdfplumber
from openai import OpenAI

# ============================================================
# שלב 1: מנוע האנליזה הפיננסית
# ============================================================
class UniversalBondAnalyzer:
    def __init__(self, ytm, duration, rating, net_debt_ebitda, current_ratio, coverage_ratio):
        self.ytm, self.duration, self.rating = ytm, duration, rating.upper()
        self.nd_ebitda, self.current_ratio, self.coverage_ratio = net_debt_ebitda, current_ratio, coverage_ratio

    def calculate_final_score(self):
        w = {'ytm': 0.20, 'rating': 0.15, 'duration': 0.15, 'nd_ebitda': 0.25, 'current': 0.15, 'coverage': 0.10}
        
        def get_score(val, steps, reverse=False):
            for i, s in enumerate(steps):
                if (val <= s if not reverse else val >= s): return i + 1
            return 5

        s_ytm = get_score(self.ytm, [3, 5, 8, 12])
        s_dur = get_score(self.duration, [2, 4, 7, 10])
        s_rat = {'AAA':1,'AA':1,'A':2,'BBB':3,'BB':4,'B':4,'CCC':5}.get(self.rating, 5)
        s_nd  = get_score(self.nd_ebitda, [2, 3.5, 5, 7])
        s_curr = get_score(self.current_ratio, [2, 1.5, 1, 0.8], reverse=True)
        s_cov = get_score(self.coverage_ratio, [5, 3, 1.5, 1], reverse=True)
        
        return round(sum([s_ytm*w['ytm'], s_rat*w['rating'], s_dur*w['duration'], s_nd*w['nd_ebitda'], s_curr*w['current'], s_cov*w['coverage']]), 2)

# ============================================================
# שלב 2: חילוץ טקסט חכם (Smart Scanning)
# ============================================================
def smart_extract_text(pdf_file):
    extracted_text = ""
    keywords = ["מאזן", "מאוחד", "רווח והפסד", "תזרים מזומנים", "התחייבויות", "נכסים שוטפים"]
    with pdfplumber.open(pdf_file) as pdf:
        # סריקה של דפים רלוונטיים בלבד למניעת עומס
        for page in pdf.pages:
            page_text = page.extract_text() or ""
            # אם העמוד מכיל מילות מפתח של דוח כספי, ניקח אותו
            if any(key in page_text for key in keywords):
                extracted_text += page_text + "\n"
            if len(extracted_text) > 400000: break # הגנה מפני קבצי ענק
    return extracted_text

def analyze_report_with_ai(text):
    client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
    prompt = """
    אתה אנליסט פיננסי בכיר. חלץ נתונים פיננסיים מאוחדים (Consolidated) לתאריך הדיווח האחרון בלבד.
    דגשים חשובים:
    1. Total_Debt: סכום אשראי בנקאי + חלויות שוטפות + אג"ח + הלוואות לזמן ארוך + חכירה.
    2. EBITDA: רווח תפעולי + פחת והפחתות. אם אין פחת, הערך Operating_Profit * 1.1. לעולם אל תחזיר 0.
    3. Current_Assets: סך נכסים שוטפים (ודא שכללת מלאי ולקוחות).
    4. Interest_Expense: הוצאות מימון נטו (חיובי).

    החזר JSON בלבד:
    {"Company_Name": "", "Total_Debt": 0, "Cash": 0, "EBITDA": 0, "Current_Assets": 0, "Current_Liabilities": 0, "Operating_Profit": 0, "Interest_Expense": 0}
    
    טקסט:
    """ + text
    
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "system", "content": "Financial Analysis Expert"}, {"role": "user", "content": prompt}],
        response_format={ "type": "json_object" }
    )
    return json.loads(response.choices[0].message.content)

# ============================================================
# שלב 3: ממשק המשתמש (UI)
# ============================================================
def main():
    st.set_page_config(page_title="Universal Bond Analyzer", layout="wide")
    st.markdown("<style>.stApp { direction: rtl; text-align: right; background: #0f1117; color: white; }</style>", unsafe_allow_html=True)

    with st.sidebar:
        st.header("נתוני שוק")
        ytm = st.number_input("תשואה (%)", value=4.5, format="%.2f")
        duration = st.number_input("מח\"מ (שנים)", value=3.0, step=0.01, format="%.2f")
        rating = st.selectbox("דירוג", ['AAA','AA','A','BBB','BB','B','CCC','NR'], index=3)

    st.title("📊 מנתח אג\"ח אוניברסלי (AI)")
    
    pdf_file = st.file_uploader("העלה דוח כספי (PDF)", type=["pdf"])
    if pdf_file:
        with st.spinner("סורק דוח ומאתר עמודי מאזן..."):
            try:
                raw_text = smart_extract_text(pdf_file)
                data = analyze_report_with_ai(raw_text)
                
                st.success(f"ניתוח הושלם עבור: {data.get('Company_Name', 'חברה לא מזוהה')}")
                with st.expander("נתונים גולמיים מהדוח"): st.json(data)
                
                # חישובי יחסים
                ebitda = data.get("EBITDA", 1) or 1
                nd_ebitda = (data.get("Total_Debt", 0) - data.get("Cash", 0)) / ebitda
                curr_ratio = data.get("Current_Assets", 0) / (data.get("Current_Liabilities", 1) or 1)
                cov_ratio = data.get("Operating_Profit", 0) / (data.get("Interest_Expense", 1) or 1)
                
                analyzer = UniversalBondAnalyzer(ytm, duration, rating, nd_ebitda, curr_ratio, cov_ratio)
                final_score = analyzer.calculate_final_score()
                
                # תצוגת תוצאות
                col1, col2, col3 = st.columns(3)
                col1.metric("חוב נטו / EBITDA", round(nd_ebitda, 2))
                col2.metric("יחס שוטף", round(curr_ratio, 2))
                col3.metric("יחס כיסוי ריבית", round(cov_ratio, 2))
                
                st.divider()
                st.subheader(f"ציון סיכון משוקלל: {final_score}")
                st.progress(min(final_score / 5.0, 1.0))
                
            except Exception as e:
                st.error(f"שגיאה: {e}")

if __name__ == "__main__":
    main()
