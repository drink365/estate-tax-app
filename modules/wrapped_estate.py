# modules/wrapped_estate.py
# AI 秒算遺產稅（穩定版）
# - 徹底移除 .astype(...)，以「統一字串格式化」避免各種 dtype/NaN 轉型錯誤
# - 表格顯示：數值欄位→千分位字串；NaN → "—"
# - 保留既有互動與試算邏輯

from dataclasses import dataclass
from typing import Tuple, Dict, Any
import math

import pandas as pd
import streamlit as st
import plotly.express as px


# ===============================
# 1. 常數與設定（可按實務調整）
# ===============================
@dataclass
class TaxConstants:
    # 金額單位：萬元
    FUNERAL_EXPENSE: float = 138
    SPOUSE_DEDUCTION_VALUE: float = 553
    ADULT_CHILD_DEDUCTION: float = 56
    EXEMPT_AMOUNT: float = 1333
    FLOOR: float = 0

    BRACKETS: Tuple[Tuple[float, float], ...] = (
        (0, 0.10),
        (5000, 0.15),
        (10000, 0.20),
        (20000, 0.30),
    )

CONS = TaxConstants()


def _calc_progressive_tax(tax_base_wan: float, cons: TaxConstants = CONS) -> float:
    if tax_base_wan <= 0:
        return 0.0
    tax = 0.0
    remaining = tax_base_wan
    brackets = list(cons.BRACKETS)
    for i, (start, rate) in enumerate(brackets):
        end = brackets[i + 1][0] if i + 1 < len(brackets) else float("inf")
        width = max(0.0, min(remaining, end - start))
        if width <= 0:
            continue
        tax += width * rate
        remaining -= width
        if remaining <= 0:
            break
    return tax


def compute_deductions(
    estate_total_wan: float,
    spouse: bool,
    adult_children_count: int,
    other_deductions_wan: float = 0.0,
    cons: TaxConstants = CONS
) -> Dict[str, float]:
    ded = {
        "免稅額": cons.EXEMPT_AMOUNT,
        "喪葬費用": cons.FUNERAL_EXPENSE,
        "配偶扣除": cons.SPOUSE_DEDUCTION_VALUE if spouse else 0.0,
        "成年子女扣除": cons.ADULT_CHILD_DEDUCTION * max(0, adult_children_count),
        "其他扣除": max(0.0, other_deductions_wan),
    }
    total_ded = sum(ded.values())
    if total_ded > estate_total_wan and total_ded > 0:
        factor = estate_total_wan / total_ded
        for k in ded:
            ded[k] = round(ded[k] * factor, 4)
    return ded


def compute_estate_tax(
    estate_total_wan: float,
    spouse: bool,
    adult_children_count: int,
    other_deductions_wan: float = 0.0,
    cons: TaxConstants = CONS
) -> Dict[str, Any]:
    ded = compute_deductions(estate_total_wan, spouse, adult_children_count, other_deductions_wan, cons)
    ded_total = sum(ded.values())
    taxable_base = max(0.0, estate_total_wan - ded_total)
    tax_wan = _calc_progressive_tax(taxable_base, cons)
    return {
        "estate_total_wan": estate_total_wan,
        "deductions": ded,
        "deductions_total": ded_total,
        "taxable_base": taxable_base,
        "tax_wan": tax_wan,
    }


class EstateUI:
    def __init__(self):
        self.cons = CONS

    @staticmethod
    def _format_table(df: pd.DataFrame) -> pd.DataFrame:
        df_out = pd.DataFrame(index=df.index)
        for col in df.columns:
            s = df[col]
            s_num = pd.to_numeric(s, errors="coerce")
            numeric_ratio = s_num.notna().mean()
            if numeric_ratio >= 0.5:
                s_fmt = s_num.round(0).map(lambda x: f"{int(x):,}" if pd.notna(x) else "—")
                df_out[col] = s_fmt
            else:
                df_out[col] = s.map(lambda x: "—" if pd.isna(x) else str(x))
        return df_out

    def render_ui(self):
        st.markdown("## AI 秒算遺產稅")
        with st.container():
            c1, c2, c3, c4 = st.columns([1.4, 1.0, 1.0, 1.0])
            estate_total_wan = c1.number_input("遺產總額（萬元）", min_value=0.0, step=100.0, value=5000.0)
            spouse = c2.selectbox("是否有配偶", options=[True, False], index=0, format_func=lambda x: "是" if x else "否")
            adult_children_count = c3.number_input("成年子女數", min_value=0, step=1, value=2)
            other_deductions_wan = c4.number_input("其他扣除（萬元）", min_value=0.0, step=10.0, value=0.0)

        result = compute_estate_tax(
            estate_total_wan=estate_total_wan,
            spouse=spouse,
            adult_children_count=adult_children_count,
            other_deductions_wan=other_deductions_wan,
            cons=self.cons
        )

        st.markdown("### 扣除額明細")
        df_deductions = pd.DataFrame({"扣除額（萬元）": pd.Series(result["deductions"], dtype="object")})
        st.table(self._format_table(df_deductions))

        st.markdown("### 試算結果（萬元）")
        summary = pd.DataFrame({
            "項目": ["遺產總額", "扣除合計", "課稅遺產淨額", "試算稅額"],
            "金額（萬元）": [
                result["estate_total_wan"],
                result["deductions_total"],
                result["taxable_base"],
                result["tax_wan"],
            ],
        })
        st.table(self._format_table(summary.set_index("項目")))

        try:
            pie_df = pd.DataFrame({
                "項目": ["扣除合計", "課稅遺產淨額"],
                "金額（萬元）": [result["deductions_total"], result["taxable_base"]],
            })
            pie_df["金額（萬元）"] = pd.to_numeric(pie_df["金額（萬元）"], errors="coerce").fillna(0.0)
            if pie_df["金額（萬元）"].sum() > 0:
                import plotly.express as px
                fig = px.pie(pie_df, names="項目", values="金額（萬元）", title="遺產構成（萬元）")
                st.plotly_chart(fig, use_container_width=True)
        except Exception:
            pass


def run_estate():
    ui = EstateUI()
    ui.render_ui()
