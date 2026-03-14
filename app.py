import streamlit as st

# --- שלב 1: מנוע האנליזה הפיננסית ---
class BondAnalyzer:
    def __init__(self, ytm, duration, rating, coverage_ratio):
        self.ytm = ytm
        self.duration = duration
        self.rating = rating.upper()
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
        # מיפוי דירוגים לרמת סיכון
        ratings_map = {
            'AAA': 1, 'AA': 1, 
            'A': 2, 
            'BBB': 3, 
            'BB': 4, 'B': 4, 
            'CCC': 5, 'CC': 5, 'C': 5, 'D': 5, 'NR': 5
        }
        # אם הדירוג לא נמצא במילון, נניח שהוא מסוכן (5)
        return ratings_map.get(self.rating, 5)

    def score_coverage(self):
        if self.coverage_ratio >= 5.0: return 1
        elif self.coverage_ratio >= 3.0: return 2
        elif self.coverage_ratio >= 1.5: return 3
        elif self.coverage_ratio >= 1.0: return 4
        else: return 5

    def calculate_final_score(self):
        # משקולות
        w_ytm = 0.35
        w_rating = 0.25
        w_duration = 0.20
        w_coverage = 0.20

        # חישוב התוצאה
        final_score = (self.score_ytm() * w_ytm) + \
                      (self.score_rating() * w_rating) + \
                      (self.score_duration() * w_duration) + \
                      (self.score_coverage() * w_coverage)
        
        return round(final_score, 2)

# --- שלב 2: ממשק המשתמש (GUI) ---
def main():
    st.set_page_config(page_title="מערכת לניתוח סיכוני אג״ח", layout="centered")
    st.title("📊 מערכת לניתוח סיכוני אג״ח")
    st.write("הזן את נתוני איגרת החוב כדי לקבל ציון סיכון משוקלל בין 1 (בטוח מאוד) ל-5 (מסוכן מאוד).")

    # יצירת טופס הזנת נתונים
    with st.form("bond_data_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            ytm = st.number_input("תשואה לפדיון (YTM) ב-%", min_value=-10.0, max_value=100.0, value=4.5, step=0.1)
            duration = st.number_input("מח״מ (בשנים)", min_value=0.1, max_value=50.0, value=3.0, step=0.1)
        
        with col2:
            rating_options = ['AAA', 'AA', 'A', 'BBB', 'BB', 'B', 'CCC', 'CC', 'C', 'D', 'NR']
            rating = st.selectbox("דירוג אשראי", rating_options, index=3) # ברירת מחדל BBB
            coverage_ratio = st.number_input("יחס כיסוי ריבית", min_value=-10.0, max_value=100.0, value=2.5, step=0.1)
        
        submitted = st.form_submit_button("חשב רמת סיכון")

    # הצגת התוצאה
    if submitted:
        analyzer = BondAnalyzer(ytm, duration, rating, coverage_ratio)
        final_score = analyzer.calculate_final_score()
        
        st.subheader("תוצאת הניתוח:")
        
        # התאמת צבעים וטקסט לפי רמת הסיכון
        if final_score <= 2.0:
            st.success(f"ציון סיכון: {final_score} - רמת סיכון נמוכה (השקעה סולידית).")
        elif final_score <= 3.5:
            st.warning(f"ציון סיכון: {final_score} - רמת סיכון בינונית (יש לבחון היטב את החברה).")
        else:
            st.error(f"ציון סיכון: {final_score} - רמת סיכון גבוהה (אג״ח זבל / סכנת חדלות פירעון).")
            
        st.write("---")
        st.write("**פירוט הציונים הפנימיים (מ-1 עד 5):**")
        st.write(f"* ציון תשואה: {analyzer.score_ytm()}")
        st.write(f"* ציון מח״מ: {analyzer.score_duration()}")
        st.write(f"* ציון דירוג אשראי: {analyzer.score_rating()}")
        st.write(f"* ציון יחס כיסוי: {analyzer.score_coverage()}")

if __name__ == "__main__":
    main()
