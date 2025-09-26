# modules/wrapped_estate.py
# AI 秒算遺產稅（簡化版＋穩定表格顯示）
# - 修復：避免 df.astype(int) 在含 NaN 時拋出 ValueError
# - 顯示：表格改用「安全轉型 → Int64（可空整數）→ 千分位格式」
# - 介面：保留簡潔輸入與結果示範，方便之後擴充

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
    # 喪葬費用（萬元）
    FUNERAL_EXPENSE: float = 138  # 例：138 萬
    # 配偶扣除額（萬元）
    SPOUSE_DEDUCTION_VALUE: float = 553  # 例：553 萬
    # 成年子女每人扣除額（萬元）
    ADULT_CHILD_DEDUCTION: float = 56    # 例：56 萬
    # 免稅額（萬元）— 視規範調整
    EXEMPT_AMOUNT: float = 1333          # 例：1,333 萬
    # 免稅門檻：若課稅遺產淨額未達此門檻，稅額為 0（可依規範調整）
    FLOOR: float = 0

    # 稅率級距（僅示範用途，請依最新規範調整）
    # 以「萬元」為單位，稅率用小數（0.1 = 10%）
    BRACKETS: Tuple[Tuple[float, float], ...] = (
        (0, 0.10),
        (5000, 0.15),
        (10000, 0.20),
        (20000, 0.30),
    )

CONS = TaxConstants()


# ===============================
# 2. 計算邏輯
# ===============================
def _calc_progressive_tax(tax_base_wan: float, cons: TaxConstants = CONS) -> float:
    """
    簡化累進計算（示範）：
    - 傳入金額單位為「萬元」
    - 回傳稅額單位為「萬元」
    """
    if tax_base_wan <= 0:
        return 0.0

    tax = 0.0
    remaining = tax_base_wan
    # 依序套用級距
    # BRACKETS: (起點, 稅率)
    # 例： [0,10%], [5000,15%], [10000,20%], [20000,30%]
    brackets = list(cons.BRACKETS)
    for i, (start, rate) in enumerate(brackets):
        # 下一級距起點
        end = brackets[i + 1][0] if i + 1 < len(brackets) else math.inf
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
    """
    回傳各扣除項目（萬元）
    """
    ded = {
        "免稅額": cons.EXEMPT_AMOUNT,
        "喪葬費用": cons.FUNERAL_EXPENSE,
        "配偶扣除": cons.SPOUSE_DEDUCTION_VALUE if spouse else 0.0,
        "成年子女扣除": cons.ADULT_CHILD_DEDUCTION * max(0, adult_children_count),
        "其他扣除": max(0.0, other_deductions_wan),
    }
    # 限制扣除合計不得超過遺產總額（避免負值）
    total_ded = sum(ded.values())
    if total_ded > estate_total_wan:
        # 按比例壓縮（示範用法；你也可選擇只砍「其他扣除」）
        factor = estate_total_wan / total_ded if total_ded > 0 else 0
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
    """
    主計算：回傳 dict，內含扣除明細、課稅基礎、試算稅額
    - 所有金額以「萬元」為單位
    """
    ded = compute_deductions(estate_total_wan, spouse, adult_children_count, other_deductions_wan, cons)
    ded_total = sum(ded.values())
    taxable_base = max(0.0, estate_total_wan - ded_total)
    # 若有免稅門檻（FLOOR）邏輯，可在此加入
    tax_wan = _calc_progressive_tax(taxable_base, cons)

    return {
        "estate_total_wan": estate_total_wan,
        "deductions": ded,                 # 各項扣除（萬元）
        "deductions_total": ded_total,     # 扣除總額（萬元）
        "taxable_base": taxable_base,      # 課稅遺產淨額（萬元）
        "tax_wan": tax_wan,                # 試算稅額（萬元）
    }


# ===============================
# 3. UI 呈現
# ===============================
class EstateUI:
    def __init__(self):
        self.cons = CONS

    def _fmt_table_int64(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        安全轉整數（允許 NaN）→ Int64（可空整數）→ 回傳「字串化、千分位」的 DataFrame。
        注意：此為「顯示」資料，非計算用。
        """
        df_show = df.apply(lambda col: pd.to_numeric(col, errors="coerce"))
        # 以萬元為單位，多數欄位是整數；四捨五入再用 Int64 承接 NaN
        df_show = df_show.round(0).astype("Int64")
        df_fmt = df_show.applymap(lambda x: f"{x:,}" if pd.notna(x) else "—")
        return df_fmt

    def render_ui(self):
        st.markdown("## AI 秒算遺產稅")

        with st.container():
            c1, c2, c3, c4 = st.columns([1.4, 1.0, 1.0, 1.0])
            estate_total_wan = c1.number_input("遺產總額（萬元）", min_value=0.0, step=100.0, value=5000.0)
            spouse = c2.selectbox("是否有配偶", options=[True, False], index=0, format_func=lambda x: "是" if x else "否")
            adult_children_count = c3.number_input("成年子女數", min_value=0, step=1, value=2)
            other_deductions_wan = c4.number_input("其他扣除（萬元）", min_value=0.0, step=10.0, value=0.0)

        # 計算
        result = compute_estate_tax(
            estate_total_wan=estate_total_wan,
            spouse=spouse,
            adult_children_count=adult_children_count,
            other_deductions_wan=other_deductions_wan,
            cons=self.cons
        )

        # 扣除明細表
        st.markdown("### 扣除額明細")
        df_deductions = pd.DataFrame(
            {"扣除額（萬元）": pd.Series(result["deductions"], dtype="float")}
        )
        # ✅ 關鍵：安全轉型＋千分位顯示（避免 astype(int) 報錯）
        st.table(self._fmt_table_int64(df_deductions))

        # 結果摘要
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

        st.table(self._fmt_table_int64(summary.set_index("項目")))

        # 視覺化（簡單示範）
        try:
            pie_df = pd.DataFrame({
                "項目": ["扣除合計", "課稅遺產淨額"],
                "金額（萬元）": [result["deductions_total"], result["taxable_base"]],
            })
            fig = px.pie(pie_df, names="項目", values="金額（萬元）", title="遺產構成（萬元）")
            st.plotly_chart(fig, use_container_width=True)
        except Exception:
            pass


# ===============================
# 4. 對外入口
# ===============================
def run_estate():
    """
    外部由 app.py 呼叫的入口。
    """
    ui = EstateUI()
    ui.render_ui()
