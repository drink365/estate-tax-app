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

def _set_active_session(username: str, token: str, meta: dict):
    with _store_lock:
        store = _load_store()
        store[username] = {
            "token": token,
            "last_seen": int(time.time()),
            "meta": meta,
        }
        _save_store(store)

def _get_active_session(username: str):
    with _store_lock:
        store = _load_store()
        _cleanup_store(store)
        return store.get(username)

def _refresh_active_session(username: str, token: str):
    with _store_lock:
        store = _load_store()
        sess = store.get(username)
        if not sess:
            return False
        if sess.get("token") != token:
            return False
        sess["last_seen"] = int(time.time())
        _save_store(store)
        return True

def _invalidate_session(username: str):
    with _store_lock:
        store = _load_store()
        if username in store:
            store.pop(username)
            _save_store(store)

# --------------------------- Auth via ENV (TOML) ---------------------------

def _load_users(env_key: str = "AUTHORIZED_USERS"):
    """
    加強版載入邏輯：
    1) 優先讀取環境變數 AUTHORIZED_USERS（TOML 字串）
    2) 若無，再嘗試 st.secrets["AUTHORIZED_USERS"]：可為 TOML 字串或已解析的 dict
    3) 若還是無，再嘗試 st.secrets 直接含有 [authorized_users.*] 結構（dict）
    回傳：{ username_lower: {username, password, name, role, start_date, end_date} }
    """
    raw = os.environ.get(env_key, "")
    data = None

    # 1) 環境變數（TOML 字串）
    if isinstance(raw, str) and raw.strip():
        try:
            data = _toml.loads(raw.strip())
        except Exception as e:
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
                    st.error("授權設定（AUTHORIZED_USERS）格式錯誤（SECRETS 字串）。請確認為 TOML。")
                    st.stop()
            elif isinstance(sec, dict):
                data = dict(sec)  # 已是 dict 結構
            else:
                st.error("授權設定（AUTHORIZED_USERS）於 st.secrets 中格式不支援。")
                st.stop()

    # 3) 直接於 st.secrets 中的 [authorized_users.*]
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

    for key, info in auth.items():
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

    raw = os.environ.get(env_key, "").strip()
    if not raw:
        return {}
    try:
        data = _toml.loads(raw)
    except Exception as e:
        st.error("授權設定（AUTHORIZED_USERS）格式錯誤，請確認為 TOML。")
        st.stop()
    users = {}
    today = _dt.date.today()
    auth = data.get("authorized_users", {})
    if not isinstance(auth, dict):
        return {}
    for key, info in auth.items():
        try:
            username = str(info["username"]).strip()
            password = str(info["password"])
            name = str(info.get("name", username))
            start = _dt.date.fromisoformat(info.get("start_date", "1900-01-01"))
            end = _dt.date.fromisoformat(info.get("end_date", "2999-12-31"))
            role = str(info.get("role", "member"))
            if start <= today <= end:
                users[username] = {
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
    username = (username or '').strip().lower()
    u = users.get(username)
    if not u:
        return False, None
    if password != u["password"]:
        return False, None
    return True, u

def do_login(users: dict):
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

        active = _get_active_session(username)
        if active and not takeover:
            st.warning("此帳號目前已在其他裝置使用，若要登入請勾選『允許我搶下使用權』。")
            return

        token = secrets.token_urlsafe(24)
        st.session_state["authed"] = True
        st.session_state["user"] = info["name"]
        st.session_state["username"] = info["username"]
        st.session_state["role"] = info.get("role","member")
        st.session_state["start_date"] = info.get("start_date")
        st.session_state["end_date"] = info.get("end_date")
        st.session_state["session_token"] = token

        meta = {"ts": int(time.time())}
        _set_active_session(info["username"], token, meta)

        st.success(f"登入成功，歡迎 {info['name']}")
        st.rerun()

def ensure_auth():
    users = _load_users()
    if not st.session_state.get("authed"):
        do_login(users)
        return False

    user = st.session_state.get("username", "")
    token = st.session_state.get("session_token", "")
    if not user or not token:
        st.session_state.clear()
        do_login(users)
        return False

    active = _get_active_session(user)
    if not active or active.get("token") != token:
        st.warning("此帳號已在其他裝置登入，您已被登出。")
        st.session_state.clear()
        do_login(users)
        return False

    _refresh_active_session(user, token)
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
# --------------------------- 顯示登入資訊（右上角） ---------------------------
with st.container():
    col1, col2 = st.columns([8,2])
    with col2:
        exp_date = st.session_state.get("end_date")
        exp_str = exp_date.strftime("%Y-%m-%d") if exp_date else "N/A"
        st.caption(f"歡迎，{st.session_state.get('user','')}｜有效期限至 {exp_str}")
        if st.button("登出", key="top_logout", use_container_width=True):
            try:
                _invalidate_session(st.session_state.get("username",""))
            except Exception:
                pass
            st.session_state.clear()
            st.rerun()


if not ensure_auth():
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
    st.caption(f"會話將在無操作 {int(os.environ.get('SESSION_TTL_SECONDS','1800'))//60} 分鐘後自動過期")
    colA, colB = st.columns(2)
    with colA:
        if st.button("強制登出此帳號的其他裝置", use_container_width=True):
            # 清除此用戶所有活躍會話（踢掉別處）
            try:
                _invalidate_session(st.session_state.get("username",""))
            except Exception:
                pass
            st.success("已登出其他裝置。")
            st.rerun()
    with colB:
        if st.button("登出", type="secondary", use_container_width=True):
            try:
                _invalidate_session(st.session_state.get("username",""))
            except Exception:
                pass
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
