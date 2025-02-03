import streamlit as st
import pandas as pd
import math

# === 常數設定 ===
EXEMPT_AMOUNT = 1333          # 免稅額（萬）
FUNERAL_EXPENSE = 138         # 喪葬費扣除額（萬）
SPOUSE_DEDUCTION_VALUE = 553  # 配偶扣除額（萬）
ADULT_CHILD_DEDUCTION = 56    # 直系血親卑親屬扣除額（萬）
PARENTS_DEDUCTION = 138       # 父母扣除額（萬）
DISABLED_DEDUCTION = 693      # 重度以上身心障礙扣除額（萬）
OTHER_DEPENDENTS_DEDUCTION = 56  # 其他撫養扣除額（萬）

# 台灣 2025 年累進稅率結構 (上限, 稅率)
TAX_BRACKETS = [
    (5621, 0.1),
    (11242, 0.15),
    (float('inf'), 0.2)
]

# === 核心計算邏輯 ===
@st.cache_data
def calculate_estate_tax(total_assets, spouse_deduction, adult_children, other_dependents, disabled_people, parents):
    """
    計算遺產稅
    回傳值：(課稅遺產淨額, 預估遺產稅, 總扣除額)
    當免稅額加扣除額總和超過總遺產時，直接回傳課稅遺產淨額及預估遺產稅均為 0
    """
    deductions = (
        spouse_deduction +
        FUNERAL_EXPENSE +
        (disabled_people * DISABLED_DEDUCTION) +
        (adult_children * ADULT_CHILD_DEDUCTION) +
        (other_dependents * OTHER_DEPENDENTS_DEDUCTION) +
        (parents * PARENTS_DEDUCTION)
    )
    
    if total_assets < EXEMPT_AMOUNT + deductions:
        return 0, 0, deductions

    taxable_amount = int(total_assets - EXEMPT_AMOUNT - deductions)
    tax_due = 0
    previous_bracket = 0
    for bracket, rate in TAX_BRACKETS:
        if taxable_amount > previous_bracket:
            taxable_at_this_rate = min(taxable_amount, bracket) - previous_bracket
            tax_due += taxable_at_this_rate * rate
            previous_bracket = bracket
    return taxable_amount, round(tax_due, 2), deductions

def inject_custom_css():
    custom_css = """
    <style>
    body {
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        background-color: #f8f9fa;
    }
    .main-header {
        color: #2c3e50;
        text-align: center;
    }
    .data-card {
        background-color: #ffffff;
        padding: 15px;
        border-radius: 8px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        margin-bottom: 20px;
    }
    </style>
    """
    st.markdown(custom_css, unsafe_allow_html=True)

def main():
    st.set_page_config(page_title="遺產稅試算工具", layout="wide")
    inject_custom_css()
    st.markdown("<h1 class='main-header'>遺產稅試算工具</h1>", unsafe_allow_html=True)
    
    st.selectbox("選擇適用地區", ["台灣（2025年起）"], index=0)
    
    # 輸入區：資產及家庭資訊
    with st.container():
        st.markdown("### 請輸入資產及家庭資訊", unsafe_allow_html=True)
        total_assets = st.number_input("遺產總額（萬）", min_value=1000, max_value=100000, value=5000, step=100, help="請輸入您的總遺產金額（單位：萬）")
        st.markdown("---")
        st.markdown("#### 請輸入家庭成員數")
        has_spouse = st.checkbox("是否有配偶（扣除額 553 萬）", value=False)
        spouse_deduction = SPOUSE_DEDUCTION_VALUE if has_spouse else 0
        adult_children = st.number_input("直系血親卑親屬數（每人 56 萬）", min_value=0, max_value=10, value=0, help="請輸入直系血親或卑親屬人數")
        parents = st.number_input("父母數（每人 138 萬，最多 2 人）", min_value=0, max_value=2, value=0, help="請輸入父母人數")
        
        # 調整 "重度以上身心障礙者數" 的最大限制：不得大於 配偶（1 或 0） + 直系血親卑親屬數 + 父母數
        max_disabled = (1 if has_spouse else 0) + adult_children + parents
        disabled_people = st.number_input(
            "重度以上身心障礙者數（每人 693 萬）",
            min_value=0,
            max_value=max_disabled,
            value=0,
            help="請輸入重度以上身心障礙者人數，數值不得大於配偶、直系血親卑親屬數及父母數之總和"
        )
        other_dependents = st.number_input("受撫養之兄弟姊妹、祖父母數（每人 56 萬）", min_value=0, max_value=5, value=0, help="請輸入兄弟姊妹或祖父母人數")
    
    taxable_amount, tax_due, total_deductions = calculate_estate_tax(
        total_assets, spouse_deduction, adult_children, other_dependents, disabled_people, parents
    )

    # 顯示計算結果
    st.markdown("<div class='data-card'>", unsafe_allow_html=True)
    st.subheader(f"預估遺產稅：{tax_due:,.2f} 萬元")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("**資產概況**")
        df_assets = pd.DataFrame({"項目": ["遺產總額"], "金額（萬）": [total_assets]})
        st.table(df_assets)
    with col2:
        st.markdown("**扣除項目**")
        df_deductions = pd.DataFrame({
            "項目": ["免稅額", "喪葬費扣除額", "配偶扣除額", "直系血親卑親屬扣除額", "父母扣除額", "重度身心障礙扣除額", "其他撫養扣除額"],
            "金額（萬）": [
                EXEMPT_AMOUNT, 
                FUNERAL_EXPENSE, 
                spouse_deduction,
                adult_children * ADULT_CHILD_DEDUCTION, 
                parents * PARENTS_DEDUCTION,
                disabled_people * DISABLED_DEDUCTION, 
                other_dependents * OTHER_DEPENDENTS_DEDUCTION
            ]
        })
        st.table(df_deductions)
    with col3:
        st.markdown("**稅務計算**")
        df_tax = pd.DataFrame({
            "項目": ["課稅遺產淨額", "預估遺產稅"],
            "金額（萬）": [taxable_amount, tax_due]
        })
        st.table(df_tax.round(2))
    st.markdown("</div>", unsafe_allow_html=True)
    
    # 行銷導引區塊：引導用戶前往永傳家族辦公室官網
    st.markdown("---")
    st.markdown("### 想了解更多？")
    st.markdown("歡迎前往 **永傳家族辦公室**，我們提供專業的家族傳承與財富規劃服務。")
    st.markdown("[點此前往官網](https://www.gracefo.com)", unsafe_allow_html=True)

if __name__ == "__main__":
    main()
