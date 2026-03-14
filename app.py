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
        
        # משקלות סיכון חברה (פונדמנטלי)
        return (s_nd * 0.5) + (s_cr * 0.25) + (s_cov * 0.25)

    def calc_bond_risk(self):
        spread = self.data['spread']
        dur = self.data['duration']
        rating = self.data['rating']
        collateral = self.data['collateral']
        
        # סולם סיכון למרווח (באחוזים): מתחת ל-1% בטוח, מעל 6% מסוכן מאוד (זבל)
        s_spread = self.score_metric(spread, [1.0, 2.5, 4.0, 6.0])
        s_dur = self.score_metric(dur, [2, 4, 7, 10])
        s_rat = {'AAA':1, 'AA':1.5, 'A':2, 'BBB':3, 'BB':4, 'B':4.5, 'CCC':5}.get(rating, 5)
        
        # המרווח מחליף את התשואה כמדד העיקרי לסיכון השוק של האג"ח
        raw_bond_score = (s_spread * 0.45) + (s_rat * 0.35) + (s_dur * 0.20)
        
        # אפקט ביטחונות (מפחית סיכון - LGD)
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
        title={'text': title, 'font': {'size': 18, 'color': 'white'}},
        number={'font': {'color': 'white'}},
        gauge={'axis': {'range': [1, 5], 'tickwidth': 1, 'tickcolor': "white"},
               'bar': {'color': "rgba(255,255,255,0.6)"},
               'steps': [{'range': [1, 2.5], 'color': "#00cc96"}, 
                         {'range': [2.5, 3.8], 'color': "#FFA15A"}, 
                         {'range': [3.8, 5], 'color': "#EF553B"}]}
    ))
    fig.update_layout(height=250, margin=dict(l=10, r=10, t=40, b=10), paper_bgcolor="rgba(0,0,0,0)")
    return fig

def create_comparison_radar(bonds_list):
    fig = go.Figure()
    categories = ['מרווח ממשלתי', 'מח"מ', 'דירוג מנפיק', 'מינוף (ND/EBITDA)', 'נזילות (יחס שוטף)', 'כיסוי ריבית']
    
    for bond in bonds_list:
        data = bond['data']
        analyzer = BondProAnalyzer(data)
        
        # המרת הנתונים לסולם של 1-5 לצורך הגרף
        vals = [
            analyzer.score_metric(data['spread'], [1.0, 2.5, 4.0, 6.0]),
            analyzer.score_metric(data['duration'], [2, 4, 7, 10]),
            {'AAA':1, 'AA':1.5, 'A':2, 'BBB':3, 'BB':4, 'B':4.5, 'CCC':5}.get(data['rating'], 5),
            analyzer.score_metric(data['nd_ebitda'], [2, 3.5, 5, 7]),
            analyzer.score_metric(data['current_ratio'], [2, 1.5, 1, 0.8], True),
            analyzer.score_metric(data['coverage'], [5, 3, 1.5, 1], True)
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
        bond_name = st.text_input("שם / זיהוי האג\"ח (למשל: לאומי אגח סג')", "אג\"ח דוגמה")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("🏢 נתוני החברה המנפיקה (פונדמנטלי)")
            m_debt = st.number_input("סך חוב פיננסי", value=1000.0, help="כלל ההתחייבויות נושאות הריבית של החברה (לטווח קצר וארוך).")
            m_cash = st.number_input("מזומן ונזילות", value=200.0, help="מזומנים, שווי מזומנים והשקעות לזמן קצר.")
            m_ebitda = st.number_input("EBITDA (רווח תפעולי תזרימי)", value=300.0, help="הרווח התפעולי של החברה בתוספת פחת והפחתות. מראה את המזומן מפעילות הליבה.")
            
            st.divider()
            
            m_assets = st.number_input("נכסים שוטפים", value=500.0, help="נכסים שיהפכו למזומן בשנה הקרובה (מזומן, לקוחות, מלאי).")
            m_liab = st.number_input("התחייבויות שוטפות", value=400.0, help="התחייבויות שיש לשלם בשנה הקרובה.")
            m_op = st.number_input("רווח תפעולי", value=150.0, help="הרווח מפעילות החברה לפני הוצאות מימון ומסים.")
            m_int = st.number_input("הוצאות מימון (ריבית)", value=50.0, help="סך הוצאות הריבית שהחברה משלמת בשנה.")

        with col2:
            st.subheader("📄 נתוני איגרת החוב (שוק החוב)")
            
            c_yield1, c_yield2 = st.columns(2)
            with c_yield1:
                ytm = st.number_input("תשואה לפדיון האג\"ח (%)", value=4.5, step=0.1, help="התשואה השנתית הצפויה אם האיגרת תוחזק עד לפדיון.")
            with c_yield2:
                spread = st.number_input("מרווח ממשלתי (Spread) ב-%", value=2.0, step=0.1, help="הפער בין תשואת האג\"ח לתשואת אג\"ח ממשלתית במח\"מ דומה. מגלם את פרמיית הסיכון שהשוק דורש.")
            
            duration = st.number_input("מח\"מ (שנים)", value=3.0, step=0.1, help="משך החיים הממוצע של האג\"ח. מח\"מ ארוך = רגישות גבוהה יותר לשינויי ריבית.")
            rating = st.selectbox("דירוג אשראי", ['AAA','AA','A','BBB','BB','B','CCC','NR'], index=3, help="דירוג חברות המידרוג הרשמי.")
            
            st.divider()
            st.subheader("🛡️ ביטחונות (Collaterals)")
            st.caption("קיום שעבודים מפחית את ה-LGD (ההפסד במקרה של כשל) ומשפר את פרופיל הסיכון של האיגרת.")
            collateral = st.selectbox("סוג הבטוחה שיש לאג\"ח", [
                "ללא ביטחונות (Unsecured)",
                "שעבוד צף על כלל הנכסים (Floating)",
                "ערבות חברת אם (Parent Guarantee)",
                "שעבוד מניות סחירות (Shares)",
                "שעבוד ספציפי על נדל\"ן/נכס חזק (Specific Asset)"
            ])

    # חישוב יחסים אוטומטי
    nd = (m_debt - m_cash) / m_ebitda if m_ebitda > 0 else 99
    cr = m_assets / m_liab if m_liab > 0 else 0
    cov = m_op / m_int if m_int > 0 else 99
    
    current_data = {
        'ytm': ytm, 'spread': spread, 
        'duration': duration, 'rating': rating, 'collateral': collateral,
        'nd_ebitda': nd, 'current_ratio': cr, 'coverage': cov
    }
    
    analyzer = BondProAnalyzer(current_data)

    with tab_results:
        st.header(f"ניתוח סיכונים: {bond_name}")
        st.caption("הציון נע בין 1 (רמת ביטחון גבוהה) ל-5 (רמת סיכון קריטית/זבל).")
        
        g1, g2, g3 = st.columns(3)
        with g1: st.plotly_chart(create_gauge(analyzer.calc_company_risk(), "סיכון מנפיק (פונדמנטלי)"), use_container_width=True)
        with g2: st.plotly_chart(create_gauge(analyzer.calc_bond_risk(), "סיכון האג\"ח (מרווח + ביטחונות)"), use_container_width=True)
        with g3: st.plotly_chart(create_gauge(analyzer.get_final_score(), "ציון סיכון משוקלל סופי"), use_container_width=True)
        
        st.subheader("יחסים ופרמטרים מחושבים")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("מרווח ממשלתי", f"{round(spread, 2)}%", "מרווח מעל 4% מעיד על לחץ" if spread > 4 else "פרמיה תקינה", delta_color="inverse")
        m2.metric("חוב נטו ל-EBITDA", f"{round(nd, 2)}x", "מינוף גבוה מ-4 מסוכן" if nd > 4 else "מינוף תקין", delta_color="inverse")
        m3.metric("יחס שוטף", f"{round(cr, 2)}x", "נזילות נמוכה מ-1 מסוכנת" if cr < 1 else "נזילות תקינה")
        m4.metric("יחס כיסוי ריבית", f"{round(cov, 2)}x", "כיסוי חלש מ-1.5" if cov < 1.5 else "כיסוי תקין")
        
        if st.button("💾 שמור איגרת חוב להשוואה", type="primary"):
            st.session_state.saved_bonds.append({"name": bond_name, "data": current_data, "score": analyzer.get_final_score()})
            st.success(f"האג\"ח '{bond_name}' נשמר בהצלחה! עבור לטאב השוואות.")

    with tab_compare:
        st.header("⚖️ מעבדת השוואת אג\"ח")
        if not st.session_state.saved_bonds:
            st.info("רשימת ההשוואה ריקה. הוסף איגרות חוב מטאב 'תוצאות ניתוח'.")
        else:
            if st.button("🗑️ נקה רשימת השוואה"):
                st.session_state.saved_bonds = []
                st.rerun()
                
            if st.session_state.saved_bonds:
                c1, c2 = st.columns([2, 1])
                
                with c1:
                    st.subheader("תצוגת רדאר - פיזור הסיכונים")
                    st.plotly_chart(create_comparison_radar(st.session_state.saved_bonds), use_container_width=True)
                
                with c2:
                    st.subheader("טבלת סיכום")
                    df_compare = pd.DataFrame([{
                        "שם האג\"ח": b['name'],
                        "ציון כולל": b['score'],
                        "מרווח ממשלתי": f"{round(b['data']['spread'], 2)}%",
                        "תשואה לפדיון": f"{b['data']['ytm']}%",
                        "ביטחונות": b['data']['collateral'].split("(")[0].strip()
                    } for b in st.session_state.saved_bonds])
                    st.dataframe(df_compare, hide_index=True)

if __name__ == "__main__":
    main()
