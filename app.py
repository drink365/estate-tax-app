import os
import json
import time
import secrets
import datetime as _dt
import threading
import base64
import streamlit as st

# ---- 你現有的功能模組（保持不變）----
from modules.wrapped_estate import run_estate
from modules.wrapped_cvgift import run_cvgift

# =========================
# 基本設定
# =========================
st.set_page_config(
    page_title="《影響力》傳承策略平台 | 整合版",
    layout="wide",
    page_icon="assets/logo2.png",  # favicon
)

SESSION_STORE_PATH = os.environ.get("SESSION_STORE_PATH", ".sessions.json")
SESSION_TTL_SECONDS = int(os.environ.get("SESSION_TTL_SECONDS", "3600"))  # 60 分鐘

# =========================
# 載入 assets/logo.png（以 data URI 方式避免路徑問題）
# =========================
def load_logo(path="assets/logo.png"):
    try:
        with open(path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("ascii")
        return f"data:image/png;base64,{b64}"
    except Exception:
        return None

logo_data_uri = load_logo()

# =========================
# CSS 美化（含響應式 Logo 與標題）
# =========================
INK   = "#111827"
MUTED = "#6b7280"
BRAND = "#e11d48"

st.markdown(
    f"""
<style>
/* 隱藏 Streamlit 頂列/選單/頁尾，避免壓住標題 */
[data-testid="stToolbar"] {{ visibility: hidden; height: 0; position: fixed; }}
header {{ visibility: hidden; height: 0; }}
#MainMenu {{ visibility: hidden; }}
footer {{ visibility: hidden; }}

/* 背景與容器 */
.stApp {{
  background: linear-gradient(180deg, #fff, #fff9f9 30%, #fff 80%);
  padding-top: .5rem;
}}
.block-container {{ padding-top: .25rem; max-width: 1200px; }}

/* Header：Logo + Title（響應式） */
.header-wrap {{
  display:flex; align-items:center; gap:14px; flex-wrap:wrap;
}}
.header-logo {{
  height: clamp(28px, 6vw, 44px);  /* 手機≈28–36px，桌機最多44px */
  width:auto; display:block;
  image-rendering:-webkit-optimize-contrast;
  image-rendering:optimizeQuality;
}}
.header-text h1 {{
  /* clamp(最小, 首選, 最大) -> 手機不會爆字，桌機仍醒目 */
  font-size: clamp(22px, 3.4vw, 38px);
  line-height: 1.15;
  margin: 0;
  color: {INK};
  font-weight: 800;
}}
.header-text p {{
  margin: 2px 0 0 0; color: {MUTED}; font-size: .95rem;
}}
@media (max-width: 640px) {{
  .header-wrap {{ flex-direction: column; align-items:flex-start; gap:8px; }}
}}

/* 細分隔線（品牌色漸層） */
.hr-thin {{
  border:none; height:1px;
  background: linear-gradient(90deg, {BRAND}, transparent);
  margin:.6rem 0 1rem 0;
}}

/* Tabs：簡潔底線樣式 */
.stTabs {{ padding-top: .25rem; }}
.stTabs [role="tablist"] {{ gap:2rem; }}
.stTabs [role="tab"] {{
  font-size:1.06rem; padding:.6rem .25rem; color:{MUTED};
  border-bottom:2px solid transparent;
}}
.stTabs [role="tab"][aria-selected="true"] {{
  color:{BRAND}; border-color:{BRAND}; font-weight:700;
}}

/* 右上登出：低調 */
.logout-btn>button {{
  border-radius:4px !important;
  padding:.35rem .75rem !important;
  box-shadow:none !important;
  border:1px solid #d1d5db !important;
  color:#374151 !important;
  background:#f9fafb !important;
  font-size:.85rem !important;
}}
.logout-btn>button:hover {{
  background:#f3f4f6 !important; color:#111827 !important;
}}

/* Plotly：柱內數字 & 註解改白色 */
.js-plotly-plot .bartext {{ fill:#ffffff !important; }}
.js-plotly-plot g.annotation text {{ fill:#ffffff !important; }}
</style>
""",
    unsafe_allow_html=True,
)

# =========================
# 單點登入（沿用你先前版本）
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
            st.error("授權設定（AUTHORIZED_USERS）格式有誤（ENV）。"); st.stop()
    if data is None:
        try:
            sec = st.secrets.get("AUTHORIZED_USERS", None)
        except Exception:
            sec = None
        if isinstance(sec, str) and sec.strip():
            try:
                data = _toml.loads(sec.strip())
            except Exception:
                st.error("授權設定（AUTHORIZED_USERS）格式有誤（secrets 字串）。"); st.stop()
        elif isinstance(sec, dict):
            data = dict(sec)
    if data is None:
        return {}

    users = {}
    auth = data.get("authorized_users", {}) if isinstance(data, dict) else {}
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
                st.error("帳號或密碼錯誤，或帳號已過期"); return
            username_l = info["username"].lower().strip()
            active = _get_active_session(username_l)
            if active and not takeover:
                st.warning("此帳號目前已在其他裝置登入。請勾選上方選項以登入。"); return
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
        _login_flow(users); return False
    u_l = st.session_state.get("username_l", ""); t = st.session_state.get("session_token", "")
    if not u_l or not t or not _refresh_active_session(u_l, t):
        st.session_state.clear(); _login_flow(users); return False
    return True

# =========================
# Header（logo + 主標題）
# =========================
if logo_data_uri:
    st.markdown(
        f"""
        <div class="header-wrap">
          <img class="header-logo" src="{logo_data_uri}" alt="logo" />
          <div class="header-text">
            <h1>《影響力》傳承策略平台｜整合版</h1>
            <p>專業 × 溫度 × 智能｜遺產稅試算 + 保單贈與規劃</p>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
else:
    st.markdown(
        f"""
        <div class="header-text">
          <h1>《影響力》傳承策略平台｜整合版</h1>
          <p style="color:{MUTED};">專業 × 溫度 × 智能｜遺產稅試算 + 保單贈與規劃</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.markdown('<hr class="hr-thin">', unsafe_allow_html=True)

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
            st.session_state.clear(); st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)
else:
    st.stop()

# =========================
# Tabs（不再在 app.py 內放分頁標題，避免與模組重複）
# =========================
tabs = st.tabs(["🏛️ 遺產稅試算", "🎁 保單贈與規劃"])

with tabs[0]:
    try:
        run_estate()   # 由 wrapped_estate 內部負責顯示「遺產稅試算」標題
    except Exception as e:
        st.error(f"載入遺產稅模組時發生錯誤：{e}")

with tabs[1]:
    try:
        run_cvgift()   # 由 wrapped_cvgift 內部負責顯示該頁標題
    except Exception as e:
        st.error(f"載入保單贈與模組時發生錯誤：{e}")

# =========================
# Footer
# =========================
st.markdown("---")
st.caption("《影響力》傳承策略平台｜永傳家族辦公室 ｜ 聯絡信箱：123@gracefo.com")
