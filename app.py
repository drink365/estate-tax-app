import streamlit as st
from modules import estate_tax_app, cvgift_app
from utils.session_manager import get_current_user, logout
from utils.html_utils import local_css

# ====== 基本設定 ======
st.set_page_config(
    page_title="《影響力》傳承策略平台 | 整合版",
    page_icon="logo2.png",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# 套用自訂 CSS
local_css("style.css")

# ====== Header ======
col1, col2 = st.columns([1, 4])
with col1:
    st.image("logo.png", width=220)  # 保持高解析度，不拉伸
with col2:
    st.markdown(
        """
        <div style="padding-top:20px;">
            <h1 style="margin-bottom:0; font-size:38px;">《影響力》傳承策略平台 | 整合版</h1>
            <p style="margin-top:5px; font-size:18px; color:gray;">
                專業 × 溫度 × 智能 ｜ 遺產稅試算 + 保單贈與規劃
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.markdown("---")

# ====== 使用者資訊列 ======
user = get_current_user()
if user:
    col1, col2 = st.columns([6, 1])
    with col1:
        st.markdown(
            f"歡迎 😀 ，**{user['username']}** ｜ 有效期限至 {user['valid_until']}",
            unsafe_allow_html=True,
        )
    with col2:
        if st.button("登出", use_container_width=True):
            logout()
            st.rerun()
else:
    st.warning("請先登入以使用平台功能")

st.markdown("<br>", unsafe_allow_html=True)

# ====== 導覽 Tabs ======
tabs = st.tabs([
    "🏛️ 遺產稅試算",
    "🎁 保單贈與規劃",
])

with tabs[0]:
    st.markdown(
        "<h2 style='color:#C00000; font-size:30px;'>遺產稅試算</h2>",
        unsafe_allow_html=True,
    )
    estate_tax_app.app()

with tabs[1]:
    st.markdown(
        "<h2 style='color:#C00000; font-size:30px;'>保單規劃｜用同樣現金流，更聰明完成贈與</h2>",
        unsafe_allow_html=True,
    )
    cvgift_app.app()

# ====== 頁尾 ======
st.markdown("---")
st.markdown(
    """
    《影響力》傳承策略平台 ｜ 永傳家族辦公室  
    聯絡信箱：<a href="mailto:123@gracefo.com">123@gracefo.com</a>
    """,
    unsafe_allow_html=True,
)
