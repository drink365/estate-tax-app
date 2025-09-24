# modules/wrapped_cvgift.py
# －－－「保單贈與規劃（CVGift）」功能頁 －－－
from __future__ import annotations

import math
from typing import Dict

import pandas as pd
import plotly.express as px
import streamlit as st


# 贈與稅：依淨額分級（單位：元）
GIFT_EXEMPT_YEARLY = 2_440_000  # 年免稅額
# 10% 淨額上限 28,110,000；15% 淨額上限 56,210,000；其餘 20%
GIFT_BRACKETS = [
    (28_110_000, 0.10),
    (56_210_000, 0.15),
    (float("inf"), 0.20),
]


def gift_tax(net_amount: int) -> int:
    """依淨額計算贈與稅（元）"""
    if net_amount <= 0:
        return 0
    tax = 0.0
    prev = 0.0
    for bound, rate in GIFT_BRACKETS:
        if net_amount > prev:
            taxed = min(net_amount, bound) - prev
            tax += taxed * rate
            prev = bound
    return int(round(tax))


def summarize_plan(
    annual_premium: int,
    change_year: int,
    cv1: int,
    cv2: int,
    cv3: int,
) -> Dict:
    """簡化版的『保單變更要保人』試算（單位：元）

    假設：
      - 第 change_year 年變更要保人，視同贈與當年「年末現金價值」
      - 贈與淨額 = 現金價值 - 年免稅額
      - 贈與稅依 GIFT_BRACKETS 計算
      - 同樣現金流：前 change_year 年皆支付保費（由原要保人負擔）
    """
    cvs = {1: cv1, 2: cv2, 3: cv3}
    gift_amount = cvs.get(change_year, 0)

    # 贈與稅
    net = max(0, gift_amount - GIFT_EXEMPT_YEARLY)
    tax = gift_tax(net)

    # 現金流（到變更前）
    total_premium_paid = annual_premium * change_year

    # 以表格回傳試算摘要
    df = pd.DataFrame(
        [
            ["變更年度", change_year, ""],
            ["贈與金額（以年末現金價值）", f"{gift_amount:,}", "元"],
            ["年免稅額", f"{GIFT_EXEMPT_YEARLY:,}", "元"],
            ["贈與淨額", f"{net:,}", "元"],
            ["估算贈與稅", f"{tax:,}", "元"],
            ["變更前累計保費", f"{total_premium_paid:,}", "元"],
        ],
        columns=["項目", "數值", "單位"],
    )

    return {
        "gift_amount": gift_amount,
        "net_amount": net,
        "gift_tax": tax,
        "total_premium_paid": total_premium_paid,
        "table": df,
    }


def run_cvgift():
    # 單一主標題（由 app.py 的 CSS 統一樣式）
    st.markdown("<h2 class='page-title'>保單贈與規劃</h2>", unsafe_allow_html=True)

    st.markdown(
        "以『**變更要保人**』達成提前贈與的直觀試算。此頁以示意模型協助溝通決策，"
        "實務仍需依保單條款與主管機關規範調整。"
    )

    with st.container():
        st.markdown("### 輸入條件（單位：元）")
        col1, col2 = st.columns([1, 1])
        with col1:
            annual_premium = st.number_input("年繳保費", min_value=0, step=100_000, value=10_000_000, format="%d")
            change_year = st.selectbox("第幾年變更要保人", options=[1, 2, 3], index=0)
        with col2:
            cv1 = st.number_input("第 1 年保價金（年末現金價值）", min_value=0, step=100_000, value=5_000_000, format="%d")
            cv2 = st.number_input("第 2 年保價金（年末現金價值）", min_value=0, step=100_000, value=14_000_000, format="%d")
            cv3 = st.number_input("第 3 年保價金（年末現金價值）", min_value=0, step=100_000, value=24_000_000, format="%d")

    # 試算
    result = summarize_plan(annual_premium, change_year, cv1, cv2, cv3)

    st.markdown("### 結果摘要")
    st.table(result["table"])

    # 視覺化：顯示「贈與金額 vs 贈與稅 vs 免稅額」
    df_plot = pd.DataFrame(
        {
            "項目": ["贈與金額", "年免稅額", "贈與淨額", "估算贈與稅"],
            "金額（元）": [
                result["gift_amount"],
                GIFT_EXEMPT_YEARLY,
                result["net_amount"],
                result["gift_tax"],
            ],
        }
    )
    fig = px.bar(df_plot, x="項目", y="金額（元）", text="金額（元）", title="贈與試算（示意）")
    fig.update_traces(textposition="outside")
    fig.update_layout(margin=dict(t=80, b=50), height=480)
    st.plotly_chart(fig, use_container_width=True)

    with st.expander("假設與備註", expanded=False):
        st.markdown(
            """
- 變更要保人視同贈與，贈與額以 **當年度年末現金價值** 為基礎（示意）。
- 年免稅額假設為 **2,440,000 元**；贈與稅採 **10%/15%/20%** 之分級示意。
- 本頁僅供規劃討論，實務仍需依：要保/被保/受益人關係、保單條款、保單價值金定義、保險法與稅法等規範調整。
- 如需進一步法遵檢核與客製化模型，我們可於內部版本擴充計算引擎與輸出報告。
"""
        )
