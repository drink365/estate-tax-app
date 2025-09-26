
# app.py — 影響力傳承策略平台（單一登入：後登入踢前者；bcrypt；logo 36px）
import os, uuid, base64, json, hmac
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any
from PIL import Image
import streamlit as st
import bcrypt

from modules.wrapped_estate import run_estate
from modules.wrapped_cvgift import run_cvgift
from modules.session_registry import SessionRegistry

BASE_DIR = Path(__file__).resolve().parent
ASSETS_DIR = BASE_DIR / "assets"
DATA_DIR = BASE_DIR / ".data"
REGISTRY = SessionRegistry(str(DATA_DIR / "sessions.db"))

def _asset_path(name: str) -> str: return str(ASSETS_DIR / name)

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

def _load_users_from_secrets() -> Dict[str, Any]:
    try:
        return dict(st.secrets.get("users", {}))  # 使用 [users] 節，僅存 bcrypt 雜湊
    except Exception:
        return {}

def _check_password(pwd_plain: str, pwd_hash: str) -> bool:
    try:
        return bcrypt.checkpw(pwd_plain.encode(), pwd_hash.encode())
    except Exception:
        return False

def _check_credentials(username: str, password: str):
    users = _load_users_from_secrets()
    if not users:
        return False, "", "尚未設定 users（請在 secrets 設定 bcrypt 雜湊）"
    info = users.get(username)
    if not info:
        return False, "", "查無此使用者"
    if not _check_password(password, info.get("pwd_hash", "")):
        return False, "", "帳密錯誤"
    s, e = info.get("start_date"), info.get("end_date")
    if s and e:
        try:
            start_date = datetime.fromisoformat(s); end_date = datetime.fromisoformat(e)
            if not (start_date <= datetime.today() <= end_date):
                return False, "", "權限尚未啟用或已過期"
        except Exception:
            return False, "", "日期格式錯誤（YYYY-MM-DD）"
    return True, info.get("name", username), ""

if "auth" not in st.session_state:
    st.session_state.auth = {"authenticated": False, "username": "", "name": "", "session_id": ""}

with right_col:
    if not st.session_state.auth["authenticated"]:
        with st.form("top_login_inline", clear_on_submit=False):
            c1, c2, c3 = st.columns([2, 2, 1])
            u = c1.text_input("帳號", placeholder="帳號", label_visibility="collapsed")
            p = c2.text_input("密碼", placeholder="密碼", type="password", label_visibility="collapsed")
            ok_btn = c3.form_submit_button("登入")
            if ok_btn:
                ok, display, msg = _check_credentials(u, p)
                if ok:
                    new_sid = uuid.uuid4().hex
                    REGISTRY.upsert(u, new_sid)  # 單一登入：覆寫舊 session（踢掉前一個）
                    REGISTRY.cleanup_expired()
                    st.session_state.auth = {"authenticated": True, "username": u, "name": display, "session_id": new_sid}
                    st.success(f"登入成功！歡迎 {display} 😀")
                else:
                    st.error(msg or "登入失敗")
    else:
        colA, colB = st.columns([5, 1])
        with colA:
            st.markdown(f"<div style='text-align:right;font-size:14px;color:#333;'>歡迎 {st.session_state.auth['name']} 😀</div>", unsafe_allow_html=True)
        with colB:
            if st.button("登出", use_container_width=True):
                from modules.session_registry import SessionRegistry  # re-import safe
                REGISTRY.delete_if_match(st.session_state.auth["username"], st.session_state.auth["session_id"])
                st.session_state.auth = {"authenticated": False, "username": "", "name": "", "session_id": ""}

def _guard_session():
    auth = st.session_state.auth
    if not auth["authenticated"]:
        return
    row = REGISTRY.get(auth["username"])
    if not row:
        st.warning("你的登入已失效，請重新登入。"); st.session_state.auth = {"authenticated": False, "username": "", "name": "", "session_id": ""}; st.stop()
    reg_sid, last_seen = row
    if not hmac.compare_digest(reg_sid, auth["session_id"]):
        st.warning("你已在其他裝置登入，已將此處登出。"); st.session_state.auth = {"authenticated": False, "username": "", "name": "", "session_id": ""}; st.stop()
    REGISTRY.touch(auth["username"]); REGISTRY.cleanup_expired()

_guard_session()

st.markdown("<hr style='margin:6px 0 14px;'>", unsafe_allow_html=True)

tab1, tab2 = st.tabs(["AI秒算遺產稅", "保單贈與規劃"])

if not st.session_state.auth["authenticated"]:
    with tab1: st.info("此功能需登入後使用。請在右上角先登入。")
    with tab2: st.info("此功能需登入後使用。請在右上角先登入。")
else:
    with tab1: run_estate()
    with tab2: run_cvgift()
