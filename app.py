import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# ============================================================
# מנוע האנליזה
# ============================================================
class BondProAnalyzer:
    def __init__(self, data):
        self.data = data

    def score_metric(self, value, thresholds, reverse=False):
        for i, t in enumerate(thresholds):
            if (value <= t if not reverse else value >= t): return i + 1
        return 5

    def calc_company_risk(self):
        nd = self.data['nd_ebitda']
        cr = self.data['current_ratio']
        cov = self.data['coverage']
        
        s_nd = self.score_metric(nd, [2, 3.5, 5, 7])
        s_cr = self.score_metric(cr, [2, 1.5, 1, 0.8], reverse=True)
        s_cov = self.score_metric(cov, [5, 3, 1.5, 1], reverse=True)
        
        # משקלות סיכון חברה
        return (s_nd * 0.5) + (s_cr * 0.25) + (s_cov * 0.25)

    def calc_bond_risk(self):
        ytm = self.data['ytm']
        dur = self.data['duration']
        rating = self.data['rating']
        collateral = self.data['collateral']
        
        s_ytm = self.score_metric(ytm, [3, 5, 8, 12])
        s_dur = self.score_metric(dur, [2, 4, 7, 10])
        s_rat = {'AAA':1, 'AA':1.5, 'A':2, 'BBB':3, 'BB':4, 'B':4.5, 'CCC':5}.get(rating, 5)
        
        raw_bond_score = (s_ytm * 0.4) + (s_rat * 0.4) + (s_dur * 0.2)
        
        # אפקט ביטחונות (מפחית סיכון)
        col_discount = {
            "ללא ביטחונות (Unsecured)": 0,
            "שעבוד צף על כלל הנכסים (Floating)": 0.3,
            "ערבות חברת אם (Parent Guarantee)": 0.4,
            "שעבוד מניות סחירות (Shares)": 0.6,
            "שעבוד ספציפי על נדל\"ן/נכס חזק (Specific Asset)": 1.0
        }
        
        adjusted_score = raw_bond_score - col_discount.get(collateral, 0)
        return max(1.0, min(adjusted_score, 5.0)) # שומר על הטווח 1-5

    def get_final_score(self):
        comp_risk = self.calc_company_risk()
        bond_risk = self.calc_bond_risk()
        return round((comp_risk * 0.5) + (bond_risk * 0.5), 2)

# ============================================================
# ויזואליזציה
# ============================================================
def create_gauge(score, title):
    fig = go.Figure(go.Indicator(
        mode="gauge+number", value=score, domain={'x': [0, 1], 'y': [0, 1]},
        title={'text': title, 'font': {'size': 20, 'color': 'white'}},
        number={'font': {'color': 'white'}},
        gauge={'axis': {'range': [1, 5], 'tickwidth': 1, 'tickcolor': "white"},
               'bar': {'color': "rgba(255,255,255,0.5)"},
               'steps': [{'range': [1, 2.5], 'color': "#00cc96"}, 
                         {'range': [2.5, 3.8], 'color': "#FFA15A"}, 
                         {'range': [3.8, 5], 'color': "#EF553B"}]}
    ))
    fig.update_layout(height=250, margin=dict(l=10, r=10, t=40, b=10), paper_bgcolor="rgba(0,0,0,0)")
    return fig

def create_comparison_radar(bonds_list):
    fig = go.Figure()
    categories = ['תשואה', 'מח"מ', 'סיכון מנפיק', 'מינוף (ND/EBITDA)', 'נזילות (יחס שוטף)', 'כיסוי ריבית']
    
    for bond in bonds_list:
        data = bond['data']
        analyzer = BondProAnalyzer(data)
        
        # המרת הנתונים לסולם של 1-5 לצורך הגרף
        vals = [
            analyzer.score_metric(data['ytm'], [3,5,8,12]),
            analyzer.score_metric(data['duration'], [2,4,7,10]),
            analyzer.calc_company_risk(),
            analyzer.score_metric(data['nd_ebitda'], [2,3.5,5,7]),
            analyzer.score_metric(data['current_ratio'], [2,1.5,1,0.8], True),
            analyzer.score_metric(data['coverage'], [5,3,1.5,1], True)
        ]
        vals.append(vals[0]) # סגירת המעגל
        cats = categories + [categories[0]]
        
        fig.add_trace(go.Scatterpolar(r=vals, theta=cats, fill='toself', name=bond['name']))
        
    fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 5])), 
                      paper_bgcolor="rgba(0,0,0,0)", font=dict(color="white"),
                      legend=dict(orientation="h", yanchor="bottom", y=1.1, xanchor="center", x=0.5))
    return fig

# ============================================================
# ממשק המשתמש
# ============================================================
def main():
    st.set_page_config(page_title="מערכת עליונה לניתוח אג\"ח", layout="wide")
    st.markdown("""<style>
    .stApp { direction: rtl; background: #0e1117; color: #fafafa; text-align: right; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
    div[data-testid="stSidebar"] { direction: rtl; text-align: right; }
    p, div, label, h1, h2, h3, span { text-align: right !important; }
    .stTooltipIcon { margin-right: 5px; }
    </style>""", unsafe_allow_html=True)

    if 'saved_bonds' not in st.session_state:
        st.session_state.saved_bonds = []

    st.title("📊 מערכת Pro לניתוח והשוואת אג\"ח")
    
    tab_input, tab_results, tab_compare = st.tabs(["✏️ הזנת נתונים", "📈 תוצאות ניתוח", "⚖️ מעבדת השוואות"])

    with tab_input:
        st.header("הזנת פרטי איגרת החוב והחברה")
        bond_name = st.text_input("שם / זיהוי האג\"ח (למשל: דלתא גליל אגח ד')", "אג\"ח דוגמה")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("🏢 נתוני החברה המנפיקה")
            m_debt = st.number_input("סך חוב פיננסי", value=1000.0, help="כלל ההתחייבויות נושאות הריבית של החברה (לטווח קצר וארוך).")
            m_cash = st.number_input("מזומן ונזילות", value=200.0, help="מזומנים, שווי מזומנים והשקעות לזמן קצר.")
            m_ebitda = st.number_input("EBITDA (רווח תפעולי תזרימי)", value=300.0, help="הרווח התפעולי של החברה בתוספת פחת והפחתות. מייצג את המזומן מפעילות שוטפת.")
            
            st.divider()
            
            m_assets = st.number_input("נכסים שוטפים", value=500.0, help="נכסים שיהפכו למזומן בשנה הקרובה (מזומן, לקוחות, מלאי).")
            m_liab = st.number_input("התחייבויות שוטפות", value=400.0, help="התחייבויות שיש לשלם בשנה הקרובה.")
            m_op = st.number_input("רווח תפעולי", value=150.0, help="הרווח מפעילות הליבה של החברה, לפני הוצאות מימון ומסים.")
            m_int = st.number_input("הוצאות מימון (ריבית)", value=50.0, help="סך הוצאות הריבית שהחברה משלמת בשנה.")

        with col2:
            st.subheader("📄 נתוני איגרת החוב (השוק)")
            ytm = st.number_input("תשואה לפדיון YTM (%)", value=4.5, step=0.1, help="התשואה השנתית הצפויה אם תחזיק את האג\"ח עד לפדיון. תשואה גבוהה מגלמת סיכון גבוה.")
            duration = st.number_input("מח\"מ (שנים)", value=3.0, step=0.1, help="משך החיים הממוצע של האג\"ח. ככל שהמח\"מ ארוך יותר, האג\"ח רגישה יותר לשינויי ריבית במשק.")
            rating = st.selectbox("דירוג אשראי", ['AAA','AA','A','BBB','BB','B','CCC','NR'], index=3, help="דירוג חברות המידרוג (מעלות/מידרוג). מ-AAA (הכי בטוח) ועד CCC (סכנת חדלות פירעון).")
            
            st.divider()
            st.subheader("🛡️ ביטחונות (Collaterals)")
            st.info("קיום שעבודים מפחית את ה-LGD (ההפסד במקרה של כשל) ומשפר את פרופיל הסיכון של האיגרת.")
            collateral = st.selectbox("סוג הבטוחה שיש לאג\"ח", [
                "ללא ביטחונות (Unsecured)",
                "שעבוד צף על כלל הנכסים (Floating)",
                "ערבות חברת אם (Parent Guarantee)",
                "שעבוד מניות סחירות (Shares)",
                "שעבוד ספציפי על נדל\"ן/נכס חזק (Specific Asset)"
            ], help="איזה נכס מגבה את החוב במקרה שהחברה קורסת?")

    # חישוב יחסים אוטומטי
    nd = (m_debt - m_cash) / m_ebitda if m_ebitda > 0 else 99
    cr = m_assets / m_liab if m_liab > 0 else 0
    cov = m_op / m_int if m_int > 0 else 99
    
    current_data = {
        'ytm': ytm, 'duration': duration, 'rating': rating, 'collateral': collateral,
        'nd_ebitda': nd, 'current_ratio': cr, 'coverage': cov
    }
    
    analyzer = BondProAnalyzer(current_data)

    with tab_results:
        st.header(f"ניתוח סיכונים: {bond_name}")
        st.caption("הציון נע בין 1 (בטוח מאוד) ל-5 (רמת סיכון גבוהה/זבל).")
        
        g1, g2, g3 = st.columns(3)
        with g1: st.plotly_chart(create_gauge(analyzer.calc_company_risk(), "סיכון החברה (אשראי)"), use_container_width=True)
        with g2: st.plotly_chart(create_gauge(analyzer.calc_bond_risk(), "סיכון האג\"ח והביטחונות"), use_container_width=True)
        with g3: st.plotly_chart(create_gauge(analyzer.get_final_score(), "ציון סיכון משוקלל סופי"), use_container_width=True)
        
        st.subheader("יחסים פיננסיים מחושבים")
        m1, m2, m3 = st.columns(3)
        m1.metric("חוב נטו ל-EBITDA", f"{round(nd, 2)}x", "יחס מעל 4 דורש זהירות" if nd > 4 else "יחס תקין", delta_color="inverse")
        m2.metric("יחס שוטף (נזילות)", f"{round(cr, 2)}x", "יחס מתחת ל-1 מסוכן" if cr < 1 else "יחס תקין")
        m3.metric("יחס כיסוי ריבית", f"{round(cov, 2)}x", "יחס מתחת ל-1.5 גבולי" if cov < 1.5 else "יחס תקין")
        
        if st.button("💾 שמור אג\"ח להשוואה", type="primary"):
            st.session_state.saved_bonds.append({"name": bond_name, "data": current_data, "score": analyzer.get_final_score()})
            st.success(f"האג\"ח '{bond_name}' נשמר בהצלחה! עבור לטאב השוואות.")

    with tab_compare:
        st.header("⚖️ מעבדת השוואת אג\"ח")
        if not st.session_state.saved_bonds:
            st.info("עדיין לא שמרת אג\"חים. חזור לטאב התוצאות ושמור איגרות כדי להשוות ביניהן.")
        else:
            if st.button("🗑️ נקה רשימת השוואה"):
                st.session_state.saved_bonds = []
                st.rerun()
                
            if st.session_state.saved_bonds:
                c1, c2 = st.columns([2, 1])
                
                with c1:
                    st.subheader("תצוגת רדאר - השוואת פרופילי סיכון")
                    st.plotly_chart(create_comparison_radar(st.session_state.saved_bonds), use_container_width=True)
                
                with c2:
                    st.subheader("טבלת סיכום")
                    df_compare = pd.DataFrame([{
                        "שם האג\"ח": b['name'],
                        "ציון סיכון סופי": b['score'],
                        "תשואה לפדיון": f"{b['data']['ytm']}%",
                        "ביטחונות": b['data']['collateral'].split("(")[0].strip()
                    } for b in st.session_state.saved_bonds])
                    st.dataframe(df_compare, hide_index=True)

if __name__ == "__main__":
    main()
