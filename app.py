
import time
import uuid
from datetime import datetime
from pathlib import Path

import streamlit as st

st.set_page_config(
    page_title="影響力傳承策略平台",
    page_icon="assets/logo2.png",
    layout="wide"
)

from modules.wrapped_estate import run_estate
from modules.wrapped_cvgift import run_cvgift

@st.cache_resource
def _session_registry():
    return {}

REG = _session_registry()
SESSION_TIMEOUT_SECS = 60 * 60  # 60 分鐘

def _now_epoch():
    return time.time()

def _cleanup_expired_sessions():
    now = _now_epoch()
    for u in list(REG.keys()):
        last = REG[u].get("last_seen", 0)
        if now - last > SESSION_TIMEOUT_SECS:
            REG.pop(u, None)

def _touch_session(username_key: str, session_id: str):
    REG[username_key] = {"session_id": session_id, "last_seen": _now_epoch()}

def _is_active_session(username_key: str, session_id: str) -> bool:
    rec = REG.get(username_key)
    if not rec:
        return False
    if rec.get("session_id") != session_id:
        return False
    if _now_epoch() - rec.get("last_seen", 0) > SESSION_TIMEOUT_SECS:
        return False
    return True

def _logout_session(username_key: str):
    REG.pop(username_key, None)

def _lookup_user_case_insensitive(au: dict, input_username: str):
    cleaned = (input_username or "").strip()
    if cleaned in au:
        return cleaned, au[cleaned]
    lowered = {k.lower(): k for k in au.keys()}
    real_key = lowered.get(cleaned.lower())
    if real_key:
        return real_key, au[real_key]
    return None, None

def check_credentials(input_username: str, input_password: str):
    au = st.secrets.get("authorized_users", {})
    if not isinstance(au, dict) or not au:
        return False, None, None, "尚未設定授權名單（authorized_users）。請在部署環境的 secrets 設定。"

    uname_key, user_info = _lookup_user_case_insensitive(au, input_username)
    if not user_info:
        return False, None, None, "查無此使用者"

    if (input_password or "").strip() != (user_info.get("password") or ""):
        return False, None, None, "密碼錯誤"

    # 檢查有效日期（含當日）
    try:
        start_date = datetime.strptime(user_info["start_date"], "%Y-%m-%d").date()
        end_date   = datetime.strptime(user_info["end_date"],   "%Y-%m-%d").date()
        today      = datetime.today().date()
        if not (start_date <= today <= end_date):
            return False, None, None, f"帳號已不在有效期間（{start_date} ~ {end_date}）"
    except Exception:
        return False, None, None, "使用者日期格式錯誤（需 YYYY-MM-DD）"

    return True, uname_key, user_info, None

# Header
top = st.container()
with top:
    logo_col, title_col, user_col = st.columns([1, 8, 6], gap="small")

    with logo_col:
        try:
            st.image("assets/logo.png", use_container_width=True)
            st.markdown("""
                <style>
                [data-testid="stImage"] img {max-height: 48px; object-fit: contain;}
                </style>
            """, unsafe_allow_html=True)
        except Exception:
            st.write("")

    with title_col:
        st.markdown(
            "<div style='display:flex;align-items:center;gap:12px;'>"
            "<h1 style='margin:0;font-size:26px;color:#000;'>影響力傳承策略平台</h1>"
            "</div>",
            unsafe_allow_html=True
        )

    if "auth" not in st.session_state:
        st.session_state.auth = {
            "authenticated": False,
            "username_key": "",   # 真正用於註冊的 key（大小寫不敏感）
            "display_name": "",   # 顯示用名字
            "role": "",
            "end_date": "",
            "session_id": "",
            "kicked": False,
        }

    with user_col:
        st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)
        if not st.session_state.auth["authenticated"]:
            with st.form("login_form", clear_on_submit=False):
                u = st.text_input("帳號", value="", placeholder="請輸入帳號（大小寫不拘）")
                p = st.text_input("密碼", value="", type="password", placeholder="請輸入密碼")
                login = st.form_submit_button("登入")
                if login:
                    ok, uname_key, info, err = check_credentials(u, p)
                    if not ok:
                        st.error(err or "登入失敗")
                    else:
                        sid = uuid.uuid4().hex
                        _touch_session(uname_key, sid)   # 覆蓋舊 session（後登入踢掉前登入）

                        st.session_state.auth.update({
                            "authenticated": True,
                            "username_key": uname_key,
                            "display_name": info.get("name", uname_key),
                            "role": info.get("role", ""),
                            "end_date": info.get("end_date", ""),
                            "session_id": sid,
                            "kicked": False,
                        })
                        st.success("登入成功")
                        st.experimental_rerun()
        else:
            auth = st.session_state.auth
            st.write(f"**歡迎，{auth.get('display_name')}**（{auth.get('role','')}）｜有效至：{auth.get('end_date','')}")
            if st.button("登出", key="logout_btn"):
                _logout_session(auth["username_key"] or "")
                st.session_state.auth = {
                    "authenticated": False,
                    "username_key": "",
                    "display_name": "",
                    "role": "",
                    "end_date": "",
                    "session_id": "",
                    "kicked": False,
                }
                st.experimental_rerun()

# Heartbeat & kick-out check
_cleanup_expired_sessions()
if st.session_state.auth["authenticated"]:
    uname_key = st.session_state.auth["username_key"]
    sid = st.session_state.auth["session_id"]
    if not _is_active_session(uname_key, sid):
        st.session_state.auth["authenticated"] = False
        st.session_state.auth["kicked"] = True
    else:
        _touch_session(uname_key, sid)

if st.session_state.auth.get("kicked"):
    st.warning("此帳號已於其他裝置登入，您已被登出。")
    st.session_state.auth = {
        "authenticated": False,
        "username_key": "",
        "display_name": "",
        "role": "",
        "end_date": "",
        "session_id": "",
        "kicked": False,
    }

# Main tabs
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
