import streamlit as st
import pandas as pd
import io

# --- שלב 1: מנוע האנליזה הפיננסית המשודרג ---
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
        # ככל שהיחס נמוך יותר, החברה בריאה יותר
        if self.net_debt_ebitda <= 2.0: return 1
        elif self.net_debt_ebitda <= 3.5: return 2
        elif self.net_debt_ebitda <= 5.0: return 3
        elif self.net_debt_ebitda <= 7.0: return 4
        else: return 5

    def score_current_ratio(self):
        # יחס שוטף - ככל שגבוה יותר (מעל 1), נזיל ובטוח יותר
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
        # משקולות מעודכנים (נותנים הרבה משקל לדוחות הכספיים)
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

# --- שלב 2: ממשק המשתמש (Dashboard) ---
def main():
    st.set_page_config(page_title="מערכת מתקדמת לניתוח אג״ח", layout="centered")
    st.title("📊 מערכת Pro לניתוח סיכוני אג״ח")
    st.write("מערכת משולבת לניתוח נתוני שוק ויחסים פיננסיים מדוחות כספיים.")

    st.header("1. נתוני שוק")
    col1, col2, col3 = st.columns(3)
    with col1:
        ytm = st.number_input("תשואה לפדיון (%)", value=4.5, step=0.1)
    with col2:
        duration = st.number_input("מח״מ (שנים)", value=3.0, step=0.1)
    with col3:
        rating = st.selectbox("דירוג אשראי", ['AAA', 'AA', 'A', 'BBB', 'BB', 'B', 'CCC', 'CC', 'C', 'D', 'NR'], index=3)

    st.write("---")
    st.header("2. ניתוח דוחות כספיים")
    
    # יצירת תבנית להורדה
    template_data = {
        "Parameter": ["Total_Debt", "Cash", "EBITDA", "Current_Assets", "Current_Liabilities", "Operating_Profit", "Interest_Expense"],
        "Value": [1000, 200, 150, 500, 400, 120, 30] # נתוני דוגמה
    }
    df_template = pd.DataFrame(template_data)
    csv = df_template.to_csv(index=False).encode('utf-8-sig')
    
    st.write("הורד את תבנית הנתונים, עדכן את המספרים מתוך הדוח הכספי של החברה, והעלה אותה חזרה לכאן.")
    st.download_button(
        label="📥 הורד תבנית נתונים (קובץ CSV לאקסל)",
        data=csv,
        file_name='financial_template.csv',
        mime='text/csv',
    )

    uploaded_file = st.file_uploader("העלה את הקובץ המלא (CSV) לחישוב אוטומטי", type=["csv"])

    if uploaded_file is not None:
        try:
            df = pd.read_csv(uploaded_file)
            data_dict = dict(zip(df['Parameter'], df['Value']))
            
            # שליפת נתונים וחישוב היחסים הפיננסיים
            total_debt = data_dict.get("Total_Debt", 0)
            cash = data_dict.get("Cash", 0)
            ebitda = data_dict.get("EBITDA", 1) # מניעת חלוקה באפס
            current_assets = data_dict.get("Current_Assets", 0)
            current_liabilities = data_dict.get("Current_Liabilities", 1)
            operating_profit = data_dict.get("Operating_Profit", 0)
            interest_expense = data_dict.get("Interest_Expense", 1)
            
            # הנוסחאות
            net_debt_ebitda = (total_debt - cash) / ebitda if ebitda > 0 else 99
            current_ratio = current_assets / current_liabilities if current_liabilities > 0 else 0
            coverage_ratio = operating_profit / interest_expense if interest_expense > 0 else 99

            st.success("הנתונים נותחו בהצלחה! הנה היחסים הפיננסיים שחולצו:")
            
            # הצגת שעונים / מדדים יפים
            metric_col1, metric_col2, metric_col3 = st.columns(3)
            metric_col1.metric("חוב נטו ל-EBITDA", round(net_debt_ebitda, 2))
            metric_col2.metric("יחס שוטף", round(current_ratio, 2))
            metric_col3.metric("יחס כיסוי ריבית", round(coverage_ratio, 2))

            # הפעלת מנוע האנליזה
            analyzer = AdvancedBondAnalyzer(ytm, duration, rating, net_debt_ebitda, current_ratio, coverage_ratio)
            final_score = analyzer.calculate_final_score()

            st.write("---")
            st.subheader("שקלול סופי (שוק + דוחות כספיים):")
            
            if final_score <= 2.0:
                st.success(f"ציון סיכון משוקלל: {final_score} - רמת סיכון נמוכה (השקעה סולידית).")
            elif final_score <= 3.5:
                st.warning(f"ציון סיכון משוקלל: {final_score} - רמת סיכון בינונית (חברה סבירה, דורש מעקב).")
            else:
                st.error(f"ציון סיכון משוקלל: {final_score} - רמת סיכון גבוהה (אזהרת חדלות פירעון).")
                
        except Exception as e:
            st.error("הייתה בעיה בקריאת הקובץ. אנא ודא שהשתמשת בתבנית המקורית ולא שינית את שמות הפרמטרים.")

if __name__ == "__main__":
    main()
