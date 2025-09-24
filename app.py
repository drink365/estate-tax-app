import os
import json
import time
import secrets
import datetime as _dt
import threading
import streamlit as st

# ---- 你現有的模組匯入（保持不變）----
from modules.wrapped_estate import run_estate
from modules.wrapped_cvgift import run_cvgift

# =========================
# 基本設定
# =========================
st.set_page_config(
    page_title="《影響力》傳承策略平台 | 整合版",
    layout="wide",
    page_icon="assets/logo2.png",  # 只給 favicon 用 logo2.png
)

SESSION_STORE_PATH = os.environ.get("SESSION_STORE_PATH", ".sessions.json")
SESSION_TTL_SECONDS = int(os.environ.get("SESSION_TTL_SECONDS", "3600"))  # 60 分鐘

# =========================
# 美化與行為（CSS / JS）
# =========================
BRAND = "#e11d48"   # 品牌紅
INK   = "#1f2937"
MUTED = "#6b7280"

st.markdown(
    f"""
<style>
/* 隱藏 Streamlit 頂部工具列/標頭/選單/頁尾，避免擋標題 */
[data-testid="stToolbar"] {{ visibility: hidden; height: 0; position: fixed; }}
header {{ visibility: hidden; height: 0; }}
#MainMenu {{ visibility: hidden; }}
footer {{ visibility: hidden; }}

/* 背景與整體間距：輕柔，不加外框 */
.stApp {{
  background: linear-gradient(180deg, #fff, #fff9f9 30%, #fff 80%);
  padding-top: 0.75rem;
}}
.block-container {{ padding-top: .5rem; max-width: 1200px; }}

/* Tabs：簡潔風，不加卡片外框 */
.stTabs {{ padding-top: .5rem; }}
.stTabs [role="tablist"] {{ gap: 2rem; }}
.stTabs [role="tab"] {{
  font-size: 1.06rem; padding: .6rem .25rem; color: {MUTED};
  border-bottom: 2px solid transparent;
}}
.stTabs [role="tab"][aria-selected="true"] {{
  color: {BRAND}; border-color: {BRAND}; font-weight: 700;
}}

/* 右上登出：低調灰 */
.logout-btn>button {{
  border-radius: 4px !important;
  padding: .4rem .9rem !important;
  box-shadow: none !important;
  border: 1px solid #d1d5db !important;
  color: #374151 !important;
  background: #f9fafb !important;
}}
.logout-btn>button:hover {{
  background: #f3f4f6 !important;
  color: #111827 !important;
}}

/* 內容頁主標題：統一顏色與字級（避免黑色且大小不一） */
.app-title h1, .app-title h2 {{
  color: {BRAND} !important;
  font-size: 2.4rem !important;   /* 兩頁同一大小 */
  line-height: 1.2;
  margin: .25rem 0 0.75rem 0 !important;
  font-weight: 800;
}}

/* Plotly：柱內數字與註解一律白色，閱讀清楚 */
.js-plotly-plot .bartext {{ fill: #ffffff !important; }}
.js-plotly-plot g.annotation text {{ fill: #ffffff !important; }}
</style>
""",
    unsafe_allow_html=True,
)

# =========================
# 單點登入的小型會話管理（沿用前版）
# =========================
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
    now = int(time.time()); changed = False
    for u in list(store.keys()):
        if now - int(store[u].get("last_seen", 0)) > SESSION_TTL_SECONDS:
            store.pop(u, None); changed = True
    if changed: _save_store(store)

def _set_active_session(username_l: str, token: str, meta: dict):
    with _store_lock:
        s = _load_store()
        s[username_l] = {"token": token, "last_seen": int(time.time()), "meta": meta}
        _save_store(s)

def _get_active_session(username_l: str):
    with _store_lock:
        s = _load_store(); _cleanup_store(s); return s.get(username_l)

def _refresh_active_session(username_l: str, token: str):
    with _store_lock:
        s = _load_store(); sess = s.get(username_l)
        if not sess or sess.get("token") != token: return False
        sess["last_seen"] = int(time.time()); _save_store(s); return True

def _invalidate_session(username_l: str):
    with _store_lock:
        s = _load_store()
        if username_l in s: s.pop(username_l); _save_store(s)

# =========================
# 授權載入（ENV / secrets; TOML）
# =========================
def _load_users(env_key: str = "AUTHORIZED_USERS"):
    try:
        import tomllib as _toml  # py3.11+
    except Exception:
        import tomli as _toml     # py3.10

    raw = os.environ.get(env_key, "")
    data = None

    if raw.strip():
        try:
            data = _toml.loads(raw.strip())
        except Exception:
            st.error("授權設定（AUTHORIZED_USERS）格式有誤（ENV）。請確認為 TOML。")
            st.stop()

    if data is None:
        try:
            sec = st.secrets.get("AUTHORIZED_USERS", None)
        except Exception:
            sec = None
        if isinstance(sec, str) and sec.strip():
            try:
                data = _toml.loads(sec.strip())
            except Exception:
                st.error("授權設定（AUTHORIZED_USERS）格式有誤（secrets 字串）。")
                st.stop()
        elif isinstance(sec, dict):
            data = dict(sec)

    if data is None:
        # 舊版相容：若 st.secrets 只有 authorized_users
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

    for _, info in auth.items():
        try:
            username = str(info["username"]).strip()
            username_l = username.lower()
            users[username_l] = {
                "username": username,
                "name": str(info.get("name", username)),
                "role": str(info.get("role", "member")),
                "password": str(info["password"]),
                "start_date": _dt.date.fromisoformat(info.get("start_date", "1900-01-01")),
                "end_date": _dt.date.fromisoformat(info.get("end_date", "2999-12-31")),
            }
        except Exception:
            continue
    return users

def _check_login(username: str, password: str, users: dict):
    u = users.get((username or "").strip().lower())
    if not u: return False, None
    # 生效期間檢查
    today = _dt.date.today()
    if not (u["start_date"] <= today <= u["end_date"]): return False, None
    if password != u["password"]: return False, None
    return True, u

def _login_flow(users: dict):
    st.markdown("### 會員登入")
    with st.form("login_form"):
        u = st.text_input("帳號")
        p = st.text_input("密碼", type="password")
        takeover = st.checkbox("若此帳號已在其他裝置登入，允許我搶下使用權（登出他人）", value=True)
        if st.form_submit_button("登入"):
            ok, info = _check_login(u, p, users)
            if not ok:
                st.error("帳號或密碼錯誤，或帳號已過期")
                return
            username_l = info["username"].lower().strip()
            active = _get_active_session(username_l)
            if active and not takeover:
                st.warning("此帳號目前已在其他裝置登入。若要登入請勾選『允許我搶下使用權』。")
                return
            token = secrets.token_urlsafe(24)
            st.session_state.update({
                "authed": True,
                "user": info["name"],
                "username": info["username"],
                "username_l": username_l,
                "role": info.get("role", "member"),
                "start_date": info.get("start_date"),
                "end_date": info.get("end_date"),
                "session_token": token,
            })
            _set_active_session(username_l, token, {"ts": int(time.time())})
            st.rerun()

def ensure_auth() -> bool:
    users = _load_users()
    if not st.session_state.get("authed"):
        _login_flow(users)
        return False

    u_l = st.session_state.get("username_l", "")
    t   = st.session_state.get("session_token", "")
    if not u_l or not t or not _refresh_active_session(u_l, t):
        st.session_state.clear()
        _login_flow(users)
        return False
    return True

# =========================
# Header（logo 顯示用 data-uri 的版本已在先前完成；此處維持簡潔）
# =========================
st.markdown(
    f"""
    <div style="display:flex;align-items:center;gap:16px;margin-bottom:2px;">
      <img src="assets/logo.png" alt="logo" style="height:56px;display:block;" />
      <div>
        <h2 style="margin:0;color:{INK}">《影響力》傳承策略平台｜整合版</h2>
        <p style="margin:0;color:{MUTED};font-size:0.95rem;">專業 × 溫度 × 智能｜遺產稅試算 + 保單贈與規劃</p>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)
st.markdown(f"<hr style='border:none;height:1px;background:linear-gradient(90deg,{BRAND},transparent);margin:.75rem 0 1rem 0;'/>", unsafe_allow_html=True)

# =========================
# Top info bar：歡迎 😀｜有效期限｜登出
# =========================
if ensure_auth():
    exp_date = st.session_state.get("end_date")
    exp_str = exp_date.strftime("%Y-%m-%d") if isinstance(exp_date, _dt.date) else "N/A"
    name = st.session_state.get("user", "")

    c1, c2, _ = st.columns([8, 1.5, 10])
    with c1:
        st.markdown(f"<div style='color:{MUTED};font-size:.95rem;'>歡迎 😀，{name}｜有效期限至 {exp_str}</div>", unsafe_allow_html=True)
    with c2:
        st.markdown("<div class='logout-btn'>", unsafe_allow_html=True)
        if st.button("登出", use_container_width=True, type="secondary", key="logout_btn"):
            try:
                _invalidate_session((st.session_state.get("username_l","") or "").strip().lower())
            except Exception:
                pass
            st.session_state.clear()
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)
else:
    st.stop()

# =========================
# Tabs（移除括號後的簡潔標籤）
# =========================
tabs = st.tabs(["🏛️ 遺產稅試算", "🎁 保單贈與規劃"])

with tabs[0]:
    # 讓兩頁主標題一致：加一個容器 class，並在 CSS 中統一樣式
    st.markdown("<div class='app-title'><h2>遺產稅試算</h2></div>", unsafe_allow_html=True)
    try:
        run_estate()
    except Exception as e:
        st.error(f"載入遺產稅模組時發生錯誤：{e}")

with tabs[1]:
    st.markdown("<div class='app-title'><h2>保單規劃｜用同樣現金流，更聰明完成贈與</h2></div>", unsafe_allow_html=True)
    try:
        run_cvgift()
    except Exception as e:
        st.error(f"載入保單贈與模組時發生錯誤：{e}")

# =========================
# Footer
# =========================
st.markdown("---")
st.caption("《影響力》傳承策略平台｜永傳家族辦公室 ｜ 聯絡信箱：123@gracefo.com")
