import streamlit as st
import pandas as pd
import math
import plotly.express as px
from typing import Tuple, Dict, Any, List
from datetime import datetime
import time
from dataclasses import dataclass, field


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
            (float('inf'), 0.2)
        ]
    )


# ===============================
# 2. 稅務計算邏輯
# ===============================
class EstateTaxCalculator:
    """遺產稅計算器"""

    def __init__(self, constants: TaxConstants):
        self.constants = constants

    def compute_deductions(self, spouse: bool, adult_children: int, other_dependents: int,
                           disabled_people: int, parents: int) -> float:
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


# ===============================
# 3. Streamlit 介面
# ===============================
class EstateTaxUI:
    """介面"""

    def __init__(self, calculator: EstateTaxCalculator):
        self.calculator = calculator

    def render_ui(self):
        st.set_page_config(page_title="AI秒算遺產稅", layout="wide")
        st.markdown("<h1 style='text-align: center;'>AI秒算遺產稅</h1>", unsafe_allow_html=True)
        st.selectbox("選擇適用地區", ["台灣（2025年起）"], index=0)

        # ---------------- 資產輸入 ----------------
        st.markdown("## 請輸入資產資訊")
        total_assets_input = st.number_input("總資產（萬）", min_value=1000, max_value=100000, value=5000, step=100)

        # ---------------- 家庭成員輸入 ----------------
        st.markdown("## 請輸入家庭成員數")
        has_spouse = st.checkbox("是否有配偶（扣除額 553 萬）", value=False)
        adult_children_input = st.number_input("直系血親卑親屬數（每人 56 萬）", min_value=0, max_value=10, value=0)
        parents_input = st.number_input("父母數（每人 138 萬，最多 2 人）", min_value=0, max_value=2, value=0)
        disabled_people_input = st.number_input("重度以上身心障礙者數（每人 693 萬）", min_value=0, max_value=10, value=0)
        other_dependents_input = st.number_input("受撫養之兄弟姊妹、祖父母數（每人 56 萬）", min_value=0, max_value=5, value=0)

        try:
            taxable_amount, tax_due, _ = self.calculator.calculate_estate_tax(
                total_assets_input, has_spouse, adult_children_input,
                other_dependents_input, disabled_people_input, parents_input
            )
        except Exception as e:
            st.error(f"計算遺產稅時發生錯誤：{e}")
            return

        st.markdown(f"## 預估遺產稅：{tax_due:,.0f} 萬元")


# ===============================
# 4. 包裝成 run_estate()
# ===============================
def run_estate():
    constants = TaxConstants()
    calculator = EstateTaxCalculator(constants)
    ui = EstateTaxUI(calculator)
    ui.render_ui()
