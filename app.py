# app.py — 影響力傳承策略平台（兩模組｜外層登入｜不提供任何預設帳號）
import os, uuid, base64, json
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any
from PIL import Image
import streamlit as st

# 子模組
from modules.wrapped_estate import run_estate
from modules.wrapped_cvgift import run_cvgift

# ---------- 資產路徑 ----------
BASE_DIR = Path(__file__).resolve().parent
ASSETS_DIR = BASE_DIR / "assets"

def _asset_path(name: str) -> str:
    return str(ASSETS_DIR / name)

@st.cache_data(show_spinner=False)
def _asset_b64(name: str) -> Optional[str]:
    try:
        with open(ASSETS_DIR / name, "rb") as f:
            return base64.b64encode(f.read()).decode()
    except Exception:
        return None

# ---------- 頁面設定與 favicon ----------
st.set_page_config(
    page_title="影響力傳承策略平台",
    page_icon=Image.open(_asset_path("logo2.png")) if os.path.exists(_asset_path("logo2.png"))
              else (Image.open(_asset_path("logo.png")) if os.path.exists(_asset_path("logo.png")) else "🧭"),
    layout="wide"
)

# ---------- 頂部抬頭（Logo 36px） ----------
st.markdown("""
<style>
.header { display:flex; align-items:center; justify-content:space-between; gap:12px; }
.brand { display:flex; align-items:center; gap:14px; }
.brand-title { margin:0; font-size:26px; color:#2b2f36; line-height:1; }
.brand-logo { height:36px; image-rendering:auto; }
@media (max-width:1200px){ .brand-logo{ height:32px; } .brand-title{ font-size:24px; } }
@media (max-width:768px){  .brand-logo{ height:28px; } .brand-title{ font-size:22px; } }
</style>
""", unsafe_allow_html=True)

b64_1x = _asset_b64("logo.png")
logo_img_tag = f"<img src='data:image/png;base64,{b64_1x}' class='brand-logo' alt='logo'>" if b64_1x else ""
st.markdown("<div class='header'>", unsafe_allow_html=True)
st.markdown(f"<div class='brand'>{logo_img_tag}<h1 class='brand-title'>影響力傳承策略平台</h1></div>", unsafe_allow_html=True)
right_col = st.container()
st.markdown("</div>", unsafe_allow_html=True)

# ---------- 認證：只接受 secrets 或環境變數，不提供任何預設帳號 ----------
def _load_authorized_users() -> Dict[str, Any]:
    """
    優先讀取 st.secrets['authorized_users']；
    次之讀取環境變數 AUTH_USERS_JSON（內容為 JSON 物件）。
    兩者皆無時，回傳空 dict（不允許登入成功）。
    """
    try:
        au = st.secrets.get("authorized_users", None)
        if au:
            return dict(au)  # MappingProxy → dict
    except Exception:
        pass

    env_json = os.getenv("AUTH_USERS_JSON", "").strip()
    if env_json:
        try:
            data = json.loads(env_json)
            if isinstance(data, dict):
                return data
            else:
                st.warning("AUTH_USERS_JSON 應為 JSON 物件（字典）格式。")
        except Exception:
            st.warning("AUTH_USERS_JSON 解析失敗，請檢查 JSON 格式。")

    return {}  # 僅回傳空資料，不提供任何可用預設帳號

def _check_credentials(input_username: str, input_password: str):
    authorized_users = _load_authorized_users()
    if not authorized_users:
        return False, "", "尚未設定 authorized_users（請在 secrets 或環境變數設定）"

    info = authorized_users.get(input_username)
    if not info:
        return False, "", "查無此使用者"

    if input_password != info.get("password", ""):
        return False, "", "密碼錯誤"

    # 日期區間可選，若缺值則視為通過（若要嚴格可改成必填）
    start = info.get("start_date")
    end   = info.get("end_date")
    if start and end:
        try:
            start_date = datetime.strptime(start, "%Y-%m-%d")
            end_date   = datetime.strptime(end,   "%Y-%m-%d")
            today = datetime.today()
            if not (start_date <= today <= end_date):
                return False, "", "您的使用權限尚未啟用或已過期"
        except Exception:
            return False, "", "帳號日期設定格式有誤（YYYY-MM-DD）"

    return True, info.get("name", input_username), ""

# ---------- Session 狀態 ----------
if "auth" not in st.session_state:
    st.session_state.auth = {
        "authenticated": False, "username": "", "name": "", "session_id": ""
    }

with right_col:
    if not st.session_state.auth["authenticated"]:
        with st.form("top_login_inline", clear_on_submit=False):
            c1, c2, c3 = st.columns([2, 2, 1])
            input_username = c1.text_input("帳號", placeholder="帳號", label_visibility="collapsed")
            input_password = c2.text_input("密碼", placeholder="密碼", type="password", label_visibility="collapsed")
            submitted = c3.form_submit_button("登入")
            if submitted:
                ok, name, msg = _check_credentials(input_username, input_password)
                if ok:
                    st.session_state.auth = {
                        "authenticated": True,
                        "username": input_username,
                        "name": name,
                        "session_id": uuid.uuid4().hex
                    }
                    st.success(f"登入成功！歡迎 {name} 😀")
                else:
                    st.error(msg or "登入失敗")
        # 額外提醒：若尚未設定 authorized_users，給清楚指引
        if not _load_authorized_users():
            st.info(
                "請在 `.streamlit/secrets.toml` 設定 authorized_users，或在環境變數設定 `AUTH_USERS_JSON`。\n\n"
                "範例 secrets.toml：\n"
                "[authorized_users.grace]\n"
                'password   = "YOUR_PASSWORD"\n'
                'name       = "Grace"\n'
                'start_date = "2024-01-01"\n'
                'end_date   = "2030-12-31"\n',
                icon="ℹ️"
            )
    else:
        colA, colB = st.columns([5, 1])
        with colA:
            st.markdown(
                f"<div style='text-align:right;font-size:14px;color:#333;'>歡迎 {st.session_state.auth['name']} 😀</div>",
                unsafe_allow_html=True
            )
        with colB:
            if st.button("登出", use_container_width=True):
                st.session_state.auth = {"authenticated": False, "username": "", "name": "", "session_id": ""}

st.markdown("<hr style='margin:6px 0 14px;'>", unsafe_allow_html=True)

# ---------- 兩個模組頁籤 ----------
tab1, tab2 = st.tabs(["AI秒算遺產稅", "保單贈與規劃"])

if not st.session_state.auth["authenticated"]:
    with tab1:
        st.info("此功能需登入後使用。請在右上角先登入。")
    with tab2:
        st.info("此功能需登入後使用。請在右上角先登入。")
else:
    with tab1:
        run_estate()
    with tab2:
        run_cvgift()
