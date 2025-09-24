import os
import datetime as _dt
import streamlit as st

# Try tomllib (Py3.11+), fallback to tomli
try:
    import tomllib as _toml
except Exception:
    import tomli as _toml  # type: ignore

from modules.wrapped_estate import run_estate
from modules.wrapped_cvgift import run_cvgift

st.set_page_config(page_title="《影響力》傳承策略平台 | 整合版", layout="wide")

# --------------------------- Auth via ENV (TOML) ---------------------------
def _load_users_from_env(env_key: str = "AUTHORIZED_USERS"):
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
            if start <= today <= end:
                users[username] = {
                    "username": username,
                    "password": password,
                    "name": name,
                    "start_date": start,
                    "end_date": end,
                }
        except Exception:
            continue
    return users

def _check_login(username: str, password: str, users: dict):
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
        submitted = st.form_submit_button("登入")
    if submitted:
        ok, info = _check_login(username, password, users)
        if ok:
            st.session_state["authed"] = True
            st.session_state["user"] = info["name"]
            st.session_state["username"] = info["username"]
            st.success(f"登入成功，歡迎 {info['name']}")
            st.rerun()
        else:
            st.error("帳號或密碼錯誤，或帳號已過期")

def ensure_auth():
    users = _load_users_from_env()
    if not st.session_state.get("authed"):
        do_login(users)
        return False
    # Optional: runtime check to ensure the account still valid (e.g., date window changed)
    user = st.session_state.get("username", "")
    if user not in users:
        st.warning("此帳號目前未被授權或已過期。請重新登入。")
        for k in ("authed","user","username"):
            st.session_state.pop(k, None)
        do_login(users)
        return False
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
    st.write(f"目前帳號：**{st.session_state.get('user','')}**")
    if st.button("登出", type="secondary", use_container_width=True):
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
