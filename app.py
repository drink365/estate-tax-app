# app.py — 影響力傳承策略平台（主入口）
import os
import time
import uuid
import base64
from PIL import Image
from datetime import datetime
import streamlit as st

from pathlib import Path
from typing import Optional

# === 子模組 ===
from modules.wrapped_estate import run_estate
from modules.wrapped_cvgift import run_cvgift

# ======================================================
# 0) 資產路徑與 Page Config（保證 Logo / Favicon 顯示）
# ======================================================

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

st.set_page_config(
    page_title="影響力傳承策略平台",
    page_icon=Image.open(_asset_path("logo2.png")) if os.path.exists(_asset_path("logo2.png"))
              else (Image.open(_asset_path("logo.png")) if os.path.exists(_asset_path("logo.png")) else "🧭"),
    layout="wide"
)

# ======================================================
# 1) 單一登入機制（後登入踢掉前登入）
# ======================================================
@st.cache_resource
def _session_registry():
    return {}

REG = _session_registry()
SESSION_TIMEOUT_SECS = 60 * 60

def _now(): return time.time()
def _cleanup():
    now = _now()
    for u in list(REG.keys()):
        if now - REG[u].get("last_seen", 0) > SESSION_TIMEOUT_SECS:
            REG.pop(u, None)

def _touch(u, sid): REG[u] = {"session_id": sid, "last_seen": _now()}
def _valid(u, sid): 
    r = REG.get(u)
    return r and r["session_id"] == sid and _now() - r["last_seen"] <= SESSION_TIMEOUT_SECS
def _logout(u): REG.pop(u, None)

_cleanup()

# ======================================================
# 2) 授權名單（以 st.secrets 優先）
# ======================================================
try:
    import tomllib as toml
except Exception:
    import toml

def _parse_users_from_toml_str(toml_str: str) -> dict:
    if not toml_str.strip(): return {}
    return toml.loads(toml_str).get("authorized_users", {})

def _read_authorized_users_raw() -> dict:
    au = st.secrets.get("authorized_users", None)
    if isinstance(au, dict) and au: return au
    env_str = os.environ.get("AUTHORIZED_USERS", "")
    if env_str.strip(): return _parse_users_from_toml_str(env_str)
    return {}

def _load_users_from_sources():
    users = {}
    raw = _read_authorized_users_raw()
    for section_name, d in raw.items():
        if not isinstance(d, dict): continue
        username = d.get("username", section_name)
        pwd_env = os.environ.get(f"AUTH_{username.upper()}_PASSWORD")
        users[username] = {
            "name": d.get("name", username),
            "username": username,
            "password": pwd_env if pwd_env else d.get("password", ""),
            "start_date": d.get("start_date", "1970-01-01"),
            "end_date": d.get("end_date", "2099-12-31"),
            "role": d.get("role", "member"),
        }
    return users

USERS = _load_users_from_sources()

def check_credentials(input_username: str, input_password: str):
    info = USERS.get(input_username)
    if not info: return False, None, "查無此使用者"
    if input_password != info["password"]: return False, None, "密碼錯誤"
    today = datetime.today().date()
    try:
        start_date = datetime.strptime(info["start_date"], "%Y-%m-%d").date()
        end_date = datetime.strptime(info["end_date"], "%Y-%m-%d").date()
        if not (start_date <= today <= end_date):
            return False, None, "帳號已過期或尚未啟用"
    except Exception:
        return False, None, "帳號日期設定有誤"
    return True, info, ""

# ======================================================
# 3) Logo 與標題
# ======================================================
st.markdown("""
<style>
.header { display:flex; align-items:center; justify-content:space-between; gap:12px; }
.brand { display:flex; align-items:center; gap:14px; }
.brand-title { margin:0; font-size:22px; color:#000; line-height:1; }  /* 縮小一號 */
.brand-logo { height:36px; image-rendering:auto; }
@media (max-width:1200px){ .brand-logo{ height:30px; } .brand-title{ font-size:20px; } }
@media (max-width:768px){  .brand-logo{ height:26px; } .brand-title{ font-size:18px; } }
.header-right { display:flex; align-items:center; gap:8px; }
</style>
""", unsafe_allow_html=True)

b64_1x = _asset_b64("logo.png")
b64_2x = _asset_b64("logo@2x.png")
if b64_2x and b64_1x:
    logo_img_tag = f"<img src='data:image/png;base64,{b64_1x}' srcset='data:image/png;base64,{b64_1x} 1x, data:image/png;base64,{b64_2x} 2x' class='brand-logo'>"
elif b64_1x:
    logo_img_tag = f"<img src='data:image/png;base64,{b64_1x}' class='brand-logo'>"
else:
    logo_img_tag = f"<img src='{_asset_path('logo.png')}' class='brand-logo'>"

st.markdown("<div class='header'>", unsafe_allow_html=True)
st.markdown(f"<div class='brand'>{logo_img_tag}<h1 class='brand-title'>影響力傳承策略平台</h1></div>", unsafe_allow_html=True)
right_col = st.container()
st.markdown("</div>", unsafe_allow_html=True)

# ======================================================
# 4) 登入/登出
# ======================================================
if "auth" not in st.session_state:
    st.session_state.auth = {"authenticated": False}

if st.session_state.auth.get("authenticated"):
    u, sid = st.session_state.auth["username"], st.session_state.auth["session_id"]
    if not _valid(u, sid):
        st.session_state.auth = {"authenticated": False}
        st.warning("此帳號已在其他裝置登入，您已被登出。")
    else:
        _touch(u, sid)

with right_col:
    if not st.session_state.auth.get("authenticated"):
        with st.form("top_login_inline", clear_on_submit=False):
            c1, c2, c3 = st.columns([2, 2, 1])
            input_username = c1.text_input("帳號", placeholder="帳號", label_visibility="collapsed")
            input_password = c2.text_input("密碼", placeholder="密碼", type="password", label_visibility="collapsed")
            submitted = c3.form_submit_button("登入")
            if submitted:
                ok, info, msg = check_credentials(input_username, input_password)
                if ok:
                    sid = uuid.uuid4().hex
                    _touch(input_username, sid)
                    st.session_state.auth = {
                        "authenticated": True,
                        "username": input_username,
                        "name": info["name"],
                        "role": info["role"],
                        "end_date": info["end_date"],
                        "session_id": sid
                    }
                    st.success(f"登入成功！歡迎 {info['name']} 😀")
                else:
                    st.error(msg)
    else:
        colA, colB = st.columns([5, 1])
        with colA:
            st.markdown(
                f"<div style='text-align:right;font-size:14px;color:#333;'>"
                f"歡迎 {st.session_state.auth['name']} 😀｜有效期限至 {st.session_state.auth['end_date']}"
                f"</div>", unsafe_allow_html=True
            )
        with colB:
            if st.button("登出", use_container_width=True):
                _logout(st.session_state.auth["username"])
                st.session_state.auth = {"authenticated": False}

st.markdown("<hr style='margin-top:6px;margin-bottom:14px;'>", unsafe_allow_html=True)

# ======================================================
# 5) 子模組頁籤
# ======================================================
tab1, tab2 = st.tabs(["AI秒算遺產稅", "保單贈與規劃"])

if not st.session_state.auth.get("authenticated"):
    with tab1: st.info("此功能需登入後使用。請在右上角先登入。")
    with tab2: st.info("此功能需登入後使用。請在右上角先登入。")
else:
    with tab1: run_estate()
    with tab2: run_cvgift()
