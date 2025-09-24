import os
import json
import time
import secrets
import datetime as _dt
import threading
import streamlit as st

# Try tomllib (Py3.11+), fallback to tomli
try:
    import tomllib as _toml
except Exception:
    import tomli as _toml  # type: ignore

from modules.wrapped_estate import run_estate
from modules.wrapped_cvgift import run_cvgift

st.set_page_config(page_title="《影響力》傳承策略平台 | 整合版", layout="wide")

# --------------------------- Config ---------------------------
SESSION_STORE_PATH = os.environ.get("SESSION_STORE_PATH", ".sessions.json")
SESSION_TTL_SECONDS = int(os.environ.get("SESSION_TTL_SECONDS", "1800"))  # 30 分鐘無操作即過期
ALLOW_TAKEOVER = True  # 允許「搶下使用權」以登出其它裝置

# --------------------------- 授權診斷（可選） ---------------------------
def _auth_debug_panel(users: dict, place: str = "sidebar"):
    if os.environ.get("AUTH_DEBUG", "0") != "1":
        return
    panel = st.sidebar if place == "sidebar" else st
    with panel.expander("🔧 授權診斷（僅在 AUTH_DEBUG=1 時顯示）", expanded=False):
        if not users:
            st.warning("目前未載入到任何使用者。請檢查 AUTHORIZED_USERS 設定。")
        else:
            rows = []
            for k, v in users.items():
                rows.append({
                    "username_key": k,
                    "username": v.get("username"),
                    "name": v.get("name"),
                    "role": v.get("role"),
                    "start_date": v.get("start_date"),
                    "end_date": v.get("end_date"),
                })
            st.dataframe(rows, use_container_width=True)

# --------------------------- Session Store ---------------------------
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
    users = list(store.keys())
    changed = False
    for u in users:
        sess = store.get(u, {})
        last_seen = int(sess.get("last_seen", 0))
        if now - last_seen > SESSION_TTL_SECONDS:
            store.pop(u, None)
            changed = True
    if changed:
        _save_store(store)

def _set_active_session(username_l: str, token: str, meta: dict):
    with _store_lock:
        store = _load_store()
        store[username_l] = {
            "token": token,
            "last_seen": int(time.time()),
            "meta": meta,
        }
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
        if not sess:
            return False
        if sess.get("token") != token:
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

# --------------------------- Auth Loader（ENV / SECRETS） ---------------------------
def _load_users(env_key: str = "AUTHORIZED_USERS"):
    """
    讀取授權使用者：
    1) 環境變數 AUTHORIZED_USERS（TOML 字串）
    2) st.secrets["AUTHORIZED_USERS"]（TOML 字串或 dict）
    3) st.secrets 根層含 authorized_users 字典
    回傳：{ username_lower: {...} }
    """
    raw = os.environ.get(env_key, "")
    data = None

    # 1) ENV：TOML 字串
    if isinstance(raw, str) and raw.strip():
        try:
            data = _toml.loads(raw.strip())
        except Exception:
            st.error("授權設定（AUTHORIZED_USERS）格式錯誤（ENV）。請確認為 TOML。")
            st.stop()

    # 2) st.secrets["AUTHORIZED_USERS"]
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

    # 3) 根層含 authorized_users
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
            password = str(info["password"])
            name = str(info.get("name", username))
            role = str(info.get("role", "member"))
            start = _dt.date.fromisoformat(info.get("start_date", "1900-01-01"))
            end = _dt.date.fromisoformat(info.get("end_date", "2999-12-31"))
            if start <= today <= end:
                users[username_l] = {
                    "username": username,
                    "password": password,
                    "name": name,
                    "role": role,
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

# --------------------------- Login Flow ---------------------------
def do_login(users: dict):
    _auth_debug_panel(users, place='main')

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
        st.session_state["authed"] = True
        st.session_state["user"] = info["name"]
        st.session_state["username"] = info["username"]           # 原始大小寫
        st.session_state["username_l"] = username_l               # 小寫供會話管理
        st.session_state["role"] = info.get("role","member")
        st.session_state["start_date"] = info.get("start_date")
        st.session_state["end_date"] = info.get("end_date")
        st.session_state["session_token"] = token

        meta = {"ts": int(time.time())}
        _set_active_session(username_l, token, meta)

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
    _auth_debug_panel(users, place='sidebar')
    if not active or active.get("token") != token:
        st.warning("此帳號已在其他裝置登入，您已被登出。")
        st.session_state.clear()
        do_login(users)
        return False

    _refresh_active_session(user_l, token)
    return True

# --------------------------- UI ---------------------------
brand_col1, brand_col2 = st.columns([1,5])
with brand_col1:
    try:
        st.image("assets/logo.png", caption=None, use_container_width=True)
    except Exception:
        pass
with brand_col2:
    st.title("《影響力》傳承策略平台｜整合版")
    st.caption("專業 × 溫度 × 智能｜Estate Tax Simulator + 保單贈與規劃")

st.divider()

# 右上角（其實是同一行靠左）：歡迎｜有效期限｜登出（單行顯示）
if ensure_auth():
    exp_date = st.session_state.get("end_date")
    exp_str = exp_date.strftime("%Y-%m-%d") if isinstance(exp_date, _dt.date) else "N/A"
    name = st.session_state.get("user", "")

    # 建立三欄，前兩欄放資訊與按鈕，第三欄空白用來保持「靠左單行」
    bar_col1, bar_col2, _ = st.columns([8, 1.5, 10])
    with bar_col1:
        st.markdown(
            f"""
            <div style="display:flex;align-items:center;gap:0.75rem;font-size:0.9rem;color:#6b7280;">
                <span>歡迎，{name}｜有效期限至 {exp_str}</span>
            </div>
            """,
            unsafe_allow_html=True
        )
    with bar_col2:
        if st.button("登出", key="top_logout", use_container_width=True):
            try:
                _invalidate_session((st.session_state.get("username_l","") or "").strip().lower())
            except Exception:
                pass
            st.session_state.clear()
            st.rerun()
else:
    st.stop()

# Sidebar Navigation
st.sidebar.header("功能選單")
page = st.sidebar.radio(
    "請選擇",
    ["🏛️ 遺產稅試算（Estate Tax）", "🎁 保單贈與規劃（CVGift）"],
    index=0,
    label_visibility="collapsed"
)

st.sidebar.markdown("---")
st.sidebar.write("付費會員限定功能")
with st.sidebar.expander("帳號管理", expanded=False):
    st.write(f"目前帳號：**{st.session_state.get('user','')}**（角色：{st.session_state.get('role','member')}）")
    st.caption(f"會話將在無操作 {SESSION_TTL_SECONDS//60} 分鐘後自動過期")
    colA, colB = st.columns(2)
    with colA:
        if st.button("強制登出此帳號的其他裝置", use_container_width=True):
            _invalidate_session((st.session_state.get("username_l","") or "").strip().lower())
            st.success("已登出其他裝置。")
            st.rerun()
    with colB:
        if st.button("登出", type="secondary", use_container_width=True):
            _invalidate_session((st.session_state.get("username_l","") or "").strip().lower())
            st.session_state.clear()
            st.rerun()

# Route to chosen module
if page.startswith("🏛️"):
    run_estate()
elif page.startswith("🎁"):
    st.markdown("#### 保單贈與規劃")
    run_cvgift()
else:
    st.info("請從左側選單選擇功能")

# Footer
st.markdown("---")
st.caption("《影響力》傳承策略平台｜永傳家族辦公室  ｜ 聯絡信箱：123@gracefo.com")
