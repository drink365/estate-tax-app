# modules/wrapped_cvgift.py
from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

GIFT_EXEMPT_YEARLY = 2_440_000
GIFT_BRACKETS = [
    (28_110_000, 0.10),
    (56_210_000, 0.15),
    (float("inf"), 0.20),
]


def gift_tax(net_amount: int) -> int:
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


def summarize_plan(annual_premium: int, change_year: int, cv_map: dict) -> dict:
    gift_amount = int(cv_map.get(change_year, 0))
    net = max(0, gift_amount - GIFT_EXEMPT_YEARLY)
    tax = gift_tax(net)
    total_premium_paid = int(annual_premium * change_year)

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


def _benefit_cards():
    st.markdown("### 8 大好處（用同樣現金流，更聰明完成贈與）")
    cols = st.columns(4)
    items = [
        ("💡 明確目的", "以『變更要保人』實現提前贈與。"),
        ("🧾 稅負可預期", "按淨額10/15/20%分級，稅源可事前準備。"),
        ("💸 現金流不變", "維持原本年繳保費，流程簡單。"),
        ("🧑‍🤝‍🧑 受益保障", "指定受益人，資金歸屬清楚。"),
        ("🧱 資產隔離", "保單具保全、抗風險特性。"),
        ("🧭 彈性安排", "可選擇最佳變更年度與金額。"),
        ("📈 淨移轉提升", "多年度分批，總淨移轉金額更高。"),
        ("📑 留痕可驗", "契約/保單文件留痕，合規易檢。"),
    ]
    for i, (title, desc) in enumerate(items):
        with cols[i % 4]:
            st.markdown(
                f"""
                <div style="border:1px solid #eee;border-radius:12px;padding:14px;margin-bottom:12px;background:#fff;">
                  <div style="font-weight:700;margin-bottom:6px;">{title}</div>
                  <div style="color:#6b7280;font-size:0.95rem;">{desc}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )


def run_cvgift():
    st.markdown("<h2 class='page-title'>保單贈與規劃</h2>", unsafe_allow_html=True)

    st.markdown(
        "以『**變更要保人**』達成提前贈與的直觀試算。此頁以示意模型協助溝通決策，"
        "實務仍需依保單條款與主管機關規範調整。"
    )

    _benefit_cards()

    st.markdown("### 輸入條件（單位：元）")
    col1, col2 = st.columns([1, 1])
    with col1:
        annual_premium = st.number_input("年繳保費", min_value=0, step=100_000, value=10_000_000, format="%d")
        change_year = st.selectbox("第幾年變更要保人", options=[1, 2, 3], index=0)
    with col2:
        cv1 = st.number_input("第 1 年保價金（年末現金價值）", min_value=0, step=100_000, value=5_000_000, format="%d")
        cv2 = st.number_input("第 2 年保價金（年末現金價值）", min_value=0, step=100_000, value=14_000_000, format="%d")
        cv3 = st.number_input("第 3 年保價金（年末現金價值）", min_value=0, step=100_000, value=24_000_000, format="%d")

    result = summarize_plan(annual_premium, change_year, {1: cv1, 2: cv2, 3: cv3})

    st.markdown("### 效果總覽")
    colA, colB, colC = st.columns(3)
    with colA:
        st.metric("當年贈與金額", f"{result['gift_amount']:,} 元")
    with colB:
        st.metric("估算贈與稅", f"{result['gift_tax']:,} 元")
    with colC:
        st.metric("贈與淨額（可移轉）", f"{result['net_amount']:,} 元")

    st.markdown("### 詳細結果")
    st.table(result["table"])

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
    st.plotly_chart(fig, use_container_width=True, config={"responsive": True})

    with st.expander("假設與備註", expanded=False):
        st.markdown(
            """
- 變更要保人視同贈與，贈與額以 **當年度年末現金價值** 為基礎（示意）。
- 年免稅額假設為 **2,440,000 元**；贈與稅採 **10%/15%/20%** 之分級示意。
- 本頁僅供規劃討論，實務仍需依：要保/被保/受益人關係、保單條款、保單價值金定義、保險法與稅法等規範調整。
- 如需進一步法遵檢核與客製化模型，我們可在內部版本擴充計算引擎與輸出報告。
"""
        )
