import streamlit as st
import pandas as pd
import math
import plotly.express as px
from typing import Tuple, Dict, Any
from datetime import datetime
import time

# ===============================
# 1. 基本設定與常數（單位：萬）
# ===============================
st.set_page_config(page_title="遺產稅試算", layout="wide")

# 響應式設計：自訂 CSS 調整手機板版面
st.markdown(
    """
    <style>
    /* 當螢幕寬度小於 600px 時，調整標題與文字大小 */
    @media only screen and (max-width: 600px) {
        .main-header {font-size: 24px !important;}
        .stMarkdown {font-size: 14px !important;}
    }
    </style>
    """, unsafe_allow_html=True)

# 常數設定，可考慮未來集中管理
EXEMPT_AMOUNT = 1333          # 免稅額
FUNERAL_EXPENSE = 138         # 喪葬費扣除額
SPOUSE_DEDUCTION_VALUE = 553  # 配偶扣除額
ADULT_CHILD_DEDUCTION = 56    # 每位子女扣除額
PARENTS_DEDUCTION = 138       # 父母扣除額
DISABLED_DEDUCTION = 693      # 重度身心障礙扣除額
OTHER_DEPENDENTS_DEDUCTION = 56  # 其他撫養扣除額

# 台灣 2025 年累進稅率結構
TAX_BRACKETS = [
    (5621, 0.1),
    (11242, 0.15),
    (float('inf'), 0.2)
]

# ===============================
# 2. 登入驗證（保護區用）
# ===============================
# 請在 Streamlit Cloud 的 Secrets 或 .streamlit/secrets.toml 中設定：
# [authorized_users.admin]
# name = "管理者"
# username = "admin"
# password = "secret"
# start_date = "2023-01-01"
# end_date = "2025-12-31"
# [authorized_users.user1]
# name = "使用者一"
# username = "user1"
# password = "pass1"
# start_date = "2023-03-01"
# end_date = "2025-12-31"
# [authorized_users.user2]
# name = "使用者二"
# username = "user2"
# password = "pass2"
# start_date = "2023-05-01"
# end_date = "2024-12-31"
authorized_users = st.secrets["authorized_users"]

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

def check_credentials(input_username: str, input_password: str) -> Tuple[bool, str]:
    """
    檢查使用者認證，並驗證使用權限日期

    :param input_username: 輸入的帳號
    :param input_password: 輸入的密碼
    :return: (是否通過, 使用者名稱)
    """
    if input_username in authorized_users:
        user_info = authorized_users[input_username]
        if input_password == user_info["password"]:
            start_date = datetime.strptime(user_info["start_date"], "%Y-%m-%d")
            end_date = datetime.strptime(user_info["end_date"], "%Y-%m-%d")
            today = datetime.today()
            if start_date <= today <= end_date:
                return True, user_info["name"]
            else:
                st.error("您的使用權限尚未啟用或已過期")
                return False, ""
        else:
            st.error("密碼錯誤")
            return False, ""
    else:
        st.error("查無此使用者")
        return False, ""

# ===============================
# 3. 稅務計算相關函式
# ===============================
def compute_deductions(spouse: bool, adult_children: int, other_dependents: int,
                       disabled_people: int, parents: int) -> float:
    """
    計算各項扣除額

    :return: 扣除總額（萬）
    """
    spouse_deduction = SPOUSE_DEDUCTION_VALUE if spouse else 0
    total_deductions = (
        spouse_deduction +
        FUNERAL_EXPENSE +
        (disabled_people * DISABLED_DEDUCTION) +
        (adult_children * ADULT_CHILD_DEDUCTION) +
        (other_dependents * OTHER_DEPENDENTS_DEDUCTION) +
        (parents * PARENTS_DEDUCTION)
    )
    return total_deductions

@st.cache_data
def calculate_estate_tax(total_assets: float, spouse: bool, adult_children: int,
                          other_dependents: int, disabled_people: int, parents: int
                         ) -> Tuple[float, float, float]:
    """
    根據輸入計算可課稅金額與預估遺產稅

    :return: (課稅遺產淨額, 預估遺產稅, 扣除總額)
    """
    deductions = compute_deductions(spouse, adult_children, other_dependents, disabled_people, parents)
    if total_assets < EXEMPT_AMOUNT + deductions:
        return 0, 0, deductions
    taxable_amount = max(0, total_assets - EXEMPT_AMOUNT - deductions)
    tax_due = 0.0
    previous_bracket = 0
    for bracket, rate in TAX_BRACKETS:
        if taxable_amount > previous_bracket:
            taxable_at_rate = min(taxable_amount, bracket) - previous_bracket
            tax_due += taxable_at_rate * rate
            previous_bracket = bracket
    return taxable_amount, round(tax_due, 0), deductions

def generate_basic_advice() -> str:
    """
    產生基本的家族傳承策略建議文字
    """
    advice = (
        "<span style='color: blue;'>1. 規劃保單</span>：透過保險預留稅源。<br><br>"
        "<span style='color: blue;'>2. 提前贈與</span>：利用免稅贈與逐年轉移財富。<br><br>"
        "<span style='color: blue;'>3. 分散配置</span>：透過合理資產配置降低稅負。"
    )
    return advice

def simulate_insurance_strategy(total_assets: float, spouse: bool, adult_children: int,
                                other_dependents: int, disabled_people: int, parents: int,
                                premium_ratio: float, premium: float) -> Dict[str, Any]:
    """
    模擬保單策略效益

    :return: 不同策略下的稅務與淨資產數據
    """
    _, tax_no_insurance, _ = calculate_estate_tax(total_assets, spouse, adult_children, other_dependents, disabled_people, parents)
    net_no_insurance = total_assets - tax_no_insurance
    claim_amount = round(premium * premium_ratio, 0)
    new_total_assets = total_assets - premium
    _, tax_new, _ = calculate_estate_tax(new_total_assets, spouse, adult_children, other_dependents, disabled_people, parents)
    net_not_taxed = round(new_total_assets - tax_new + claim_amount, 0)
    effect_not_taxed = net_not_taxed - net_no_insurance
    effective_estate = total_assets - premium + claim_amount
    _, tax_effective, _ = calculate_estate_tax(effective_estate, spouse, adult_children, other_dependents, disabled_people, parents)
    net_taxed = round(effective_estate - tax_effective, 0)
    effect_taxed = net_taxed - net_no_insurance
    return {
        "沒有規劃": {
            "總資產": int(total_assets),
            "預估遺產稅": int(tax_no_insurance),
            "家人總共取得": int(net_no_insurance)
        },
        "有規劃保單": {
            "預估遺產稅": int(tax_new),
            "家人總共取得": int(net_not_taxed),
            "規劃效果": int(effect_not_taxed)
        },
        "有規劃保單 (被實質課稅)": {
            "預估遺產稅": int(tax_effective),
            "家人總共取得": int(net_taxed),
            "規劃效果": int(effect_taxed)
        }
    }

def simulate_gift_strategy(total_assets: float, spouse: bool, adult_children: int,
                             other_dependents: int, disabled_people: int, parents: int,
                             years: int) -> Dict[str, Any]:
    """
    模擬提前贈與策略效益

    :return: 模擬結果數據
    """
    annual_gift_exemption = 244
    total_gift = years * annual_gift_exemption
    simulated_total_assets = max(total_assets - total_gift, 0)
    _, tax_sim, _ = calculate_estate_tax(simulated_total_assets, spouse, adult_children, other_dependents, disabled_people, parents)
    net_after = round(simulated_total_assets - tax_sim + total_gift, 0)
    _, tax_original, _ = calculate_estate_tax(total_assets, spouse, adult_children, other_dependents, disabled_people, parents)
    net_original = total_assets - tax_original
    effect = net_after - net_original
    return {
        "沒有規劃": {
            "總資產": int(total_assets),
            "預估遺產稅": int(tax_original),
            "家人總共取得": int(net_original)
        },
        "提前贈與後": {
            "總資產": int(simulated_total_assets),
            "預估遺產稅": int(tax_sim),
            "總贈與金額": int(total_gift),
            "家人總共取得": int(net_after),
            "贈與年數": years
        },
        "規劃效果": {
            "較沒有規劃增加": int(effect)
        }
    }

def simulate_diversified_strategy(tax_due: float) -> Dict[str, Any]:
    """
    模擬分散配置策略效益

    :return: 模擬結果數據
    """
    tax_factor = 0.90
    simulated_tax_due = round(tax_due * tax_factor, 0)
    saved = tax_due - simulated_tax_due
    percent_saved = round((saved / tax_due) * 100, 2) if tax_due else 0
    return {
        "沒有規劃": {
            "預估遺產稅": int(tax_due)
        },
        "分散配置後": {
            "預估遺產稅": int(simulated_tax_due)
        },
        "規劃效果": {
            "較沒有規劃減少": int(saved),
            "節省百分比": percent_saved
        }
    }

# ===============================
# 4. 繪圖函式
# ===============================
def plot_strategy_comparison(df: pd.DataFrame) -> None:
    """
    利用 Plotly 畫出不同規劃策略下家人總共取得金額的比較圖

    :param df: 包含策略數據的 DataFrame
    """
    fig_bar = px.bar(
        df,
        x="規劃策略",
        y="家人總共取得（萬）",
        title="不同規劃策略下家人總共取得金額比較（案例）",
        text="家人總共取得（萬）"
    )
    fig_bar.update_traces(texttemplate='%{text:.0f}', textposition='outside')

    baseline_value = df.loc[df["規劃策略"] == "沒有規劃", "家人總共取得（萬）"].iloc[0]
    for idx, row in df.iterrows():
        if row["規劃策略"] != "沒有規劃":
            diff = row["家人總共取得（萬）"] - baseline_value
            diff_text = f"+{int(diff)}" if diff >= 0 else f"{int(diff)}"
            fig_bar.add_annotation(
                x=row["規劃策略"],
                y=row["家人總共取得（萬）"],
                text=diff_text,
                showarrow=False,
                font=dict(color="yellow", size=14),
                yshift=-50
            )
    max_value = df["家人總共取得（萬）"].max()
    dtick = max_value / 10
    fig_bar.update_layout(margin=dict(t=100), yaxis_range=[0, max_value + dtick], autosize=True)
    st.plotly_chart(fig_bar, use_container_width=True)

# ===============================
# 5. 主程式區塊（非保護區：遺產稅試算與策略建議）
# ===============================
st.markdown("<h1 class='main-header'>遺產稅試算</h1>", unsafe_allow_html=True)
st.selectbox("選擇適用地區", ["台灣（2025年起）"], index=0)

with st.container():
    st.markdown("### 請輸入資產及家庭資訊")
    total_assets_input: float = st.number_input("總資產（萬）", min_value=1000, max_value=100000,
                                                  value=5000, step=100,
                                                  help="請輸入您的總資產（單位：萬）")
    st.markdown("---")
    st.markdown("#### 請輸入家庭成員數")
    has_spouse: bool = st.checkbox("是否有配偶（扣除額 553 萬）", value=False)
    adult_children_input: int = st.number_input("直系血親卑親屬數（每人 56 萬）", min_value=0, max_value=10,
                                                 value=0, help="請輸入直系血親或卑親屬人數")
    parents_input: int = st.number_input("父母數（每人 138 萬，最多 2 人）", min_value=0, max_value=2,
                                          value=0, help="請輸入父母人數")
    max_disabled: int = (1 if has_spouse else 0) + adult_children_input + parents_input
    disabled_people_input: int = st.number_input("重度以上身心障礙者數（每人 693 萬）", min_value=0, max_value=max_disabled,
                                                 value=0, help="請輸入重度以上身心障礙者人數")
    other_dependents_input: int = st.number_input("受撫養之兄弟姊妹、祖父母數（每人 56 萬）", min_value=0, max_value=5,
                                                  value=0, help="請輸入兄弟姊妹或祖父母人數")

taxable_amount, tax_due, total_deductions = calculate_estate_tax(
    total_assets_input, has_spouse, adult_children_input,
    other_dependents_input, disabled_people_input, parents_input
)

st.markdown(f"<h3>預估遺產稅：{tax_due:,.0f} 萬元</h3>", unsafe_allow_html=True)

col1, col2, col3 = st.columns(3)
with col1:
    st.markdown("**資產概況**")
    df_assets = pd.DataFrame({"項目": ["總資產"], "金額（萬）": [int(total_assets_input)]})
    st.table(df_assets)
with col2:
    st.markdown("**扣除項目**")
    df_deductions = pd.DataFrame({
        "項目": ["免稅額", "喪葬費扣除額", "配偶扣除額", "直系血親卑親屬扣除額", "父母扣除額", "重度身心障礙扣除額", "其他撫養扣除額"],
        "金額（萬）": [
            EXEMPT_AMOUNT,
            FUNERAL_EXPENSE,
            SPOUSE_DEDUCTION_VALUE if has_spouse else 0,
            adult_children_input * ADULT_CHILD_DEDUCTION,
            parents_input * PARENTS_DEDUCTION,
            disabled_people_input * DISABLED_DEDUCTION,
            other_dependents_input * OTHER_DEPENDENTS_DEDUCTION
        ]
    })
    df_deductions["金額（萬）"] = df_deductions["金額（萬）"].astype(int)
    st.table(df_deductions)
with col3:
    st.markdown("**稅務計算**")
    df_tax = pd.DataFrame({
        "項目": ["課稅遺產淨額", "預估遺產稅"],
        "金額（萬）": [int(taxable_amount), int(tax_due)]
    })
    st.table(df_tax)

st.markdown("---")
st.markdown("## 家族傳承策略建議")
st.markdown("""
1. 規劃保單：透過保險預留稅源。  
2. 提前贈與：利用免稅贈與逐年轉移財富。  
3. 分散配置：透過合理資產配置降低稅負。
""")

# ===============================
# 6. 保護區：模擬試算與效益評估（僅限授權使用者）
# ===============================
st.markdown("---")
st.markdown("## 模擬試算與效益評估 (僅限授權使用者)")

login_container = st.empty()

if not st.session_state.get("authenticated", False):
    with login_container.form("login_form"):
        st.markdown("請先登入以檢視此區域內容。")
        login_username = st.text_input("帳號", key="login_form_username")
        login_password = st.text_input("密碼", type="password", key="login_form_password")
        submitted = st.form_submit_button("登入")
        if submitted:
            valid, user_name = check_credentials(login_username, login_password)
            if valid:
                st.session_state.authenticated = True
                st.session_state.user_name = user_name
                success_container = st.empty()
                success_container.success(f"登入成功！歡迎 {user_name}")
                time.sleep(1)
                success_container.empty()
                login_container.empty()
            else:
                st.session_state.authenticated = False

if st.session_state.get("authenticated", False):
    st.markdown("請檢視下方的模擬試算與效益評估結果")
    
    # 案例參數設定
    CASE_TOTAL_ASSETS: float = total_assets_input  
    CASE_SPOUSE: bool = has_spouse
    CASE_ADULT_CHILDREN: int = adult_children_input
    CASE_PARENTS: int = parents_input
    CASE_DISABLED: int = disabled_people_input
    CASE_OTHER: int = other_dependents_input

    # 保費預設：直接等於預估遺產稅，向上取整到十萬位，若超過總資產則取總資產
    default_premium: int = int(math.ceil(tax_due / 10) * 10)
    if default_premium > CASE_TOTAL_ASSETS:
        default_premium = int(CASE_TOTAL_ASSETS)
    premium_val: int = default_premium

    # 理賠金預設：保費的 1.5 倍
    default_claim: int = int(premium_val * 1.5)

    # 贈與金額預設：若剩餘資產 (總資產 - 保費) 大於等於 244 萬，則預設為 244 萬；否則為 0
    remaining: int = int(CASE_TOTAL_ASSETS - premium_val)
    default_gift: int = 244 if remaining >= 244 else 0

    premium_case: int = st.number_input("購買保險保費（萬）",
                                   min_value=0,
                                   max_value=int(CASE_TOTAL_ASSETS),
                                   value=premium_val,
                                   step=100,
                                   key="premium_case",
                                   format="%d")
    claim_case: int = st.number_input("保險理賠金（萬）",
                                 min_value=0,
                                 max_value=100000,
                                 value=default_claim,
                                 step=100,
                                 key="claim_case",
                                 format="%d")
    gift_case: int = st.number_input("提前贈與金額（萬）",
                                min_value=0,
                                max_value=int(CASE_TOTAL_ASSETS - premium_case),
                                value=min(default_gift, int(CASE_TOTAL_ASSETS - premium_case)),
                                step=100,
                                key="case_gift",
                                format="%d")

    if premium_case > CASE_TOTAL_ASSETS:
        st.error("錯誤：保費不得高於總資產！")
    if gift_case > CASE_TOTAL_ASSETS - premium_case:
        st.error("錯誤：提前贈與金額不得高於【總資產】-【保費】！")

    # 無規劃案例計算
    _, tax_case_no_plan, _ = calculate_estate_tax(
        CASE_TOTAL_ASSETS,
        CASE_SPOUSE,
        CASE_ADULT_CHILDREN,
        CASE_OTHER,
        CASE_DISABLED,
        CASE_PARENTS
    )
    net_case_no_plan = CASE_TOTAL_ASSETS - tax_case_no_plan

    # 贈與策略計算
    effective_case_gift = CASE_TOTAL_ASSETS - gift_case
    _, tax_case_gift, _ = calculate_estate_tax(
        effective_case_gift,
        CASE_SPOUSE,
        CASE_ADULT_CHILDREN,
        CASE_OTHER,
        CASE_DISABLED,
        CASE_PARENTS
    )
    net_case_gift = effective_case_gift - tax_case_gift + gift_case

    # 保單策略計算
    effective_case_insurance = CASE_TOTAL_ASSETS - premium_case
    _, tax_case_insurance, _ = calculate_estate_tax(
        effective_case_insurance,
        CASE_SPOUSE,
        CASE_ADULT_CHILDREN,
        CASE_OTHER,
        CASE_DISABLED,
        CASE_PARENTS
    )
    net_case_insurance = effective_case_insurance - tax_case_insurance + claim_case

    # 組合策略計算：提前贈與＋保單（未被實質課稅）
    effective_case_combo_not_tax = CASE_TOTAL_ASSETS - gift_case - premium_case
    _, tax_case_combo_not_tax, _ = calculate_estate_tax(
        effective_case_combo_not_tax,
        CASE_SPOUSE,
        CASE_ADULT_CHILDREN,
        CASE_OTHER,
        CASE_DISABLED,
        CASE_PARENTS
    )
    net_case_combo_not_tax = effective_case_combo_not_tax - tax_case_combo_not_tax + claim_case + gift_case

    # 組合策略計算：提前贈與＋保單（被實質課稅）
    effective_case_combo_tax = CASE_TOTAL_ASSETS - gift_case - premium_case + claim_case
    _, tax_case_combo_tax, _ = calculate_estate_tax(
        effective_case_combo_tax,
        CASE_SPOUSE,
        CASE_ADULT_CHILDREN,
        CASE_OTHER,
        CASE_DISABLED,
        CASE_PARENTS
    )
    net_case_combo_tax = effective_case_combo_tax - tax_case_combo_tax + gift_case

    # 建構模擬結果 DataFrame
    case_data = {
        "規劃策略": [
            "沒有規劃",
            "提前贈與",
            "購買保險",
            "提前贈與＋購買保險",
            "提前贈與＋購買保險（被實質課稅）"
        ],
        "遺產稅（萬）": [
            int(tax_case_no_plan),
            int(tax_case_gift),
            int(tax_case_insurance),
            int(tax_case_combo_not_tax),
            int(tax_case_combo_tax)
        ],
        "家人總共取得（萬）": [
            int(net_case_no_plan),
            int(net_case_gift),
            int(net_case_insurance),
            int(net_case_combo_not_tax),
            int(net_case_combo_tax)
        ]
    }
    df_case_results = pd.DataFrame(case_data)
    baseline_value = df_case_results.loc[df_case_results["規劃策略"] == "沒有規劃", "家人總共取得（萬）"].iloc[0]
    df_case_results["規劃效益"] = df_case_results["家人總共取得（萬）"] - baseline_value

    st.markdown("### 案例模擬結果")
    family_status = ""
    if CASE_SPOUSE:
        family_status += "配偶, "
    family_status += f"子女{CASE_ADULT_CHILDREN}人, 父母{CASE_PARENTS}人, 重度身心障礙者{CASE_DISABLED}人, 其他撫養{CASE_OTHER}人"
    st.markdown(f"**總資產：{int(CASE_TOTAL_ASSETS):,d} 萬**  |  **家庭狀況：{family_status}**")
    st.table(df_case_results)

    # 畫圖：不同策略下家人總共取得金額比較
    plot_strategy_comparison(df_case_results)

# ===============================
# 7. 行銷資訊（所有人皆可檢視）
# ===============================
st.markdown("---")
st.markdown("### 想了解更多？")
st.markdown("歡迎前往 **永傳家族辦公室**，我們提供專業的家族傳承與財富規劃服務。")
st.markdown("[點此前往官網](https://www.gracefo.com)", unsafe_allow_html=True)
