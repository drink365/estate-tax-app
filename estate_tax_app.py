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
    return (
        "建議您考慮以下三種策略：\n"
        "1. 規劃保單：透過購買適當的保險，有機會降低課稅基數，提供家人流動資金支持。\n"
        "2. 提前贈與：利用每年244萬的免稅贈與額度，逐年轉移財富，降低遺產總額。\n"
        "3. 分散資產配置：假設分散配置可使稅率下降10%，稅額降至約90%。"
    )

def simulate_insurance_strategy(total_assets, spouse_deduction, adult_children, other_dependents, disabled_people, parents):
    """
    模擬保單策略：
    - 假設保險理賠金：向上取整至最近100萬（例如297→300）
    - 假設保費 = 假設保險理賠金 ÷ 1.5
    【原始情況】：
      - 遺產總額、預估稅額、家人總共收到 = 遺產總額 - 預估稅額
    【有規劃保單】：
      - (未被實質課稅) 預估稅額 = 稅額(遺產總額 - 假設保費)，家人總共收到 = (遺產總額 - 假設保費 - 預估稅額) + 假設保險理賠金
      - (被實質課稅) 有效遺產 = 遺產總額 - 假設保費 + 假設保險理賠金，家人總共收到 = 有效遺產 - 預估稅額
    """
    # 原始情況
    _, tax_no_insurance, _ = calculate_estate_tax(total_assets, spouse_deduction, adult_children, other_dependents, disabled_people, parents)
    net_no_insurance = total_assets - tax_no_insurance

    # 假設保險方案計算
    assumed_payout = round(math.ceil(tax_no_insurance / 100) * 100, 2)
    assumed_premium = round(assumed_payout / 1.5, 2)

    # 模擬未被實質課稅
    new_total_assets = total_assets - assumed_premium
    _, tax_new, _ = calculate_estate_tax(new_total_assets, spouse_deduction, adult_children, other_dependents, disabled_people, parents)
    net_not_taxed = round((new_total_assets - tax_new) + assumed_payout, 2)
    effect_not_taxed = round(net_not_taxed - net_no_insurance, 2)

    # 模擬被實質課稅：有效遺產 = 遺產總額 - 假設保費 + 假設保險理賠金
    effective_estate = total_assets - assumed_premium + assumed_payout
    _, tax_effective, _ = calculate_estate_tax(effective_estate, spouse_deduction, adult_children, other_dependents, disabled_people, parents)
    net_taxed = round(effective_estate - tax_effective, 2)
    effect_taxed = round(net_taxed - net_no_insurance, 2)

    return {
        "原始情況": {
            "遺產總額": total_assets,
            "預估稅額": tax_no_insurance,
            "家人總共收到": net_no_insurance
        },
        "有規劃保單 (未被實質課稅)": {
            "假設保費": assumed_premium,
            "假設保險理賠金": assumed_payout,
            "預估稅額": tax_new,
            "家人總共收到": net_not_taxed,
            "規劃效果": effect_not_taxed
        },
        "有規劃保單 (被實質課稅)": {
            "假設保費": assumed_premium,
            "假設保險理賠金": assumed_payout,
            "家人總共收到": net_taxed,
            "規劃效果": effect_taxed
        }
    }

def simulate_gift_strategy(total_assets, spouse_deduction, adult_children, other_dependents, disabled_people, parents, years):
    """
    模擬提前贈與策略：
    假設每年可贈與244萬免稅額度，
    總贈與金額 = 年數 * 244萬，
    規劃後遺產 = 遺產總額 - 總贈與金額，
    重新計算稅額後，
    家人總共收到 = (規劃後遺產 - 預估稅額) + 總贈與金額。
    規劃效果 = 家人總共收到(規劃後) - 家人總共收到(原始)
    """
    annual_gift_exemption = 244
    total_gift = years * annual_gift_exemption
    simulated_total_assets = max(total_assets - total_gift, 0)
    _, tax_sim, _ = calculate_estate_tax(simulated_total_assets, spouse_deduction, adult_children, other_dependents, disabled_people, parents)
    net_after = round((simulated_total_assets - tax_sim) + total_gift, 2)
    _, tax_original, _ = calculate_estate_tax(total_assets, spouse_deduction, adult_children, other_dependents, disabled_people, parents)
    net_original = total_assets - tax_original
    effect = round(net_after - net_original, 2)

    return {
        "原始情況": {
            "遺產總額": total_assets,
            "預估稅額": tax_original,
            "家人總共收到": net_original
        },
        "提前贈與後": {
            "遺產總額": simulated_total_assets,
            "預估稅額": tax_sim,
            "總贈與金額": round(total_gift, 2),
            "家人總共收到": net_after,
            "贈與年數": years
        },
        "規劃效果": {
            "較原始情況增加": effect
        }
    }

def simulate_diversified_strategy(tax_due):
    """
    模擬分散資產配置策略：
    假設透過分散資產配置，可使稅率降低10%，
    即最終稅額 = 原稅額的90%，
    並計算規劃效果及節省百分比。
    """
    simulated_tax_due = round(tax_due * 0.9, 2)
    saved = round(tax_due - simulated_tax_due, 2)
    percent_saved = round((saved / tax_due) * 100, 2) if tax_due else 0
    return {
        "原始情況": {
            "預估稅額": tax_due
        },
        "分散資產配置後": {
            "預估稅額": simulated_tax_due
        },
        "規劃效果": {
            "較原始情況增加": saved,
            "節省百分比": percent_saved
        }
    }

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
    .effect {
        color: green;
        font-weight: bold;
    }
    .explanation {
        color: #0077CC;
    }
    </style>
    """
    st.markdown(custom_css, unsafe_allow_html=True)

def main():
    st.set_page_config(page_title="遺產稅試算工具", layout="wide")
    inject_custom_css()
    st.markdown("<h1 class='main-header'>遺產稅試算工具</h1>", unsafe_allow_html=True)
    
    st.selectbox("選擇適用地區", ["台灣（2025年起）"], index=0)
    
    # 輸入區移至主畫面上方
    with st.container():
        st.markdown("### 請輸入資產及家庭資訊", unsafe_allow_html=True)
        total_assets = st.number_input("遺產總額（萬）", min_value=1000, max_value=100000, value=5000, step=100, help="請輸入您的總遺產金額（單位：萬）")
        st.markdown("---")
        st.markdown("#### 請輸入家庭成員數")
        has_spouse = st.checkbox("是否有配偶（扣除額 553 萬）", value=False)
        spouse_deduction = SPOUSE_DEDUCTION_VALUE if has_spouse else 0
        adult_children = st.number_input("直系血親卑親屬數（每人 56 萬）", min_value=0, max_value=10, value=0, help="請輸入直系血親或卑親屬人數")
        parents = st.number_input("父母數（每人 138 萬，最多 2 人）", min_value=0, max_value=2, value=0, help="請輸入父母人數")
        max_disabled = max(1, adult_children + parents + (1 if has_spouse else 0))
        disabled_people = st.number_input("重度以上身心障礙者數（每人 693 萬）", min_value=0, max_value=max_disabled, value=0, help="請輸入重度以上身心障礙者人數")
        other_dependents = st.number_input("受撫養之兄弟姊妹、祖父母數（每人 56 萬）", min_value=0, max_value=5, value=0, help="請輸入兄弟姊妹或祖父母人數")
    
    try:
        taxable_amount, tax_due, total_deductions = calculate_estate_tax(total_assets, spouse_deduction, adult_children, other_dependents, disabled_people, parents)
    except Exception as e:
        st.error(f"計算錯誤：{e}")
        return

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
                EXEMPT_AMOUNT, FUNERAL_EXPENSE, spouse_deduction,
                adult_children * ADULT_CHILD_DEDUCTION, parents * PARENTS_DEDUCTION,
                disabled_people * DISABLED_DEDUCTION, other_dependents * OTHER_DEPENDENTS_DEDUCTION
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
    
    st.markdown("## 家族傳承策略建議")
    st.text(generate_basic_advice(taxable_amount, tax_due))
    
    # 使用 Tabs 統一呈現三種模擬策略
    tabs = st.tabs(["保單規劃策略", "提前贈與策略", "分散資產配置策略"])
    
    # 保單規劃策略模擬
    with tabs[0]:
        st.markdown("#### 保單規劃策略說明", unsafe_allow_html=True)
        st.markdown("<span class='explanation'>保單規劃策略：保險理賠金和保費依公式計算；未被實質課稅時，理賠金不參與課稅；【被實質課稅】則保險理賠金納入遺產稅計算。</span>", unsafe_allow_html=True)
        insurance_results = simulate_insurance_strategy(total_assets, spouse_deduction, adult_children, other_dependents, disabled_people, parents)
        st.markdown("**【原始情況】**")
        original = insurance_results["原始情況"]
        st.markdown(f"- 遺產總額：**{original['遺產總額']:,.2f} 萬元**")
        st.markdown(f"- 預估稅額：**{original['預估稅額']:,.2f} 萬元**")
        st.markdown(f"- 家人總共收到：**{original['家人總共收到']:,.2f} 萬元**")
        st.markdown("**【有規劃保單（未被實質課稅）】**")
        not_taxed = insurance_results["有規劃保單 (未被實質課稅)"]
        st.markdown(f"- 假設保費：**{not_taxed['假設保費']:,.2f} 萬**，理賠金：**{not_taxed['假設保險理賠金']:,.2f} 萬**")
        st.markdown(f"- 預估稅額：**{not_taxed['預估稅額']:,.2f} 萬元**")
        st.markdown(f"- 家人總共收到：**{not_taxed['家人總共收到']:,.2f} 萬元**")
        st.markdown(f"- 規劃效果：<span class='effect'>較原始情況增加 {not_taxed['規劃效果']:,.2f} 萬元</span>", unsafe_allow_html=True)
        st.markdown("**【有規劃保單（被實質課稅）】**")
        taxed = insurance_results["有規劃保單 (被實質課稅)"]
        effective_estate = total_assets - taxed["假設保費"] + taxed["假設保險理賠金"]
        effective_tax = calculate_estate_tax(effective_estate, spouse_deduction, adult_children, other_dependents, disabled_people, parents)[1]
        st.markdown(f"- 假設保費：**{taxed.get('假設保費', 0):,.2f} 萬**，理賠金：**{taxed.get('假設保險理賠金', 0):,.2f} 萬**")
        st.markdown(f"- 預估稅額：**{effective_tax:,.2f} 萬元**")
        st.markdown(f"- 家人總共收到：**{taxed['家人總共收到']:,.2f} 萬元**")
        st.markdown(f"- 規劃效果：<span class='effect'>較原始情況增加 {taxed['規劃效果']:,.2f} 萬元</span>", unsafe_allow_html=True)
    
    # 提前贈與策略模擬
    with tabs[1]:
        st.markdown("#### 提前贈與策略說明", unsafe_allow_html=True)
        st.markdown("<span class='explanation'>提前贈與策略：每年贈與244萬免稅額度，總贈與金額 = 年數 × 244萬；家人收到的金額包含全部贈與金額。</span>", unsafe_allow_html=True)
        years = st.slider("設定提前贈與年數", 1, 10, 3, 1)
        gift_results = simulate_gift_strategy(total_assets, spouse_deduction, adult_children, other_dependents, disabled_people, parents, years)
        st.markdown("**【原始情況】**")
        original_gift = gift_results["原始情況"]
        st.markdown(f"- 遺產總額：**{original_gift['遺產總額']:,.2f} 萬元**")
        st.markdown(f"- 預估稅額：**{original_gift['預估稅額']:,.2f} 萬元**")
        st.markdown(f"- 家人總共收到：**{original_gift['家人總共收到']:,.2f} 萬元**")
        st.markdown("**【提前贈與後】**")
        after_gift = gift_results["提前贈與後"]
        st.markdown(f"- 贈與年數：**{after_gift['贈與年數']} 年**")
        st.markdown(f"- 遺產總額：**{after_gift['遺產總額']:,.2f} 萬元**")
        st.markdown(f"- 預估稅額：**{after_gift['預估稅額']:,.2f} 萬元**")
        st.markdown(f"- 總贈與金額：**{after_gift['總贈與金額']:,.2f} 萬元**")
        st.markdown(f"- 家人總共收到：**{after_gift['家人總共收到']:,.2f} 萬元**")
        effect_gift = gift_results["規劃效果"]
        st.markdown(f"- 規劃效果：<span class='effect'>較原始情況增加 {effect_gift['較原始情況增加']:,.2f} 萬元</span>", unsafe_allow_html=True)
    
    # 分散資產配置策略模擬
    with tabs[2]:
        st.markdown("#### 分散資產配置策略說明", unsafe_allow_html=True)
        st.markdown("<span class='explanation'>分散配置策略：假設分散配置可使稅率下降10%，稅額降至約90%。</span>", unsafe_allow_html=True)
        div_results = simulate_diversified_strategy(tax_due)
        st.markdown("**【原始情況】**")
        st.markdown(f"- 預估稅額：**{div_results['原始情況']['預估稅額']:,.2f} 萬元**")
        st.markdown("**【分散資產配置後】**")
        st.markdown(f"- 預估稅額：**{div_results['分散資產配置後']['預估稅額']:,.2f} 萬元**")
        effect_div = div_results["規劃效果"]
        st.markdown(f"- 規劃效果：<span class='effect'>較原始情況增加 {effect_div['較原始情況增加']:,.2f} 萬元</span>", unsafe_allow_html=True)
    
    # 行銷導引區塊：引導用戶前往永傳家族辦公室官網
    st.markdown("---")
    st.markdown("### 想了解更多？")
    st.markdown("歡迎前往 **永傳家族辦公室**，我們提供專業的家族傳承與財富規劃服務。")
    st.markdown("[點此前往官網](https://www.gracefo.com)", unsafe_allow_html=True)

if __name__ == "__main__":
    main()
