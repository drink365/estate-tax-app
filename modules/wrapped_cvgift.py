import streamlit as st
import pandas as pd
import math
import plotly.express as px

ANNUAL_GIFT_EXEMPTION = 244  # 每人每年免稅額（萬）。示意用途
# 示意用贈與稅級距（萬）：同遺/贈三級 10% / 15% / 20%
GIFT_BRACKETS = [(5621, 0.10), (11242, 0.15), (float("inf"), 0.20)]

def _gift_tax(amount: float) -> int:
    """示意用贈與稅：用三階級（萬）"""
    if amount <= 0:
        return 0
    tax = 0.0
    prev = 0.0
    for up, rate in GIFT_BRACKETS:
        if amount > prev:
            taxed = min(amount, up) - prev
            tax += taxed * rate
            prev = up
        else:
            break
    return int(round(tax, 0))

def run_cvgift():
    st.markdown("## 保單贈與規劃")

    with st.expander("保單贈與的八大好處（簡要）", expanded=False):
        df = pd.DataFrame({
            "八大好處": [
                "1. 降低贈與稅負",
                "2. 保障資產傳承秩序",
                "3. 增加家族現金流穩定性",
                "4. 具成本效益",
                "5. 靈活分期給付",
                "6. 避免爭產糾紛",
                "7. 兼具保障與傳承",
                "8. 合法稅務節流"
            ]
        })
        st.table(df)

    st.markdown("---")
    st.markdown("### 贈與策略示意試算（*展示用途，非正式稅額*）")

    # 基本輸入
    col1, col2 = st.columns(2)
    with col1:
        cv = st.number_input("保單現金價值（萬）", min_value=0, max_value=200000, value=2000, step=100)
        donee_cnt = st.number_input("受贈人數（人）", min_value=1, max_value=10, value=1, step=1)
    with col2:
        years = st.number_input("預計分年贈與年數（年）", min_value=1, max_value=50, value=5, step=1)
        add_cash = st.number_input("同步增額（若另購增額保單，萬）", min_value=0, max_value=200000, value=0, step=100)

    total_base = cv + add_cash  # 示意：若同時加購增額保單，視同一併規劃之資產

    # 方案 A：一次贈與
    exempt_A = ANNUAL_GIFT_EXEMPTION * donee_cnt  # 當年可用免稅
    taxable_A = max(0, total_base - exempt_A)
    tax_A = _gift_tax(taxable_A)
    net_A = total_base - tax_A  # 受贈人淨得（示意）

    # 方案 B：分年贈與（years 年）
    total_exempt_B = ANNUAL_GIFT_EXEMPTION * donee_cnt * years
    taxable_B = max(0, total_base - total_exempt_B)
    tax_B = _gift_tax(taxable_B)
    net_B = total_base - tax_B

    # 方案 C：估算「免稅全數移轉所需年數」
    years_needed = math.ceil(total_base / (ANNUAL_GIFT_EXEMPTION * donee_cnt)) if donee_cnt > 0 else float("inf")

    # 輸出表格
    df_res = pd.DataFrame({
        "規劃方案": ["一次贈與（當年）", f"分年贈與（{years} 年）", "估算完全免稅所需年數"],
        "總額（萬）": [int(total_base), int(total_base), int(total_base)],
        "免稅額度（萬）": [int(exempt_A), int(total_exempt_B), int(ANNUAL_GIFT_EXEMPTION*donee_cnt*years_needed)],
        "應稅贈與（萬）": [int(taxable_A), int(taxable_B), max(0, int(total_base - ANNUAL_GIFT_EXEMPTION*donee_cnt*years_needed))],
        "估算贈與稅（萬）": [int(tax_A), int(tax_B), int(_gift_tax(max(0, total_base - ANNUAL_GIFT_EXEMPTION*donee_cnt*years_needed)))],
        "受贈人淨得（萬）": [int(net_A), int(net_B), int(total_base - _gift_tax(max(0, total_base - ANNUAL_GIFT_EXEMPTION*donee_cnt*years_needed)))]
    })
    st.table(df_res)

    # CSV 下載
    csv = df_res.to_csv(index=False).encode("utf-8-sig")
    st.download_button("下載保單贈與試算 CSV", csv, "cvgift_simulation.csv", "text/csv", key="cvgift-csv")

    # 視覺化：強調分年優勢
    fig = px.bar(
        df_res.iloc[:2],  # 先比較前兩個方案
        x="規劃方案",
        y="受贈人淨得（萬）",
        text="受贈人淨得（萬）",
        title="一次 vs 分年贈與：受贈人淨得比較（示意）"
    )
    fig.update_traces(texttemplate='%{text:.0f}', textposition='outside')
    # 顯示白色文字差額
    base = df_res.loc[df_res["規劃方案"] == "一次贈與（當年）", "受贈人淨得（萬）"].iloc[0]
    for _, row in df_res.iloc[:2].iterrows():
        if row["規劃方案"] != "一次贈與（當年）":
            diff = row["受贈人淨得（萬）"] - base
            fig.add_annotation(x=row["規劃方案"], y=row["受贈人淨得（萬）"]/2,
                               text=f"{'+' if diff>=0 else ''}{int(diff)}",
                               showarrow=False, font=dict(color="white", size=16))
    st.plotly_chart(fig, config={"responsive": True}, use_container_width=True)

    st.caption("＊以上為示意模型，實務需依「保單類型、要保人/被保險人/受益人結構、實質課稅規則」綜合判斷。可於會談中進一步採用精準版。")
