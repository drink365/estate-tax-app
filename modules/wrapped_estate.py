
# modules/wrapped_estate.py — 模組一：AI秒算遺產稅（依使用者原始邏輯還原；移除內部登入畫面）
import streamlit as st
import pandas as pd
import math
import plotly.express as px
from typing import Tuple, Dict, Any, List
from dataclasses import dataclass, field

# =============== 常數與設定 ===============
@dataclass
class TaxConstants:
    """遺產稅相關常數"""
    EXEMPT_AMOUNT: float = 1333  # 免稅額
    FUNERAL_EXPENSE: float = 138  # 喪葬費扣除額
    SPOUSE_DEDUCTION_VALUE: float = 553  # 配偶扣除額
    ADULT_CHILD_DEDUCTION: float = 56  # 每位子女扣除額
    PARENTS_DEDUCTION: float = 138  # 父母扣除額
    DISABLED_DEDUCTION: float = 693  # 重度身心障礙扣除額
    OTHER_DEPENDENTS_DEDUCTION: float = 56  # 其他撫養扣除額
    TAX_BRACKETS: List[Tuple[float, float]] = field(
        default_factory=lambda: [
            (5621, 0.1),
            (11242, 0.15),
            (float('inf'), 0.2)
        ]
    )

# =============== 稅務計算邏輯 ===============
class EstateTaxCalculator:
    """遺產稅計算器"""

    def __init__(self, constants: TaxConstants):
        self.constants = constants

    def compute_deductions(self, spouse: bool, adult_children: int, other_dependents: int,
                           disabled_people: int, parents: int) -> float:
        """計算總扣除額"""
        spouse_deduction = self.constants.SPOUSE_DEDUCTION_VALUE if spouse else 0
        total_deductions = (
            spouse_deduction +
            self.constants.FUNERAL_EXPENSE +
            (disabled_people * self.constants.DISABLED_DEDUCTION) +
            (adult_children * self.constants.ADULT_CHILD_DEDUCTION) +
            (other_dependents * self.constants.OTHER_DEPENDENTS_DEDUCTION) +
            (parents * self.constants.PARENTS_DEDUCTION)
        )
        return total_deductions

    @st.cache_data
    def calculate_estate_tax(_self, total_assets: float, spouse: bool, adult_children: int,
                             other_dependents: int, disabled_people: int, parents: int) -> Tuple[float, float, float]:
        """計算遺產稅"""
        deductions = _self.compute_deductions(spouse, adult_children, other_dependents, disabled_people, parents)
        if total_assets < _self.constants.EXEMPT_AMOUNT + deductions:
            return 0, 0, deductions
        taxable_amount = max(0, total_assets - _self.constants.EXEMPT_AMOUNT - deductions)
        tax_due = 0.0
        previous_bracket = 0
        for bracket, rate in _self.constants.TAX_BRACKETS:
            if taxable_amount > previous_bracket:
                taxable_at_rate = min(taxable_amount, bracket) - previous_bracket
                tax_due += taxable_at_rate * rate
                previous_bracket = bracket
        return taxable_amount, round(tax_due, 0), deductions

# =============== 顯示輔助：安全表格格式化（不改變原計算） ===============
def _fmt_table_stable(df: pd.DataFrame) -> pd.DataFrame:
    out = pd.DataFrame(index=df.index)
    for col in df.columns:
        s = df[col]
        s_num = pd.to_numeric(s, errors="coerce")
        if s_num.notna().mean() >= 0.5:
            out[col] = s_num.map(lambda x: f"{int(x):,}" if pd.notna(x) else "—")
        else:
            out[col] = s.map(lambda x: "—" if pd.isna(x) else str(x))
    return out

# =============== 介面（已移除內部登入區） ===============
class EstateTaxUI:
    """介面"""
    def __init__(self, calculator: EstateTaxCalculator):
        self.calculator = calculator

    def render_ui(self):
        # 頁面 CSS（set_page_config 在 app.py 已設定）
        st.markdown(
            """
            <style>
            body p, body span, body label, body input, body textarea, body select, body button, body li, body a {
                font-size: 1.5em !important;
            }
            h1.main-header { font-size: 2.7em !important; text-align: center; color: #000000 !important; }
            h2 { color: #28a745 !important; }  h3 { color: #fd7e14 !important; }
            </style>
            """,
            unsafe_allow_html=True
        )

        st.markdown("<h1 class='main-header'>AI秒算遺產稅</h1>", unsafe_allow_html=True)
        st.selectbox("選擇適用地區", ["台灣（2025年起）"], index=0)

        # ---- 基本輸入 ----
        with st.container():
            st.markdown("## 請輸入資產及家庭資訊")
            total_assets_input = st.number_input(
                "總資產（萬）", min_value=1000, max_value=100000,
                value=5000, step=100, help="請輸入您的總資產（單位：萬）"
            )
            st.markdown("---")
            st.markdown("### 請輸入家庭成員數")
            has_spouse = st.checkbox("是否有配偶（扣除額 553 萬）", value=False)
            adult_children_input = st.number_input(
                "直系血親卑親屬數（每人 56 萬）", min_value=0, max_value=10,
                value=0, help="請輸入直系血親或卑親屬人數"
            )
            parents_input = st.number_input(
                "父母數（每人 138 萬，最多 2 人）", min_value=0, max_value=2,
                value=0, help="請輸入父母人數"
            )
            max_disabled = (1 if has_spouse else 0) + adult_children_input + parents_input
            disabled_people_input = st.number_input(
                "重度以上身心障礙者數（每人 693 萬）", min_value=0, max_value=max_disabled,
                value=0, help="請輸入重度以上身心障礙者人數"
            )
            other_dependents_input = st.number_input(
                "受撫養之兄弟姊妹、祖父母數（每人 56 萬）", min_value=0, max_value=5,
                value=0, help="請輸入兄弟姊妹或祖父母人數"
            )

        # ---- 計算 ----
        taxable_amount, tax_due, total_deductions = self.calculator.calculate_estate_tax(
            total_assets_input, has_spouse, adult_children_input,
            other_dependents_input, disabled_people_input, parents_input
        )

        # ---- 結果：預估遺產稅 & 三欄表 ----
        st.markdown("## 預估遺產稅：{0:,.0f} 萬元".format(tax_due), unsafe_allow_html=True)

        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown("**資產概況**")
            df_assets = pd.DataFrame({"項目": ["總資產"], "金額（萬）": [int(total_assets_input)]}).set_index("項目")
            st.table(_fmt_table_stable(df_assets))
        with col2:
            st.markdown("**扣除項目**")
            df_deductions = pd.DataFrame({
                "項目": [
                    "免稅額", "喪葬費扣除額", "配偶扣除額",
                    "直系血親卑親屬扣除額", "父母扣除額",
                    "重度身心障礙扣除額", "其他撫養扣除額"
                ],
                "金額（萬）": [
                    self.calculator.constants.EXEMPT_AMOUNT,
                    self.calculator.constants.FUNERAL_EXPENSE,
                    self.calculator.constants.SPOUSE_DEDUCTION_VALUE if has_spouse else 0,
                    adult_children_input * self.calculator.constants.ADULT_CHILD_DEDUCTION,
                    parents_input * self.calculator.constants.PARENTS_DEDUCTION,
                    disabled_people_input * self.calculator.constants.DISABLED_DEDUCTION,
                    other_dependents_input * self.calculator.constants.OTHER_DEPENDENTS_DEDUCTION
                ]
            }).set_index("項目")
            st.table(_fmt_table_stable(df_deductions))
        with col3:
            st.markdown("**稅務計算**")
            df_tax = pd.DataFrame({
                "項目": ["課稅遺產淨額", "預估遺產稅"],
                "金額（萬）": [int(taxable_amount), int(tax_due)]
            }).set_index("項目")
            st.table(_fmt_table_stable(df_tax))

        # ---- 直接顯示模擬區（外層已登入） ----
        st.markdown("---")
        st.markdown("## 模擬試算與效益評估")

        CASE_TOTAL_ASSETS = total_assets_input
        CASE_SPOUSE = has_spouse
        CASE_ADULT_CHILDREN = adult_children_input
        CASE_PARENTS = parents_input
        CASE_DISABLED = disabled_people_input
        CASE_OTHER = other_dependents_input

        default_premium = int(math.ceil(tax_due / 10) * 10)
        if default_premium > CASE_TOTAL_ASSETS:
            default_premium = CASE_TOTAL_ASSETS
        premium_val = default_premium
        default_claim = int(premium_val * 1.5)
        remaining = CASE_TOTAL_ASSETS - premium_val
        default_gift = 244 if remaining >= 244 else 0

        premium_case = st.number_input(
            "購買保險保費（萬）", min_value=0, max_value=CASE_TOTAL_ASSETS,
            value=premium_val, step=100, key="premium_case", format="%d"
        )
        claim_case = st.number_input(
            "保險理賠金（萬）", min_value=0, max_value=100000,
            value=default_claim, step=100, key="claim_case", format="%d"
        )
        gift_case = st.number_input(
            "提前贈與金額（萬）", min_value=0, max_value=CASE_TOTAL_ASSETS - premium_case,
            value=min(default_gift, CASE_TOTAL_ASSETS - premium_case),
            step=100, key="case_gift", format="%d"
        )

        if premium_case > CASE_TOTAL_ASSETS:
            st.error("錯誤：保費不得高於總資產！")
        if gift_case > CASE_TOTAL_ASSETS - premium_case:
            st.error("錯誤：提前贈與金額不得高於【總資產】-【保費】！")

        # 各策略稅額與家人取得
        def _calc(total):
            _, t, _ = self.calculator.calculate_estate_tax(
                total, CASE_SPOUSE, CASE_ADULT_CHILDREN, CASE_OTHER, CASE_DISABLED, CASE_PARENTS
            ); return t

        tax_case_no_plan = _calc(CASE_TOTAL_ASSETS)
        net_case_no_plan = CASE_TOTAL_ASSETS - tax_case_no_plan

        effective_case_gift = CASE_TOTAL_ASSETS - gift_case
        tax_case_gift = _calc(effective_case_gift)
        net_case_gift = effective_case_gift - tax_case_gift + gift_case

        effective_case_insurance = CASE_TOTAL_ASSETS - premium_case
        tax_case_insurance = _calc(effective_case_insurance)
        net_case_insurance = effective_case_insurance - tax_case_insurance + claim_case

        effective_case_combo_not_tax = CASE_TOTAL_ASSETS - gift_case - premium_case
        tax_case_combo_not_tax = _calc(effective_case_combo_not_tax)
        net_case_combo_not_tax = effective_case_combo_not_tax - tax_case_combo_not_tax + claim_case + gift_case

        effective_case_combo_tax = CASE_TOTAL_ASSETS - gift_case - premium_case + claim_case
        tax_case_combo_tax = _calc(effective_case_combo_tax)
        net_case_combo_tax = effective_case_combo_tax - tax_case_combo_tax + gift_case

        case_data = {
            "規劃策略": [
                "沒有規劃", "提前贈與", "購買保險",
                "提前贈與＋購買保險", "提前贈與＋購買保險（被實質課稅）"
            ],
            "遺產稅（萬）": list(map(int, [
                tax_case_no_plan, tax_case_gift, tax_case_insurance, tax_case_combo_not_tax, tax_case_combo_tax
            ])),
            "家人總共取得（萬）": list(map(int, [
                net_case_no_plan, net_case_gift, net_case_insurance, net_case_combo_not_tax, net_case_combo_tax
            ]))
        }
        df_case_results = pd.DataFrame(case_data)
        baseline_value = df_case_results.loc[
            df_case_results["規劃策略"] == "沒有規劃", "家人總共取得（萬）"
        ].iloc[0]
        df_case_results["規劃效益"] = df_case_results["家人總共取得（萬）"] - baseline_value

        st.markdown("### 案例模擬結果")
        family_status = ("配偶, " if CASE_SPOUSE else "") + \
            f"子女{CASE_ADULT_CHILDREN}人, 父母{CASE_PARENTS}人, 重度身心障礙者{CASE_DISABLED}人, 其他撫養{CASE_OTHER}人"
        st.markdown(f"**總資產：{int(CASE_TOTAL_ASSETS):,d} 萬**  |  **家庭狀況：{family_status}**")

        # 顯示表格（安全格式化）
        st.table(_fmt_table_stable(df_case_results.set_index('規劃策略')))

def run_estate():
    constants = TaxConstants()
    calculator = EstateTaxCalculator(constants)
    ui = EstateTaxUI(calculator)
    ui.render_ui()
