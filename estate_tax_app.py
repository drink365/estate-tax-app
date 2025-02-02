import streamlit as st
import pandas as pd
import math
import io

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

@st.cache_data
def calculate_estate_tax(total_assets, spouse_deduction, adult_children, other_dependents, disabled_people, parents):
    deductions = (
        spouse_deduction + FUNERAL_EXPENSE +
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

def generate_basic_advice(taxable_amount, tax_due):
    suggestions = []
    if tax_due > 1000:
        suggestions.append("✅ 規劃保單可減少資產計入課稅，提升繼承人獲得的金額。")
    if taxable_amount > 5000:
        suggestions.append("✅ 每年利用 244 萬的免稅贈與額度，可逐步降低遺產總額。")
    if tax_due > taxable_amount * 0.15:
        suggestions.append("✅ 調整資產配置，降低遺產稅負擔，確保家人資產最大化。")
    
    return "\n".join(suggestions) if suggestions else "✅ 您的稅負不高，但仍可進一步優化資產規劃。"

def generate_report(taxable_amount, tax_due, total_assets):
    report = f"""
    遺產總額: {total_assets} 萬元
    課稅遺產淨額: {taxable_amount} 萬元
    預估遺產稅: {tax_due} 萬元
    
    建議規劃方案：
    {generate_basic_advice(taxable_amount, tax_due)}
    """
    return report

def main():
    st.set_page_config(page_title="遺產稅試算工具", layout="wide")
    st.title("遺產稅試算工具")
    
    with st.sidebar:
        st.header("輸入家庭資訊")
        total_assets = st.number_input("遺產總額（萬）", min_value=1000, max_value=100000, value=5000, step=100)
        has_spouse = st.radio("是否有配偶（扣除額 553 萬）", ["無", "有"])
        spouse_deduction = SPOUSE_DEDUCTION_VALUE if has_spouse == "有" else 0
        adult_children = st.slider("直系血親卑親屬數", 0, 10, 0)
        parents = st.slider("父母數（最多2人）", 0, 2, 0)
        disabled_people = st.slider("重度以上身心障礙者數", 0, max(1, adult_children + parents + (1 if has_spouse == "有" else 0)), 0)
        other_dependents = st.slider("受撫養兄弟姊妹、祖父母數", 0, 5, 0)
    
    try:
        taxable_amount, tax_due, total_deductions = calculate_estate_tax(
            total_assets, spouse_deduction, adult_children, other_dependents, disabled_people, parents
        )
    except Exception as e:
        st.error(f"計算錯誤：{e}")
        return
    
    st.metric(label="預估遺產稅", value=f"{tax_due:,.2f} 萬元")
    st.metric(label="總扣除額", value=f"{total_deductions:,.2f} 萬元")
    st.progress(int((tax_due / total_assets) * 100))
    
    st.subheader("家族傳承策略建議")
    st.text(generate_basic_advice(taxable_amount, tax_due))
    
    if st.button("下載完整遺產稅規劃報告"):
        report_text = generate_report(taxable_amount, tax_due, total_assets)
        buffer = io.BytesIO()
        buffer.write(report_text.encode("utf-8"))
        st.download_button(
            label="點擊下載報告",
            data=buffer.getvalue(),
            file_name="遺產稅規劃報告.txt",
            mime="text/plain"
        )

if __name__ == "__main__":
    main()
