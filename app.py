import os
import json
import time
import secrets
import datetime as _dt
import streamlit as st
from modules.wrapped_estate import run_estate
from modules.wrapped_cvgift import run_cvgift
import base64

# =========================
# 基本設定
# =========================
st.set_page_config(
    page_title="《影響力》傳承策略平台 | 整合版",
    layout="wide",
    page_icon="logo2.png",  # favicon
)

SESSION_STORE_PATH = os.environ.get("SESSION_STORE_PATH", ".sessions.json")
SESSION_TTL_SECONDS = int(os.environ.get("SESSION_TTL_SECONDS", "3600"))

# =========================
# 載入 logo.png (assets 資料夾)
# =========================
def load_logo(path="assets/logo.png"):
    try:
        with open(path, "rb") as f:
            data = f.read()
        return f"data:image/png;base64,{base64.b64encode(data).decode()}"
    except Exception:
        return None

logo_data_uri = load_logo()

# =========================
# CSS 美化
# =========================
INK   = "#111827"  # 主標題黑色
MUTED = "#6b7280"
BRAND = "#e11d48"

st.markdown(
    f"""
<style>
[data-testid="stToolbar"] {{ visibility: hidden; height: 0; position: fixed; }}
header {{ visibility: hidden; height: 0; }}
#MainMenu {{ visibility: hidden; }}
footer {{ visibility: hidden; }}

.stApp {{
  background: linear-gradient(180deg, #fff, #fff9f9 30%, #fff 80%);
  padding-top: 0.75rem;
}}
.block-container {{ padding-top: .5rem; max-width: 1200px; }}

.stTabs [role="tablist"] {{ gap: 2rem; }}
.stTabs [role="tab"] {{
  font-size: 1.06rem; padding: .6rem .25rem; color: {MUTED};
  border-bottom: 2px solid transparent;
}}
.stTabs [role="tab"][aria-selected="true"] {{
  color: {BRAND}; border-color: {BRAND}; font-weight: 700;
}}

.logout-btn>button {{
  border-radius: 4px !important;
  padding: .3rem .7rem !important;
  box-shadow: none !important;
  border: 1px solid #d1d5db !important;
  color: #374151 !important;
  background: #f9fafb !important;
  font-size: 0.85rem !important;
}}
.logout-btn>button:hover {{
  background: #f3f4f6 !important;
  color: #111827 !important;
}}

.app-title h1, .app-title h2 {{
  color: {INK} !important;   /* 主標題黑色 */
  font-size: 2.4rem !important;
  line-height: 1.2;
  margin: .25rem 0 1rem 0 !important;
  font-weight: 800;
}}

.js-plotly-plot .bartext {{ fill: #ffffff !important; }}
.js-plotly-plot g.annotation text {{ fill: #ffffff !important; }}
</style>
""",
    unsafe_allow_html=True,
)

# =========================
# Header
# =========================
if logo_data_uri:
    st.markdown(
        f"""
        <div style="display:flex;align-items:center;gap:16px;margin-bottom:2px;">
          <img src="{logo_data_uri}" alt="logo" style="height:56px;display:block;" />
          <div>
            <h2 style="margin:0;color:{INK}">《影響力》傳承策略平台｜整合版</h2>
            <p style="margin:0;color:{MUTED};font-size:0.95rem;">
              專業 × 溫度 × 智能｜遺產稅試算 + 保單贈與規劃
            </p>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
else:
    st.markdown(
        f"<h2 style='color:{INK}'>《影響力》傳承策略平台｜整合版</h2>",
        unsafe_allow_html=True,
    )

st.markdown(
    "<hr style='border:none;height:1px;background:linear-gradient(90deg,#e11d48,transparent);margin:.75rem 0 1rem 0;'/>",
    unsafe_allow_html=True,
)

# =========================
# Tabs
# =========================
tabs = st.tabs(["🏛️ 遺產稅試算", "🎁 保單贈與規劃"])

with tabs[0]:
    st.markdown("<div class='app-title'><h2>遺產稅試算</h2></div>", unsafe_allow_html=True)
    run_estate()

with tabs[1]:
    st.markdown("<div class='app-title'><h2>保單規劃｜用同樣現金流，更聰明完成贈與</h2></div>", unsafe_allow_html=True)
    run_cvgift()

st.markdown("---")
st.caption("《影響力》傳承策略平台｜永傳家族辦公室 ｜ 聯絡信箱：123@gracefo.com")
