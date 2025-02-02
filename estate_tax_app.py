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

# === 核心計算邏輯，並使用 st.cache_data 提升效能 ===
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

    # 檢查輸入合理性
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

def generate_basic_advice(taxable_amount, tax_due):
    """
    根據計算結果生成基本的 AI 規劃建議文字
    """
    return (
        "建議您考慮以下三種策略：\n"
        "1. 規劃保單：保單保額至少應等同於遺產稅，建議向上取整至 10 萬，例如 297.6 萬建議購買 300 萬保額。\n"
        "2. 提前贈與：利用每年 244 萬的免稅額度，逐年轉移財富，減少遺產總額。\n"
        "3. 分散資產配置：透過優化資產配置，降低累進稅率影響，假設可降低 10% 稅額。"
    )

def simulate_insurance_strategy(tax_due):
    """
    模擬保單規劃策略：
    建議的保險額度為遺產稅向上取整至最近 10 萬
    """
    recommended_insurance = math.ceil(tax_due / 10) * 10
    return recommended_insurance

def simulate_gift_strategy(total_assets, spouse_deduction, adult_children, other_dependents, disabled_people, parents, years):
    """
    模擬提前贈與策略：
    假設每年可贈與 244 萬免稅額度，總贈與金額 = years * 244 萬
    用此金額降低總遺產，再重新計算稅額
    """
    annual_gift_exemption = 244
    total_gift = years * annual_gift_exemption
    simulated_total_assets = max(total_assets - total_gift, 0)
    try:
        taxable_sim, tax_due_sim, _ = calculate_estate_tax(
            simulated_total_assets, spouse_deduction, adult_children, other_dependents, disabled_people, parents
        )
    except Exception as e:
        return None, None, simulated_total_assets
    return taxable_sim, tax_due_sim, simulated_total_assets

def simulate_diversified_strategy(tax_due):
    """
    模擬分散資產配置策略：
    假設可降低 10% 稅額，即最終稅額為原稅額的 90%
    """
    simulated_tax_due = tax_due * 0.9
    return round(simulated_tax_due, 2)

def inject_custom_css():
    """
    注入自訂 CSS 以美化介面
    """
    custom_css = """
    <style>
    /* 調整整體背景與字型 */
    body {
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        background-color: #f8f9fa;
    }
    /* 標題美化 */
    .main-header {
        color: #2c3e50;
        text-align: center;
    }
    /* 資料區塊卡片化 */
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
    # 設定頁面與注入 CSS
    st.set_page_config(page_title="遺產稅試算工具", layout="wide")
    inject_custom_css()
    st.markdown("<h1 class='main-header'>遺產稅試算工具</h1>", unsafe_allow_html=True)
    
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
    
    # 主計算流程（含錯誤處理）
    try:
        taxable_amount, tax_due, total_deductions = calculate_estate_tax(
            total_assets, spouse_deduction, adult_children, other_dependents, disabled_people, parents
        )
    except Exception as e:
        st.error(f"計算錯誤：{e}")
        return

    # 結果展示區：採用卡片式區塊
    st.markdown("<div class='data-card'>", unsafe_allow_html=True)
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
    st.markdown("</div>", unsafe_allow_html=True)
    
    # 顯示基本 AI 規劃建議
    st.markdown("## 家族傳承策略建議")
    st.text(generate_basic_advice(taxable_amount, tax_due))
    
    # --- 模擬情境：分別對三種策略進行模擬 ---
    st.markdown("### 模擬情境")
    
    # 模擬 1：保單規劃策略
    with st.expander("1. 規劃保單策略"):
        recommended_insurance = simulate_insurance_strategy(tax_due)
        st.markdown(f"**建議保險額度：** {recommended_insurance:,.0f} 萬（足以支付遺產稅）")
    
    # 模擬 2：提前贈與策略
    with st.expander("2. 提前贈與策略"):
        years = st.slider("設定提前贈與年數", min_value=1, max_value=10, value=3, step=1)
        sim_taxable, sim_tax_due, sim_total_assets = simulate_gift_strategy(
            total_assets, spouse_deduction, adult_children, other_dependents, disabled_people, parents, years
        )
        if sim_taxable is None:
            st.error("模擬計算發生錯誤，請檢查輸入數值。")
        else:
            st.markdown(f"原始總遺產：**{total_assets:,.2f} 萬元**")
            st.markdown(f"模擬後總遺產（提前贈與 {years} 年，共計可免稅 {years*244:,.0f} 萬）：**{sim_total_assets:,.2f} 萬元**")
            st.markdown(f"原始預估稅額：**{tax_due:,.2f} 萬元**")
            st.markdown(f"模擬預估稅額：**{sim_tax_due:,.2f} 萬元**")
            saved = tax_due - sim_tax_due
            percent_saved = (saved / tax_due) * 100 if tax_due else 0
            st.markdown(f"節省稅額：**{saved:,.2f} 萬元**，約節省 **{percent_saved:.1f}%**")
    
    # 模擬 3：分散資產配置策略
    with st.expander("3. 分散資產配置策略"):
        simulated_div_tax = simulate_diversified_strategy(tax_due)
        st.markdown(f"模擬後預估稅額：**{simulated_div_tax:,.2f} 萬元**")
        saved_div = tax_due - simulated_div_tax
        percent_saved_div = (saved_div / tax_due) * 100 if tax_due else 0
        st.markdown(f"節省稅額：**{saved_div:,.2f} 萬元**，約節省 **{percent_saved_div:.1f}%**")
    
if __name__ == "__main__":
    main()
