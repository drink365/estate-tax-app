import streamlit as st
import pandas as pd
import math
import plotly.express as px
from datetime import datetime
from dataclasses import dataclass, field
from typing import Tuple, Dict, Any, List


# ===============================
# 1. 常數與設定
# ===============================
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
            (float("inf"), 0.2),
        ]
    )


# ===============================
# 2. 計算邏輯
# ===============================
class EstateTaxCalculator:
    def __init__(self, constants: TaxConstants):
        self.constants = constants

    def compute_deductions(
        self, spouse: bool, adult_children: int, other_dependents: int,
        disabled_people: int, parents: int
    ) -> float:
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
    def calculate_estate_tax(
        _self, total_assets: float, spouse: bool, adult_children: int,
        other_dependents: int, disabled_people: int, parents: int
    ) -> Tuple[float, float, float]:
        deductions = _self.compute_deductions(
            spouse, adult_children, other_dependents, disabled_people, parents
        )
        if total_assets < _self.constants.EXEMPT_AMOUNT + deductions:
            return 0, 0, deductions
        taxable_amount = max(0, total_assets - _self.constants.EXEMPT_AMOUNT - deductions)
        tax_due = 0.0
        prev_bracket = 0
        for bracket, rate in _self.constants.TAX_BRACKETS:
            if taxable_amount > prev_bracket:
                taxable_at_rate = min(taxable_amount, bracket) - prev_bracket
                tax_due += taxable_at_rate * rate
                prev_bracket = bracket
        return taxable_amount, round(tax_due, 0), deductions


# ===============================
# 3. Streamlit 介面
# ===============================
def run_estate():
    st.markdown("<h2 style='text-align:center;'>AI 秒算遺產稅</h2>", unsafe_allow_html=True)

    constants = TaxConstants()
    calculator = EstateTaxCalculator(constants)

    # Step 1: 選擇地區
    st.selectbox("選擇適用地區", ["台灣（2025年起）"], index=0)

    # Step 2: 輸入資產
    st.markdown("### 請輸入資產資訊")
    total_assets_input = st.number_input(
        "總資產（萬）", min_value=1000, max_value=100000,
        value=5000, step=100, help="請輸入您的總資產（單位：萬）"
    )

    # Step 3: 輸入家庭成員
    st.markdown("### 請輸入家庭成員數")
    has_spouse = st.checkbox("是否有配偶（扣除額 553 萬）", value=False)
    adult_children_input = st.number_input("直系血親卑親屬數（每人 56 萬）", 0, 10, 0)
    parents_input = st.number_input("父母數（每人 138 萬，最多 2 人）", 0, 2, 0)
    max_disabled = (1 if has_spouse else 0) + adult_children_input + parents_input
    disabled_people_input = st.number_input("重度以上身心障礙者數（每人 693 萬）", 0, max_disabled, 0)
    other_dependents_input = st.number_input("受撫養之兄弟姊妹、祖父母數（每人 56 萬）", 0, 5, 0)

    # 計算遺產稅
    try:
        taxable_amount, tax_due, total_deductions = calculator.calculate_estate_tax(
            total_assets_input, has_spouse, adult_children_input,
            other_dependents_input, disabled_people_input, parents_input
        )
    except Exception as e:
        st.error(f"計算時發生錯誤：{e}")
        return

    st.markdown(f"## 預估遺產稅：{int(tax_due):,} 萬元")

    # =============================
    # 策略模擬試算
    # =============================
    st.markdown("---")
    st.markdown("## 策略模擬與效益評估")

    gift_case = st.number_input("提前贈與金額（萬）", 0, total_assets_input, 0, step=100)
    premium_case = st.number_input("購買保險保費（萬）", 0, total_assets_input, 0, step=100)
    claim_case = st.number_input("保險理賠金（萬）", 0, 100000, 0, step=100)

    # 策略計算
    _, tax_no_plan, _ = calculator.calculate_estate_tax(
        total_assets_input, has_spouse, adult_children_input,
        other_dependents_input, disabled_people_input, parents_input
    )
    net_no_plan = total_assets_input - tax_no_plan

    effective_case_gift = total_assets_input - gift_case
    _, tax_case_gift, _ = calculator.calculate_estate_tax(
        effective_case_gift, has_spouse, adult_children_input,
        other_dependents_input, disabled_people_input, parents_input
    )
    net_case_gift = effective_case_gift - tax_case_gift + gift_case

    effective_case_insurance = total_assets_input - premium_case
    _, tax_case_insurance, _ = calculator.calculate_estate_tax(
        effective_case_insurance, has_spouse, adult_children_input,
        other_dependents_input, disabled_people_input, parents_input
    )
    net_case_insurance = effective_case_insurance - tax_case_insurance + claim_case

    # 規劃結果表
    case_data = {
        "策略": ["沒有規劃", "提前贈與", "購買保險"],
        "遺產稅（萬）": [int(tax_no_plan), int(tax_case_gift), int(tax_case_insurance)],
        "家人總共取得（萬）": [int(net_no_plan), int(net_case_gift), int(net_case_insurance)],
    }
    df_case_results = pd.DataFrame(case_data)
    baseline_value = df_case_results.loc[
        df_case_results["策略"] == "沒有規劃", "家人總共取得（萬）"
    ].iloc[0]
    df_case_results["規劃效益"] = df_case_results["家人總共取得（萬）"] - baseline_value

    st.table(df_case_results)

    # 視覺化圖表
    fig_bar = px.bar(
        df_case_results,
        x="策略",
        y="家人總共取得（萬）",
        text="家人總共取得（萬）",
        title="不同策略下家人總共取得金額比較",
    )
    fig_bar.update_traces(texttemplate="%{text:.0f}", textposition="outside", marker_color="#2a9d8f")
    fig_bar.update_layout(
        yaxis_range=[0, df_case_results["家人總共取得（萬）"].max() * 1.3],
        font=dict(size=18, color="black"),
        title_font=dict(size=22, color="black"),
        width=None,
        height=600,
    )
    st.plotly_chart(fig_bar, config={"responsive": True}, width="stretch")
