# modules/wrapped_cvgift.py — 修正版：修正f-string引號、欄位名稱一致
import pandas as pd
import streamlit as st

EXEMPTION    = 2_440_000
BR10_NET_MAX = 28_110_000
BR15_NET_MAX = 56_210_000
RATE_10, RATE_15, RATE_20 = 0.10, 0.15, 0.20
MAX_ANNUAL   = 100_000_000

def card(label: str, value: str, note: str = ""):
    html = f'<div class="kpi"><div class="label">{label}</div><div class="value">{value}</div>'
    if note:
        html += f'<div class="note">{note}</div>'  # 修正這行引號
    html += '</div>'
    st.markdown(html, unsafe_allow_html=True)

def fmt(n: float) -> str: return f"{n:,.0f}"
def fmt_y(n: float) -> str: return f"{fmt(n)} 元"

def tax_calc(net:int):
    if net <= 0: return 0, "—"
    if net <= BR10_NET_MAX: return int(round(net * RATE_10)), "10%"
    if net <= BR15_NET_MAX:
        base = BR10_NET_MAX * RATE_10
        extra = (net - BR10_NET_MAX) * RATE_15
        return int(round(base + extra)), "15%"
    base = BR10_NET_MAX * RATE_10 + (BR15_NET_MAX - BR10_NET_MAX) * RATE_15
    extra = (net - BR15_NET_MAX) * RATE_20
    return int(round(base + extra)), "20%"

def _on_prem_change():
    p = int(st.session_state.y1_prem)
    st.session_state.y2_prem = p
    st.session_state.y3_prem = p
    st.session_state.y1_cv = 0
    st.session_state.y2_cv = 0
    st.session_state.y3_cv = 0

def run_cvgift():
    DEFAULTS = {
        "change_year": 1,
        "y1_prem": 10_000_000,
        "y2_prem": 10_000_000,
        "y3_prem": 10_000_000,
        "y1_cv":   5_000_000,
        "y2_cv":  14_000_000,
        "y3_cv":  24_000_000,
    }
    for k, v in DEFAULTS.items():
        if k not in st.session_state:
            st.session_state[k] = v

    st.title("保單規劃｜用同樣現金流，更聰明完成贈與")
    st.caption("單位：新台幣。稅制假設（114年/2025）：年免稅 2,440,000；10% 淨額上限 28,110,000；15% 淨額上限 56,210,000。")

    st.number_input("年繳保費（元）",
        min_value=0, max_value=MAX_ANNUAL, step=100_000, format="%d",
        key="y1_prem", on_change=_on_prem_change)

    st.selectbox("第幾年變更要保人（交棒）",
        options=[1, 2, 3], index=0, key="change_year")

    p = int(st.session_state.y1_prem)
    max_y1, max_y2, max_y3 = p*1, p*2, p*3

    st.subheader("前三年保價金（年末現金價值）")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.number_input("第 1 年保價金（元）", min_value=0, max_value=max_y1, step=100_000, format="%d", key="y1_cv")
    with c2:
        st.number_input("第 2 年保價金（元）", min_value=0, max_value=max_y2, step=100_000, format="%d", key="y2_cv")
    with c3:
        st.number_input("第 3 年保價金（元）", min_value=0, max_value=max_y3, step=100_000, format="%d", key="y3_cv")

    st.session_state.y2_prem = st.session_state.y1_prem
    st.session_state.y3_prem = st.session_state.y1_prem

    def build_schedule_3y():
        rows, cum = [], 0
        for y in (1, 2, 3):
            premium = int(st.session_state.y1_prem)
            cum += premium
            cv = int(st.session_state[f"y{y}_cv"])
            rows.append({"年度": y, "每年投入（元）": premium, "累計投入（元）": cum, "年末現金價值（元）": cv})
        return pd.DataFrame(rows)

    df_years = build_schedule_3y()
    change_year = int(st.session_state.change_year)

    cv_at_change = int(df_years.loc[df_years["年度"] == change_year, "年末現金價值（元）"].iloc[0])
    nominal_transfer_to_N = int(df_years.loc[df_years["年度"] <= change_year, "每年投入（元）"].sum())

    gift_with_policy = cv_at_change
    net_with_policy  = max(0, gift_with_policy - EXEMPTION)
    tax_with_policy, rate_with = tax_calc(net_with_policy)

    total_tax_no_policy, yearly_tax_list = 0, []
    for _, r in df_years[df_years["年度"] <= change_year].iterrows():
        annual_i = int(r["每年投入（元）"])
        net = max(0, annual_i - EXEMPTION)
        t, rate = tax_calc(net)
        total_tax_no_policy += t
        yearly_tax_list.append({
            "年度": int(r["年度"]),
            "現金贈與（元）": annual_i,
            "免稅後淨額（元）": net,
            "應納贈與稅（元）": t,
            "適用稅率": rate
        })

    tax_saving   = total_tax_no_policy - tax_with_policy
    saving_label = "節省之贈與稅" if tax_saving >= 0 else "增加之贈與稅"

    colA, colB, colC = st.columns(3)
    with colA:
        st.markdown(f"**保單規劃（第 {change_year} 年變更）**")
        card(f"累積移轉（名目）至第 {change_year} 年", fmt_y(nominal_transfer_to_N))
        card("變更當年視為贈與（保單價值準備金）", fmt_y(gift_with_policy))
        card("當年度應納贈與稅", fmt_y(tax_with_policy), note=f"稅率 {rate_with}")
    with colB:
        st.markdown(f"**現金贈與（第 1～{change_year} 年）**")
        card(f"累積移轉（名目）至第 {change_year} 年", fmt_y(nominal_transfer_to_N))
        card(f"累計贈與稅（至第 {change_year} 年）", fmt_y(total_tax_no_policy))
    with colC:
        st.markdown("**稅負差異**")
        card(f"至第 {change_year} 年{saving_label}", fmt_y(abs(tax_saving)))

    with st.expander("年度明細與逐年稅額（1～3 年）", expanded=False):
        st.markdown("**年度現金價值（1～3 年皆為手動輸入）**")
        df_show = df_years.copy()
        df_show["每年投入（元）"] = df_show["每年投入（元）"].map(fmt)
        df_show["累計投入（元）"] = df_show["累計投入（元）"].map(fmt)
        df_show["年末現金價值（元）"] = df_show["年末現金價值（元）"].map(fmt)
        st.dataframe(df_show, use_container_width=True, hide_index=True)

        st.markdown("**現金贈與：逐年稅額（第 1～變更年）**")
        df_no = pd.DataFrame(sorted(yearly_tax_list, key=lambda x: x["年度"]))
        df_no_show = df_no.copy()
        for c in ["現金贈與（元）", "免稅後淨額（元）", "應納贈與稅（元）"]:
            df_no_show[c] = df_no_show[c].map(fmt_y)
        st.dataframe(df_no_show, use_container_width=True, hide_index=True)

        # 匯出 CSV
        csv_all = pd.concat([df_years, df_no], axis=1)
        st.download_button(
            "下載明細（CSV）",
            data=csv_all.to_csv(index=False).encode("utf-8-sig"),
            file_name="年度明細_逐年稅額.csv",
            mime="text/csv"
        )
