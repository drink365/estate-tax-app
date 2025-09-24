import os
import json
import time
import secrets
import datetime as _dt
import threading
import streamlit as st

# tomllib / tomli for TOML parsing
try:
    import tomllib as _toml
except Exception:
    import tomli as _toml  # type: ignore

from modules.wrapped_estate import run_estate
from modules.wrapped_cvgift import run_cvgift

# ------------------------------------------------------------
# Page config (favicon = logo2.png)
# ------------------------------------------------------------
st.set_page_config(
    page_title="《影響力》傳承策略平台 | 整合版",
    layout="wide",
    page_icon="assets/logo2.png",
)

# ------------------------------------------------------------
# Global Config
# ------------------------------------------------------------
SESSION_STORE_PATH = os.environ.get("SESSION_STORE_PATH", ".sessions.json")
SESSION_TTL_SECONDS = int(os.environ.get("SESSION_TTL_SECONDS", "3600"))  # 60 分鐘
ALLOW_TAKEOVER = True

# ------------------------------------------------------------
# Small CSS (壓縮頁首高度、避免標題被覆蓋)
# ------------------------------------------------------------
st.markdown(
    """
<style>
/* 壓縮 Streamlit 全域標題與間距 */
h1, h2, .stTitle { margin-top: 0.2rem !important; margin-bottom: 0.2rem !important; }
/* 頁首 Logo 尺寸（固定寬度，避免過高） */
.header-logo { height: 56px; }

/* Tabs 風格微調 */
.stTabs [role="tablist"] { gap: 2rem; }
.stTabs [role="tab"] { font-size: 1.05rem; padding: 0.5rem 0.25rem; }

/* 頂部資訊列字色 */
.topbar { display:flex; align-items:center; gap:0.75rem; font-size:0.95rem; color:#6b7280; }
</style>
""",
    unsafe_allow_html=True,
)

# ------------------------------------------------------------
# Session store helpers (單一登入 + 逾時)
# ------------------------------------------------------------
_store_lock = threading.Lock()

def _load_store() -> dict:
    if not os.path.exists(SESSION_STORE_PATH):
        return {}
    try:
        with open(SESSION_STORE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def _save_store(store: dict):
    tmp = SESSION_STORE_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(store, f, ensure_ascii=False, indent=2)
    os.replace(tmp, SESSION_STORE_PATH)

def _cleanup_store(store: dict):
    now = int(time.time())
    changed = False
    for u in list(store.keys()):
        last_seen = int(store[u].get("last_seen", 0))
        if now - last_seen > SESSION_TTL_SECONDS:
            store.pop(u, None)
            changed = True
    if changed:
        _save_store(store)

def _set_active_session(username_l: str, token: str, meta: dict):
    with _store_lock:
        store = _load_store()
        store[username_l] = {"token": token, "last_seen": int(time.time()), "meta": meta}
        _save_store(store)

def _get_active_session(username_l: str):
    with _store_lock:
        store = _load_store()
        _cleanup_store(store)
        return store.get(username_l)

def _refresh_active_session(username_l: str, token: str):
    with _store_lock:
        store = _load_store()
        sess = store.get(username_l)
        if not sess or sess.get("token") != token:
            return False
        sess["last_seen"] = int(time.time())
        _save_store(store)
        return True

def _invalidate_session(username_l: str):
    with _store_lock:
        store = _load_store()
        if username_l in store:
            store.pop(username_l)
            _save_store(store)

# ------------------------------------------------------------
# Load users from ENV / secrets (TOML)
# ------------------------------------------------------------
def _load_users(env_key: str = "AUTHORIZED_USERS"):
    raw = os.environ.get(env_key, "")
    data = None

    if isinstance(raw, str) and raw.strip():
        try:
            data = _toml.loads(raw.strip())
        except Exception:
            st.error("授權設定（AUTHORIZED_USERS）格式錯誤（ENV）。請確認為 TOML。")
            st.stop()

    if data is None:
        try:
            sec = st.secrets.get("AUTHORIZED_USERS", None)
        except Exception:
            sec = None
        if sec:
            if isinstance(sec, str):
                try:
                    data = _toml.loads(sec.strip())
                except Exception:
                    st.error("授權設定（AUTHORIZED_USERS）格式錯誤（SECRETS 字串）。")
                    st.stop()
            elif isinstance(sec, dict):
                data = dict(sec)
            else:
                st.error("授權設定（AUTHORIZED_USERS）於 st.secrets 中格式不支援。")
                st.stop()

    if data is None:
        try:
            maybe = dict(st.secrets)
            if "authorized_users" in maybe:
                data = maybe
        except Exception:
            pass

    if data is None:
        return {}

    users = {}
    today = _dt.date.today()
    auth = data.get("authorized_users", {})
    if not isinstance(auth, dict):
        return {}

    for _key, info in auth.items():
        try:
            username = str(info["username"]).strip()
            username_l = username.lower()
            name = str(info.get("name", username))
            role = str(info.get("role", "member"))
            password = str(info["password"])
            start = _dt.date.fromisoformat(info.get("start_date", "1900-01-01"))
            end = _dt.date.fromisoformat(info.get("end_date", "2999-12-31"))
            if start <= today <= end:
                users[username_l] = {
                    "username": username,
                    "name": name,
                    "role": role,
                    "password": password,
                    "start_date": start,
                    "end_date": end,
                }
        except Exception:
            continue
    return users

def _check_login(username: str, password: str, users: dict):
    username = (username or "").strip().lower()
    u = users.get(username)
    if not u:
        return False, None
    if password != u["password"]:
        return False, None
    return True, u

# ------------------------------------------------------------
# Auth flow (no sidebar)
# ------------------------------------------------------------
def _auth_debug_panel(users: dict):
    if os.environ.get("AUTH_DEBUG", "0") != "1":
        return
    with st.expander("🔧 授權診斷（僅在 AUTH_DEBUG=1 顯示）", expanded=False):
        st.dataframe(
            [
                {
                    "username_key": k,
                    "username": v.get("username"),
                    "name": v.get("name"),
                    "role": v.get("role"),
                    "start_date": v.get("start_date"),
                    "end_date": v.get("end_date"),
                }
                for k, v in users.items()
            ],
            use_container_width=True,
        )

def do_login(users: dict):
    _auth_debug_panel(users)

    st.markdown("### 會員登入")
    with st.form("login_form", clear_on_submit=False):
        username = st.text_input("帳號", value="", autocomplete="username")
        password = st.text_input("密碼", type="password", value="", autocomplete="current-password")
        takeover = st.checkbox("若此帳號已在其他裝置登入，允許我搶下使用權（登出他人）", value=True)
        submitted = st.form_submit_button("登入")
    if submitted:
        ok, info = _check_login(username, password, users)
        if not ok:
            st.error("帳號或密碼錯誤，或帳號已過期")
            return

        username_l = info["username"].strip().lower()
        active = _get_active_session(username_l)
        if active and not takeover:
            st.warning("此帳號目前已在其他裝置使用，若要登入請勾選『允許我搶下使用權』。")
            return

        token = secrets.token_urlsafe(24)
        st.session_state.update(
            {
                "authed": True,
                "user": info["name"],
                "username": info["username"],
                "username_l": username_l,
                "role": info.get("role", "member"),
                "start_date": info.get("start_date"),
                "end_date": info.get("end_date"),
                "session_token": token,
            }
        )
        _set_active_session(username_l, token, {"ts": int(time.time())})
        st.success(f"登入成功，歡迎 {info['name']}")
        st.rerun()

def ensure_auth():
    users = _load_users()
    if not st.session_state.get("authed"):
        do_login(users)
        return False

    user_l = (st.session_state.get("username_l", "") or "").strip().lower()
    token = st.session_state.get("session_token", "")
    if not user_l or not token:
        st.session_state.clear()
        do_login(users)
        return False

    active = _get_active_session(user_l)
    _auth_debug_panel(users)
    if not active or active.get("token") != token:
        st.warning("此帳號已在其他裝置登入，您已被登出。")
        st.session_state.clear()
        do_login(users)
        return False

    _refresh_active_session(user_l, token)
    return True

# ------------------------------------------------------------
# Header: Logo(logo.png) + Title 同一行
# ------------------------------------------------------------
col1, col2 = st.columns([1, 6], vertical_alignment="center")
with col1:
    try:
        st.image("assets/logo.png", use_container_width=False, output_format="PNG", caption=None, width=150)
    except Exception:
        st.write("")  # 安靜略過
with col2:
    st.markdown(
        "<h2 style='margin:0;'>《影響力》傳承策略平台｜整合版</h2>"
        "<p style='margin:0;color:#6b7280;font-size:0.95rem;'>專業 × 溫度 × 智能｜Estate Tax Simulator + 保單贈與規劃</p>",
        unsafe_allow_html=True,
    )

st.divider()

# ------------------------------------------------------------
# Top info bar: 歡迎｜有效期限｜登出（單行靠左）
# ------------------------------------------------------------
if ensure_auth():
    exp_date = st.session_state.get("end_date")
    exp_str = exp_date.strftime("%Y-%m-%d") if isinstance(exp_date, _dt.date) else "N/A"
    name = st.session_state.get("user", "")

    info_col1, info_col2, _ = st.columns([8, 1.5, 10], vertical_alignment="center")
    with info_col1:
        st.markdown(f"<div class='topbar'>歡迎，{name}｜有效期限至 {exp_str}</div>", unsafe_allow_html=True)
    with info_col2:
        if st.button("登出", key="top_logout", use_container_width=True):
            try:
                _invalidate_session((st.session_state.get("username_l","") or "").strip().lower())
            except Exception:
                pass
            st.session_state.clear()
            st.rerun()
else:
    st.stop()

# ------------------------------------------------------------
# Top Tabs（取代側邊欄）
# ------------------------------------------------------------
tabs = st.tabs(["🏛️ 遺產稅試算（AI秒算遺產稅）", "🎁 保單贈與規劃（CVGift）"])

with tabs[0]:
    try:
        run_estate()
    except Exception as e:
        st.error(f"載入遺產稅模組時發生錯誤：{e}")

with tabs[1]:
    try:
        run_cvgift()
    except Exception as e:
        st.error(f"載入保單贈與模組時發生錯誤：{e}")

# ------------------------------------------------------------
# Footer
# ------------------------------------------------------------
st.markdown("---")
st.caption("《影響力》傳承策略平台｜永傳家族辦公室  ｜ 聯絡信箱：123@gracefo.com")
