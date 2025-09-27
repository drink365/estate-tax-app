# modules/wrapped_estate.py — 模組一：AI秒算遺產稅（保費×1.5 自動同步理賠金）
import streamlit as st
import pandas as pd
import math
from typing import Tuple, List
from dataclasses import dataclass, field

@dataclass
class TaxConstants:
    EXEMPT_AMOUNT: float = 1333
    FUNERAL_EXPENSE: float = 138
    SPOUSE_DEDUCTION_VALUE: float = 553
    ADULT_CHILD_DEDUCTION: float = 56
    PARENTS_DEDUCTION: float = 138
    DISABLED_DEDUCTION: float = 693
    OTHER_DEPENDENTS_DEDUCTION: float = 56
    TAX_BRACKETS: List[Tuple[float, float]] = field(
        default_factory=lambda: [(5621, 0.10),(11242, 0.15),(float("inf"), 0.20)]
    )

class EstateTaxCalculator:
    def __init__(self, constants: TaxConstants):
        self.constants = constants

    def compute_deductions(self, spouse: bool, adult_children: int, other_dependents: int,
                           disabled_people: int, parents: int) -> float:
        spouse_deduction = self.constants.SPOUSE_DEDUCTION_VALUE if spouse else 0
        return (
            spouse_deduction + self.constants.FUNERAL_EXPENSE +
            disabled_people * self.constants.DISABLED_DEDUCTION +
            adult_children * self.constants.ADULT_CHILD_DEDUCTION +
            other_dependents * self.constants.OTHER_DEPENDENTS_DEDUCTION +
            parents * self.constants.PARENTS_DEDUCTION
        )

    @st.cache_data
    def calculate_estate_tax(_self, total_assets: float, spouse: bool, adult_children: int,
                             other_dependents: int, disabled_people: int, parents: int):
        deductions = _self.compute_deductions(spouse, adult_children, other_dependents, disabled_people, parents)
        if total_assets < _self.constants.EXEMPT_AMOUNT + deductions:
            return 0, 0, deductions
        taxable_amount = max(0, total_assets - _self.constants.EXEMPT_AMOUNT - deductions)
        tax_due = 0.0
        previous = 0
        for bracket, rate in _self.constants.TAX_BRACKETS:
            if taxable_amount > previous:
                taxable_at = min(taxable_amount, bracket) - previous
                tax_due += taxable_at * rate
                previous = bracket
        return taxable_amount, round(tax_due, 0), deductions

def _fmt_table(df: pd.DataFrame) -> pd.DataFrame:
    out = pd.DataFrame(index=df.index)
    for col in df.columns:
        s = df[col]
        s_num = pd.to_numeric(s, errors="coerce")
        if s_num.notna().mean() >= 0.5:
            out[col] = s_num.map(lambda x: f"{int(x):,}" if pd.notna(x) else "—")
        else:
            out[col] = s.map(lambda x: "—" if pd.isna(x) else str(x))
    return out

class EstateTaxUI:
    def __init__(self, calculator: EstateTaxCalculator):
        self.calculator = calculator

    def render_ui(self):
        st.markdown("<h1 class='main-header'>AI秒算遺產稅</h1>", unsafe_allow_html=True)
        st.selectbox("選擇適用地區", ["台灣（2025年起）"], index=0)

        with st.container():
            st.markdown("## 請輸入資產及家庭資訊")
            total_assets_input = st.number_input("總資產（萬）", min_value=1000, max_value=100000, value=5000, step=100)
            st.markdown("---")
            has_spouse = st.checkbox("是否有配偶（扣除額 553 萬）", value=False)
            adult_children_input = st.number_input("直系血親卑親屬數（每人 56 萬）", min_value=0, max_value=10, value=0)
            parents_input = st.number_input("父母數（每人 138 萬，最多 2 人）", min_value=0, max_value=2, value=0)
            max_disabled = (1 if has_spouse else 0) + adult_children_input + parents_input
            disabled_people_input = st.number_input("重度以上身心障礙者數（每人 693 萬）", min_value=0, max_value=max_disabled, value=0)
            other_dependents_input = st.number_input("受撫養之兄弟姊妹、祖父母數（每人 56 萬）", min_value=0, max_value=5, value=0)

        taxable_amount, tax_due, _ = self.calculator.calculate_estate_tax(
            total_assets_input, has_spouse, adult_children_input, other_dependents_input, disabled_people_input, parents_input
        )
        st.markdown(f"## 預估遺產稅：{tax_due:,.0f} 萬元")

        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown("**資產概況**")
            st.table(_fmt_table(pd.DataFrame({"金額（萬）":[int(total_assets_input)]}, index=["總資產"])))
        with c2:
            st.markdown("**扣除項目**")
            df_d = pd.DataFrame({
                "金額（萬）":[
                    self.calculator.constants.EXEMPT_AMOUNT,
                    self.calculator.constants.FUNERAL_EXPENSE,
                    self.calculator.constants.SPOUSE_DEDUCTION_VALUE if has_spouse else 0,
                    adult_children_input * self.calculator.constants.ADULT_CHILD_DEDUCTION,
                    parents_input * self.calculator.constants.PARENTS_DEDUCTION,
                    disabled_people_input * self.calculator.constants.DISABLED_DEDUCTION,
                    other_dependents_input * self.calculator.constants.OTHER_DEPENDENTS_DEDUCTION
                ]
            }, index=["免稅額","喪葬費扣除額","配偶扣除額","直系血親卑親屬扣除額","父母扣除額","重度身心障礙扣除額","其他撫養扣除額"])
            st.table(_fmt_table(df_d))
        with c3:
            st.markdown("**稅務計算**")
            st.table(_fmt_table(pd.DataFrame({"金額（萬）":[int(taxable_amount), int(tax_due)]}, index=["課稅遺產淨額","預估遺產稅"])))

        # 模擬：保費改變→自動把理賠金 = 保費×1.5（除非使用者手動改過理賠金）
        st.markdown("---"); st.markdown("## 模擬試算與效益評估")
        CASE_TOTAL_ASSETS = total_assets_input
        CASE_SPOUSE = has_spouse
        CASE_ADULT_CHILDREN = adult_children_input
        CASE_PARENTS = parents_input
        CASE_DISABLED = disabled_people_input
        CASE_OTHER = other_dependents_input

        default_premium = int(math.ceil(tax_due / 10) * 10)
        if default_premium > CASE_TOTAL_ASSETS:
            default_premium = CASE_TOTAL_ASSETS
        default_claim = int(default_premium * 1.5)

        basis = int(default_premium)
        if "premium_basis" not in st.session_state: st.session_state.premium_basis = basis
        if st.session_state.premium_basis != basis and not st.session_state.get("claim_locked", False):
            st.session_state["premium_case"] = default_premium
            st.session_state["claim_case"] = default_claim
            st.session_state.premium_basis = basis
        if "premium_case" not in st.session_state: st.session_state["premium_case"] = default_premium
        if "claim_case" not in st.session_state: st.session_state["claim_case"] = default_claim

        def _sync_claim_from_premium():
            if not st.session_state.get("claim_locked", False):
                st.session_state["claim_case"] = int(st.session_state["premium_case"] * 1.5)

        def _lock_claim(): st.session_state["claim_locked"] = True

        premium_case = st.number_input("購買保險保費（萬）", min_value=0, max_value=CASE_TOTAL_ASSETS,
                                       value=st.session_state["premium_case"], step=100, key="premium_case", format="%d",
                                       on_change=_sync_claim_from_premium)

        claim_case = st.number_input("保險理賠金（萬）", min_value=0, max_value=100000,
                                     value=st.session_state["claim_case"], step=100, key="claim_case", format="%d",
                                     on_change=_lock_claim)

        remaining = CASE_TOTAL_ASSETS - premium_case
        default_gift = 244 if remaining >= 244 else 0
        gift_case = st.number_input("提前贈與金額（萬）", min_value=0, max_value=CASE_TOTAL_ASSETS - premium_case,
                                    value=min(default_gift, CASE_TOTAL_ASSETS - premium_case), step=100, key="case_gift", format="%d")

        if premium_case > CASE_TOTAL_ASSETS: st.error("錯誤：保費不得高於總資產！")
        if gift_case > CASE_TOTAL_ASSETS - premium_case: st.error("錯誤：提前贈與金額不得高於【總資產】-【保費】！")

        def _calc(total):
            _, t, _ = self.calculator.calculate_estate_tax(total, CASE_SPOUSE, CASE_ADULT_CHILDREN, CASE_OTHER, CASE_DISABLED, CASE_PARENTS)
            return t

        tax_case_no_plan = _calc(CASE_TOTAL_ASSETS); net_case_no_plan = CASE_TOTAL_ASSETS - tax_case_no_plan
        effective_case_gift = CASE_TOTAL_ASSETS - gift_case; tax_case_gift = _calc(effective_case_gift); net_case_gift = effective_case_gift - tax_case_gift + gift_case
        effective_case_insurance = CASE_TOTAL_ASSETS - premium_case; tax_case_insurance = _calc(effective_case_insurance); net_case_insurance = effective_case_insurance - tax_case_insurance + claim_case
        effective_case_combo_not_tax = CASE_TOTAL_ASSETS - gift_case - premium_case; tax_case_combo_not_tax = _calc(effective_case_combo_not_tax); net_case_combo_not_tax = effective_case_combo_not_tax - tax_case_combo_not_tax + claim_case + gift_case
        effective_case_combo_tax = CASE_TOTAL_ASSETS - gift_case - premium_case + claim_case; tax_case_combo_tax = _calc(effective_case_combo_tax); net_case_combo_tax = effective_case_combo_tax - tax_case_combo_tax + gift_case

        df_case_results = pd.DataFrame({
            "遺產稅（萬）": list(map(int, [tax_case_no_plan, tax_case_gift, tax_case_insurance, tax_case_combo_not_tax, tax_case_combo_tax])),
            "家人總共取得（萬）": list(map(int, [net_case_no_plan, net_case_gift, net_case_insurance, net_case_combo_not_tax, net_case_combo_tax]))
        }, index=["沒有規劃","提前贈與","購買保險","提前贈與＋購買保險","提前贈與＋購買保險（被實質課稅）"])
        st.table(_fmt_table(df_case_results))

def run_estate():
    constants = TaxConstants()
    calculator = EstateTaxCalculator(constants)
    ui = EstateTaxUI(calculator)
    ui.render_ui()
