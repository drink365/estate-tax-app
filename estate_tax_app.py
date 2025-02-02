import streamlit as st
import pandas as pd
import math

# === 常數設定 ===
EXEMPT_AMOUNT = 1333  # 免稅額（萬）
FUNERAL_EXPENSE = 138  # 喪葬費扣除額（萬）
SPOUSE_DEDUCTION_VALUE = 553  # 配偶扣除額（萬）
ADULT_CHILD_DEDUCTION = 56  # 直系血親卑親屬扣除額（萬）
PARENTS_DEDUCTION = 138  # 父母扣除額（萬）
DISABLED_DEDUCTION = 693  # 重度以上身心障礙扣除額（萬）
OTHER_DEPENDENTS_DEDUCTION = 56  # 其他撫養扣除額（萬）

# 台灣 2025 年累進稅率結構 (上限, 稅率)
TAX_BRACKETS = [
    (5621, 0.1),
    (11242, 0.15),
    (float('inf'), 0.2)
]

@st.cache_data
def calculate_estate_tax(total_assets, spouse_deduction, adult_children, other_dependents, disabled_people, parents):
    deductions = (
        spouse_deduction +
        FUNERAL_EXPENSE +
        (disabled_people * DISABLED_DEDUCTION) +
        (adult_children * ADULT_CHILD_DEDUCTION) +
        (other_dependents * OTHER_DEPENDENTS_DEDUCTION) +
        (parents * PARENTS_DEDUCTION)
    )
    if total_assets < EXEMPT_AMOUNT + deductions:
        raise ValueError("扣除額總和超過了總遺產，請檢查輸入數值！")
    
    taxable_amount = int(max(0, total_assets - EXEMPT_AMOUNT - deductions))
    tax_due = 0
    previous_bracket = 0
    for bracket, rate in TAX_BRACKETS:
        if taxable_amount > previous_bracket:
            taxable_at_this_rate = min(taxable_amount, bracket) - previous_bracket
            tax_due += taxable_at_this_rate * rate
            previous_bracket = bracket
    return taxable_amount, round(tax_due, 2), deductions

def main():
    st.set_page_config(page_title="遺產稅試算工具", layout="wide")
    st.title("💰 遺產稅試算工具")
    
    total_assets = st.number_input("遺產總額（萬）", min_value=1000, max_value=100000, value=5000, step=100)
    has_spouse = st.checkbox("是否有配偶（扣除額 553 萬）", value=False)
    spouse_deduction = SPOUSE_DEDUCTION_VALUE if has_spouse else 0
    adult_children = st.number_input("直系血親卑親屬數（每人 56 萬）", min_value=0, max_value=10, value=0)
    parents = st.number_input("父母數（每人 138 萬，最多 2 人）", min_value=0, max_value=2, value=0)
    disabled_people = st.number_input("重度以上身心障礙者數（每人 693 萬）", min_value=0, max_value=10, value=0)
    other_dependents = st.number_input("受撫養之兄弟姊妹、祖父母數（每人 56 萬）", min_value=0, max_value=5, value=0)
    
    try:
        taxable_amount, tax_due, total_deductions = calculate_estate_tax(
            total_assets, spouse_deduction, adult_children, other_dependents, disabled_people, parents
        )
    except Exception as e:
        st.error(f"計算錯誤：{e}")
        return
    
    st.subheader(f"📌 預估遺產稅：{tax_due:,.2f} 萬元")
    
    # 圖表呈現不同策略下的最終家人獲得金額
    strategies = {
        "原始情況": total_assets - tax_due,
        "保單規劃": total_assets - (tax_due * 0.9),  # 模擬減稅 10%
        "提前贈與": total_assets - (tax_due * 0.85),  # 模擬減稅 15%
        "分散資產配置": total_assets - (tax_due * 0.8)  # 模擬減稅 20%
    }
    
    strategy_df = pd.DataFrame.from_dict(strategies, orient='index', columns=["家人最終可獲得金額（萬）"])
    st.bar_chart(strategy_df)
    
    # 最佳策略推薦
    best_strategy = max(strategies, key=strategies.get)
    st.success(f"✅ 最佳策略推薦：{best_strategy}，家人最終可獲得約 {strategies[best_strategy]:,.2f} 萬元！")
    
if __name__ == "__main__":
    main()
