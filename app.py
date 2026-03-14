import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# --- שלב 1: מנוע האנליזה הפיננסית ---
class AdvancedBondAnalyzer:
    def __init__(self, ytm, duration, rating, net_debt_ebitda, current_ratio, coverage_ratio):
        self.ytm = ytm
        self.duration = duration
        self.rating = rating.upper()
        self.net_debt_ebitda = net_debt_ebitda
        self.current_ratio = current_ratio
        self.coverage_ratio = coverage_ratio

    def score_ytm(self):
        if self.ytm < 3.0: return 1
        elif self.ytm <= 5.0: return 2
        elif self.ytm <= 8.0: return 3
        elif self.ytm <= 12.0: return 4
        else: return 5

    def score_duration(self):
        if self.duration < 2.0: return 1
        elif self.duration <= 4.0: return 2
        elif self.duration <= 7.0: return 3
        elif self.duration <= 10.0: return 4
        else: return 5

    def score_rating(self):
        ratings_map = {'AAA': 1, 'AA': 1, 'A': 2, 'BBB': 3, 'BB': 4, 'B': 4, 'CCC': 5, 'CC': 5, 'C': 5, 'D': 5, 'NR': 5}
        return ratings_map.get(self.rating, 5)

    def score_net_debt_ebitda(self):
        if self.net_debt_ebitda <= 2.0: return 1
        elif self.net_debt_ebitda <= 3.5: return 2
        elif self.net_debt_ebitda <= 5.0: return 3
        elif self.net_debt_ebitda <= 7.0: return 4
        else: return 5

    def score_current_ratio(self):
        if self.current_ratio >= 2.0: return 1
        elif self.current_ratio >= 1.5: return 2
        elif self.current_ratio >= 1.0: return 3
        elif self.current_ratio >= 0.8: return 4
        else: return 5

    def score_coverage(self):
        if self.coverage_ratio >= 5.0: return 1
        elif self.coverage_ratio >= 3.0: return 2
        elif self.coverage_ratio >= 1.5: return 3
        elif self.coverage_ratio >= 1.0: return 4
        else: return 5

    def calculate_final_score(self):
        w_ytm = 0.20
        w_rating = 0.15
        w_duration = 0.15
        w_nd_ebitda = 0.25
        w_current = 0.15
        w_coverage = 0.10

        final_score = (self.score_ytm() * w_ytm) + \
                      (self.score_rating() * w_rating) + \
                      (self.score_duration() * w_duration) + \
                      (self.score_net_debt_ebitda() * w_nd_ebitda) + \
                      (self.score_current_ratio() * w_current) + \
                      (self.score_coverage() * w_coverage)
        
        return round(final_score, 2)

# --- פונקציות ליצירת גרפים יפים (Plotly) ---
def create_gauge_chart(score):
    fig = go.Figure(go.Indicator(
        mode = "gauge+number",
        value = score,
        domain = {'x': [0, 1], 'y': [0, 1]},
        title = {'text': "מדד סיכון משוקלל", 'font': {'size': 24}},
        gauge = {
            'axis': {'range': [1, 5], 'tickwidth': 1, 'tickcolor': "darkblue"},
            'bar': {'color': "rgba(0,0,0,0)"},
            'bgcolor': "white",
            'borderwidth': 2,
            'bordercolor': "gray",
            'steps': [
                {'range': [1, 2.5], 'color': "#00cc96"},
                {'range': [2.5, 3.8], 'color': "#FFA15A"},
                {'range': [3.8, 5], 'color': "#EF553B"}],
        }
    ))
    fig.add_annotation(x=0.5, y=0.4, text=f"<b>{score}</b>", showarrow=False, font=dict(size=40))
    fig.update_layout(height=350, margin=dict(l=20, r=20, t=50, b=20))
    return fig

def create_radar_chart(analyzer):
    categories = ['תשואה', 'מח״מ', 'דירוג', 'מינוף (Net Debt/EBITDA)', 'נזילות (יחס שוטף)', 'כיסוי ריבית']
    values = [analyzer.score_ytm(), analyzer.score_duration(), analyzer.score_rating(),
              analyzer.score_net_debt_ebitda(), analyzer.score_current_ratio(), analyzer.score_coverage()]
    
    values.append(values[0])
    categories.append(categories[0])

    fig = go.Figure(data=go.Scatterpolar(
        r=values,
        theta=categories,
        fill='toself',
        fillcolor='rgba(99, 110, 250, 0.5)',
        line=dict(color='#636EFA')
    ))

    fig.update_layout(
        polar=dict(
            radialaxis=dict(visible=True, range=[0, 5], tickfont=dict(size=10)),
            # תיקון הבאג: הוסרה הפקודה direction='rtl'
            angularaxis=dict(tickfont=dict(size=14)) 
        ),
        showlegend=False,
        height=400,
        margin=dict(l=40, r=40, t=40, b=40)
    )
    return fig

# --- שלב 2: ממשק המשתמש (Dashboard) ---
def main():
    st.set_page_config(page_title="מערכת מתקדמת לניתוח אג״ח", layout="wide")
    
    st.markdown(
        """
        <style>
        .stApp { direction: rtl; }
        p, div, input, label, h1, h2, h3, h4, h5, h6, span { text-align: right !important; }
        div[data-testid="stSidebar"] { direction: rtl; border-left: 1px solid #ddd; }
        div[data-testid="metric-container"] { border: 1px solid #e6e6e6; padding: 15px; border-radius: 10px; box-shadow: 2px 2px 5px rgba(0,0,0,0.05); }
        .stAlert > div { direction: rtl; text-align: right; }
        </style>
        """,
        unsafe_allow_html=True
    )

    with st.sidebar:
        st.image("https://cdn-icons-png.flaticon.com/512/2474/2474069.png", width=100)
        st.title("נתוני שוק (Market)")
        st.write("הזן את נתוני האיגרת מהבורסה:")
        ytm = st.number_input("תשואה לפדיון (%)", value=4.5, step=0.1)
        duration = st.number_input("מח״מ (שנים)", value=3.0, step=0.1)
        rating = st.selectbox("דירוג אשראי", ['AAA', 'AA', 'A', 'BBB', 'BB', 'B', 'CCC', 'CC', 'C', 'D', 'NR'], index=3)

    st.title("📊 מערכת Pro לניתוח סיכוני אג״ח")
    st.write("ברוך הבא למערכת הניתוח. המערכת משלבת נתוני שוק חיים עם ניתוח פונדמנטלי של הדוחות הכספיים.")
    
    st.write("---")
    st.subheader("ניתוח דוחות כספיים (Fundamentals)")
    
    template_data = {
        "Parameter": ["Total_Debt", "Cash", "EBITDA", "Current_Assets", "Current_Liabilities", "Operating_Profit", "Interest_Expense"],
        "Value": [1000, 200, 150, 500, 400, 120, 30]
    }
    df_template = pd.DataFrame(template_data)
    csv = df_template.to_csv(index=False).encode('utf-8-sig')
    
    col_upload, col_download = st.columns([2, 1])
    with col_download:
        st.write("<br>", unsafe_allow_html=True)
        st.download_button(label="📥 הורד תבנית נתונים (CSV)", data=csv, file_name='financial_template.csv', mime='text/csv')
    with col_upload:
        uploaded_file = st.file_uploader("העלה את קובץ הדוח הכספי (CSV) לכאן:", type=["csv"])

    if uploaded_file is not None:
        try:
            df = pd.read_csv(uploaded_file)
            data_dict = dict(zip(df['Parameter'], df['Value']))
            
            total_debt = data_dict.get("Total_Debt", 0)
            cash = data_dict.get("Cash", 0)
            ebitda = data_dict.get("EBITDA", 1) 
            current_assets = data_dict.get("Current_Assets", 0)
            current_liabilities = data_dict.get("Current_Liabilities", 1)
            operating_profit = data_dict.get("Operating_Profit", 0)
            interest_expense = data_dict.get("Interest_Expense", 1)
            
            net_debt_ebitda = (total_debt - cash) / ebitda if ebitda > 0 else 99
            current_ratio = current_assets / current_liabilities if current_liabilities > 0 else 0
            coverage_ratio = operating_profit / interest_expense if interest_expense > 0 else 99

            analyzer = AdvancedBondAnalyzer(ytm, duration, rating, net_debt_ebitda, current_ratio, coverage_ratio)
            final_score = analyzer.calculate_final_score()

            st.write("---")
            st.subheader("תוצאות הניתוח")
            
            m1, m2, m3 = st.columns(3)
            m1.metric("חוב נטו ל-EBITDA", round(net_debt_ebitda, 2), "מעל 4 = מסוכן" if net_debt_ebitda > 4 else "תקין", delta_color="inverse")
            m2.metric("יחס שוטף (נזילות)", round(current_ratio, 2), "מתחת ל-1 = סכנה" if current_ratio < 1 else "תקין")
            m3.metric("יחס כיסוי ריבית", round(coverage_ratio, 2), "מתחת ל-1.5 = חלש" if coverage_ratio < 1.5 else "תקין")

            st.write("<br>", unsafe_allow_html=True)
            
            graph_col1, graph_col2 = st.columns(2)
            
            with graph_col1:
                st.markdown("### הציון הסופי")
                fig_gauge = create_gauge_chart(final_score)
                st.plotly_chart(fig_gauge, use_container_width=True)
                
                if final_score <= 2.5:
                    st.success("✅ החברה יציבה והסיכון נמוך יחסית (השקעה סולידית).")
                elif final_score <= 3.8:
                    st.warning("⚠️ רמת סיכון בינונית. יש לבחון היטב את תמחור השוק ואת התנאים המאקרו-כלכליים.")
                else:
                    st.error("🚨 אזהרת סיכון חמורה! פרופיל פיננסי חלש המעיד על סכנת חדלות פירעון גבוהה (אג״ח זבל).")

            with graph_col2:
                st.markdown("### פרופיל סיכון רב-ממדי (1 = בטוח, 5 = מסוכן)")
                fig_radar = create_radar_chart(analyzer)
                st.plotly_chart(fig_radar, use_container_width=True)

        except Exception as e:
            st.error(f"הייתה בעיה בקריאת הקובץ. שגיאה: {e}")

if __name__ == "__main__":
    main()
