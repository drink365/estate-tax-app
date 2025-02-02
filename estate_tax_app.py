import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

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

# === 核心計算邏輯，並使用 st.cache_data 以提升效能 ===
@st.cache_data
def calculate_estate_tax(total_assets, spouse_deduction, adult_children, other_dependents, disabled_people, parents):
    """
    計算遺產稅，若扣除額總和超過總遺產，則拋出錯誤。
    回傳值：(課稅遺產淨額, 預估遺產稅, 總扣除額)
    """
    # 計算總扣除額
    deductions = (
        spouse_deduction +
        FUNERAL_EXPENSE +
        (disabled_people * DISABLED_DEDUCTION) +
        (adult_children * ADULT_CHILD_DEDUCTION) +
        (other_dependents * OTHER_DEPENDENTS_DEDUCTION) +
        (parents * PARENTS_DEDUCTION)
    )

    # 若扣除額總和超過 (免稅額 + 扣除額) ，則表示輸入資料可能有誤
    if total_assets < EXEMPT_AMOUNT + deductions:
        raise ValueError("扣除額總和超過了總遺產，請檢查輸入數值！")
    
    # 課稅遺產淨額（取整數）
    taxable_amount = int(max(0, total_assets - EXEMPT_AMOUNT - deductions))
    
    # 根據累進稅率計算遺產稅
    tax_due = 0
    previous_bracket = 0
    for bracket, rate in TAX_BRACKETS:
        if taxable_amount > previous_bracket:
            taxable_at_this_rate = min(taxable_amount, bracket) - previous_bracket
            tax_due += taxable_at_this_rate * rate
            previous_bracket = bracket
    return taxable_amount, round(tax_due, 2), deductions

def generate_advice(taxable_amount, tax_due):
    """
    根據計算結果生成簡單的 AI 規劃建議文字
    """
    return (
        "根據您的情況，建議您考慮以下策略來降低遺產稅負擔：\n"
        "1. 規劃保單，預留遺產稅資金\n"
        "2. 提前贈與，逐步轉移財富\n"
        "3. 分散資產配置，降低稅務影響"
    )

def main():
    st.set_page_config(page_title="遺產稅試算工具", layout="wide")
    st.header("遺產稅試算工具")
    
    # 地區選擇（目前僅提供台灣 2025 年起的版本）
    st.selectbox("選擇適用地區", ["台灣（2025年起）"], index=0)
    
    # 側邊欄輸入區
    st.sidebar.header("請輸入遺產資訊")
    total_assets = st.sidebar.number_input(
        "遺產總額（萬）",
        min_value=1000,
        max_value=100000,
        value=5000,
        step=100,
        help="請輸入您的總遺產金額（單位：萬）"
    )
    
    st.sidebar.subheader("扣除額（根據家庭成員數填寫）")
    has_spouse = st.sidebar.checkbox("是否有配偶（扣除額 553 萬）", value=False)
    spouse_deduction = SPOUSE_DEDUCTION_VALUE if has_spouse else 0
    adult_children = st.sidebar.number_input(
        "直系血親卑親屬數（每人 56 萬）",
        min_value=0,
        max_value=10,
        value=0,
        help="請輸入直系血親或卑親屬人數"
    )
    parents = st.sidebar.number_input(
        "父母數（每人 138 萬，最多 2 人）",
        min_value=0,
        max_value=2,
        value=0,
        help="請輸入父母人數"
    )
    max_disabled = max(1, adult_children + parents + (1 if has_spouse else 0))
    disabled_people = st.sidebar.number_input(
        "重度以上身心障礙者數（每人 693 萬）",
        min_value=0,
        max_value=max_disabled,
        value=0,
        help="請輸入重度以上身心障礙者人數"
    )
    other_dependents = st.sidebar.number_input(
        "受撫養之兄弟姊妹、祖父母數（每人 56 萬）",
        min_value=0,
        max_value=5,
        value=0,
        help="請輸入兄弟姊妹或祖父母人數"
    )
    
    # 進行計算（錯誤處理）
    try:
        taxable_amount, tax_due, total_deductions = calculate_estate_tax(
            total_assets, spouse_deduction, adult_children, other_dependents, disabled_people, parents
        )
    except Exception as e:
        st.error(f"計算錯誤：{e}")
        return

    # 展示結果
    st.subheader(f"預估遺產稅：{tax_due:,.2f} 萬元")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("**資產概況**")
        df_assets = pd.DataFrame({
            "項目": ["遺產總額"],
            "金額（萬）": [total_assets]
        })
        st.table(df_assets)
    
    with col2:
        st.markdown("**扣除項目**")
        df_deductions = pd.DataFrame({
            "項目": [
                "免稅額",
                "喪葬費扣除額",
                "配偶扣除額",
                "直系血親卑親屬扣除額",
                "父母扣除額",
                "重度身心障礙扣除額",
                "其他撫養扣除額"
            ],
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
        st.table(df_tax)
    
    # 顯示 AI 規劃建議
    st.markdown("## AI 規劃建議")
    st.text(generate_advice(taxable_amount, tax_due))
    
if __name__ == "__main__":
    main()
