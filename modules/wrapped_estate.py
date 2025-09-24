# modules/wrapped_estate.py
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Tuple, Dict, Any, List

import pandas as pd
import plotly.express as px
import streamlit as st


# ===============================
# 1. 常數與設定
# ===============================
@dataclass
class TaxConstants:
    """遺產稅相關常數（單位：萬）"""
    EXEMPT_AMOUNT: float = 1333
    FUNERAL_EXPENSE: float = 138
    SPOUSE_DEDUCTION_VALUE: float = 553
    ADULT_CHILD_DEDUCTION: float = 56
    PARENTS_DEDUCTION: float = 138
    DISABLED_DEDUCTION: float = 693
    OTHER_DEPENDENTS_DEDUCTION: float = 56
    TAX_BRACKETS: List[Tuple[float, float]] = field(
        default_factory=lambda: [
            (5621, 0.10),
            (11242, 0.15),
            (float("inf"), 0.20),
        ]
    )


class EstateTaxCalculator:
    def __init__(self, constants: TaxConstants):
        self.constants = constants

    def compute_deductions(
        self, spouse: bool, adult_children: int, other_dependents: int,
        disabled_people: int, parents: int
    ) -> float:
        spouse_ded = self.constants.SPOUSE_DEDUCTION_VALUE if spouse else 0
        total = (
            spouse_ded
            + self.constants.FUNERAL_EXPENSE
            + disabled_people * self.constants.DISABLED_DEDUCTION
            + adult_children * self.constants.ADULT_CHILD_DEDUCTION
            + other_dependents * self.constants.OTHER_DEPENDENTS_DEDUCTION
            + parents * self.constants.PARENTS_DEDUCTION
        )
        return total

    @st.cache_data(show_spinner=False)
    def calculate_estate_tax(
        _self, total_assets: float, spouse: bool, adult_children: int,
        other_dependents: int, disabled_people: int, parents: int
    ) -> Tuple[float, float, float]:
        deductions = _self.compute_deductions(
            spouse, adult_children, other_dependents, disabled_people, parents
        )
        if total_assets <= _self.constants.EXEMPT_AMOUNT + deductions:
            return 0.0, 0.0, deductions

        taxable = max(0.0, total_assets - _self.constants.EXEMPT_AMOUNT - deductions)

        tax_due = 0.0
        prev = 0.0
        for bound, rate in _self.constants.TAX_BRACKETS:
            if taxable > prev:
                taxed_part = min(taxable, bound) - prev
                tax_due += taxed_part * rate
                prev = bound
        return float(taxable), round(tax_due, 0), float(deductions)


class EstateTaxSimulator:
    def __init__(self, calculator: EstateTaxCalculator):
        self.calculator = calculator

    def simulate(
        self, total_assets: float, spouse: bool, adult_children: int,
        other_dependents: int, disabled_people: int, parents: int,
        premium: float, claim_amount: float, gift_amount: float
    ) -> pd.DataFrame:
        # baseline
        _, tax_base, _ = self.calculator.calculate_estate_tax(
            total_assets, spouse, adult_children, other_dependents, disabled_people, parents
        )
        net_base = total_assets - tax_base

        # 提前贈與
        effective_gift_assets = max(total_assets - gift_amount, 0)
        _, tax_gift, _ = self.calculator.calculate_estate_tax(
            effective_gift_assets, spouse, adult_children, other_dependents, disabled_people, parents
        )
        net_gift = effective_gift_assets - tax_gift + gift_amount

        # 買保單（不計入實質課稅）
        effective_ins = max(total_assets - premium, 0)
        _, tax_ins, _ = self.calculator.calculate_estate_tax(
            effective_ins, spouse, adult_children, other_dependents, disabled_people, parents
        )
        net_ins = effective_ins - tax_ins + claim_amount

        # 贈與 + 買保單（不計入實質課稅）
        effective_combo = max(total_assets - gift_amount - premium, 0)
        _, tax_combo, _ = self.calculator.calculate_estate_tax(
            effective_combo, spouse, adult_children, other_dependents, disabled_people, parents
        )
        net_combo = effective_combo - tax_combo + gift_amount + claim_amount

        # 贈與 + 買保單（理賠被實質課稅）
        effective_combo_taxed = max(total_assets - gift_amount - premium + claim_amount, 0)
        _, tax_combo_taxed, _ = self.calculator.calculate_estate_tax(
            effective_combo_taxed, spouse, adult_children, other_dependents, disabled_people, parents
        )
        net_combo_taxed = effective_combo_taxed - tax_combo_taxed + gift_amount

        df = pd.DataFrame({
            "規劃策略": [
                "沒有規劃",
                "提前贈與",
                "購買保險",
                "提前贈與＋購買保險",
                "提前贈與＋購買保險（被實質課稅）",
            ],
            "家人總共取得（萬）": [
                int(net_base), int(net_gift), int(net_ins), int(net_combo), int(net_combo_taxed)
            ],
            "遺產稅（萬）": [
                int(tax_base), int(tax_gift), int(tax_ins), int(tax_combo), int(tax_combo_taxed)
            ]
        })
        base_value = df.loc[df["規劃策略"] == "沒有規劃", "家人總共取得（萬）"].iloc[0]
        df["規劃效益（相較無規劃）"] = df["家人總共取得（萬）"] - base_value
        return df


def run_estate():
    st.markdown("<h2 class='page-title'>遺產稅試算</h2>", unsafe_allow_html=True)

    constants = TaxConstants()
    calc = EstateTaxCalculator(constants)
    sim = EstateTaxSimulator(calc)

    with st.container():
        st.markdown("#### 選擇適用地區")
        _ = st.selectbox("地區", ["台灣（2025年起）"], index=0, key="region_estate")

    st.markdown("### 請輸入資產及家庭資訊（單位：萬）")

    colA, colB, colC = st.columns(3)
    with colA:
        total_assets = st.number_input("總資產", min_value=1000, max_value=100000, value=5000, step=100)
        spouse = st.checkbox("有配偶（配偶扣除額 553 萬）", value=False)
        parents = st.number_input("父母數（每人 138 萬，最多 2 人）", min_value=0, max_value=2, value=0)
    with colB:
        adult_children = st.number_input("直系血親卑親屬數（每人 56 萬）", min_value=0, max_value=10, value=0)
        other_dependents = st.number_input("受撫養之兄弟姊妹、祖父母數（每人 56 萬）", min_value=0, max_value=5, value=0)
    with colC:
        max_disabled = (1 if spouse else 0) + adult_children + parents
        disabled_people = st.number_input("重度以上身心障礙者數（每人 693 萬）", min_value=0, max_value=max_disabled, value=0)

    # 計算
    taxable_amount, tax_due, total_deductions = calc.calculate_estate_tax(
        total_assets, spouse, adult_children, other_dependents, disabled_people, parents
    )

    st.markdown("---")
    st.markdown(f"### 預估遺產稅：**{int(tax_due):,} 萬**（課稅遺產淨額：{int(taxable_amount):,} 萬）")

    # 概覽表
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("**資產概況**")
        st.table(pd.DataFrame({"項目": ["總資產"], "金額（萬）": [int(total_assets)]}))
    with col2:
        st.markdown("**扣除項目**")
        df_deductions = pd.DataFrame({
            "項目": [
                "免稅額", "喪葬費扣除額", "配偶扣除額",
                "直系血親卑親屬扣除額", "父母扣除額",
                "重度身心障礙扣除額", "其他撫養扣除額",
            ],
            "金額（萬）": [
                constants.EXEMPT_AMOUNT,
                constants.FUNERAL_EXPENSE,
                constants.SPOUSE_DEDUCTION_VALUE if spouse else 0,
                adult_children * constants.ADULT_CHILD_DEDUCTION,
                parents * constants.PARENTS_DEDUCTION,
                disabled_people * constants.DISABLED_DEDUCTION,
                other_dependents * constants.OTHER_DEPENDENTS_DEDUCTION,
            ],
        })
        df_deductions["金額（萬）"] = df_deductions["金額（萬）"].astype(int)
        st.table(df_deductions)
    with col3:
        st.markdown("**稅務計算**")
        st.table(pd.DataFrame({"項目": ["課稅遺產淨額", "預估遺產稅"], "金額（萬）": [int(taxable_amount), int(tax_due)]}))

    st.markdown("---")
    st.markdown("### 策略模擬（僅供討論用）")

    default_premium = max(0, int(math.ceil(tax_due / 10) * 10))
    default_claim = int(default_premium * 1.5)
    default_gift = min(244, max(0, total_assets - default_premium))

    colx, coly, colz = st.columns(3)
    with colx:
        premium = st.number_input("購買保險保費（萬）", min_value=0, max_value=total_assets,
                                  value=default_premium, step=100)
    with coly:
        claim = st.number_input("保險理賠金（萬）", min_value=0, max_value=100000,
                                value=default_claim, step=100)
    with colz:
        gift = st.number_input("提前贈與金額（萬）", min_value=0, max_value=max(0, total_assets - premium),
                               value=min(default_gift, max(0, total_assets - premium)), step=50)

    if premium > total_assets:
        st.error("保費不可高於總資產"); return
    if gift > total_assets - premium:
        st.error("提前贈與不可高於【總資產 - 保費】"); return

    df = sim.simulate(
        total_assets=total_assets,
        spouse=spouse,
        adult_children=adult_children,
        other_dependents=other_dependents,
        disabled_people=disabled_people,
        parents=parents,
        premium=premium,
        claim_amount=claim,
        gift_amount=gift,
    )

    st.table(df)

    fig = px.bar(df, x="規劃策略", y="家人總共取得（萬）", text="家人總共取得（萬）",
                 title="不同策略下家人總共取得（萬）")
    fig.update_traces(textposition="outside")
    base_val = df.loc[df["規劃策略"] == "沒有規劃", "家人總共取得（萬）"].iloc[0]
    for _, row in df.iterrows():
        if row["規劃策略"] != "沒有規劃":
            diff = int(row["家人總共取得（萬）"] - base_val)
            fig.add_annotation(x=row["規劃策略"], y=max(row["家人總共取得（萬）"] * 0.5, 1),
                               text=f"+{diff}" if diff >= 0 else f"{diff}",
                               showarrow=False)
    fig.update_layout(margin=dict(t=80, b=50), height=520)
    st.plotly_chart(fig, width="stretch")

    st.caption("＊以上為示意估算，實際課稅以主管機關及個案條件為準。")
