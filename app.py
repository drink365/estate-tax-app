# app.py — 影響力傳承策略平台（主入口）
import os
import time
import uuid
import base64
from io import BytesIO
from PIL import Image
from datetime import datetime
import streamlit as st

# ---- Robust asset path helpers ----
BASE_DIR = Path(__file__).resolve().parent
ASSETS_DIR = BASE_DIR / "assets"

def _asset_path(name: str) -> str:
    """Return a string path to asset that works in Streamlit (posix)."""
    p = ASSETS_DIR / name
    return str(p)

@st.cache_data(show_spinner=False)
def _asset_b64(name: str) -> Optional[str]:
    """Read an asset file and return base64 string, or None if missing."""
    try:
        with open(ASSETS_DIR / name, "rb") as f:
            return base64.b64encode(f.read()).decode()
    except Exception:
        return None


from typing import Optional
from pathlib import Path

# 兼容 Python 3.11+（內建 tomllib）與較舊版本（安裝 toml）
try:
    import tomllib as toml  # Python 3.11+
except Exception:  # pragma: no cover
    import toml  # pip install toml

# === 子模組 ===
from modules.wrapped_estate import run_estate
from modules.wrapped_cvgift import run_cvgift

# ======================================================
# 0) Favicon 與 Page Config（保證顯示）
# ======================================================
def _load_image(path):
    try:
        return Image.open(path)
    except Exception:
        return None

_fav_img = _load_image(_asset_path("logo2.png")) or _load_image(_asset_path("logo.png"))


# Page config with icon fallback to emoji if asset missing
st.set_page_config(
    page_title="影響力傳承策略平台",
    page_icon=Image.open(_asset_path("logo2.png")) if os.path.exists(_asset_path("logo2.png")) else (Image.open(_asset_path("logo.png")) if os.path.exists(_asset_path("logo.png")) else "🧭"),
    layout="wide"
)


def _inject_favicon(path: str):
    """有些環境 page_icon 不一定立即生效，額外再注入一次。"""
    try:
        with open(path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode()
        st.markdown(
            f"<link rel='icon' type='image/png' href='data:image/png;base64,{b64}'>",
            unsafe_allow_html=True
        )
    except Exception:
        pass

if os.path.exists(_asset_path("logo2.png")):
    _inject_favicon(_asset_path("logo2.png"))
elif os.path.exists(_asset_path("logo.png")):
    _inject_favicon(_asset_path("logo.png"))

# ======================================================
# 1) 單一登入（防共用）與逾時 60 分鐘
# ======================================================
@st.cache_resource
def _session_registry():
    # username -> {"session_id": str, "last_seen": float}
    return {}

REG = _session_registry()
SESSION_TIMEOUT_SECS = 60 * 60

def _now(): 
    return time.time()

def _cleanup():
    now = _now()
    for u in list(REG.keys()):
        if now - REG[u].get("last_seen", 0) > SESSION_TIMEOUT_SECS:
            REG.pop(u, None)

def _touch(u, sid):
    REG[u] = {"session_id": sid, "last_seen": _now()}

def _valid(u, sid):
    r = REG.get(u)
    return bool(
        r and r.get("session_id") == sid and
        _now() - r.get("last_seen", 0) <= SESSION_TIMEOUT_SECS
    )

def _logout(u):
    REG.pop(u, None)

_cleanup()

# ======================================================
# 2) 授權名單：支援 secrets.toml / 環境變數 / 檔內變數
# ======================================================
def _parse_users_from_toml_str(toml_str: str) -> dict:
    if not toml_str or not toml_str.strip():
        return {}
    data = toml.loads(toml_str)
    return data.get("authorized_users", {})

def _read_authorized_users_raw() -> dict:
    """回傳等價於 secrets['authorized_users'] 的 dict。"""
    # 1) 優先：.streamlit/secrets.toml 內 [authorized_users]
    au = st.secrets.get("authorized_users", None)
    if isinstance(au, dict) and au:
        return au

    # 2) 其次：環境變數 AUTHORIZED_USERS（內容為 TOML 字串）
    env_str = os.environ.get("AUTHORIZED_USERS", "")
    if env_str.strip():
        return _parse_users_from_toml_str(env_str)

    # 3) 最後：程式內變數 AUTHORIZED_USERS（內容為 TOML 字串）
    global AUTHORIZED_USERS  # 若未定義會被 except 吃掉
    try:
        if isinstance(AUTHORIZED_USERS, str) and AUTHORIZED_USERS.strip():
            return _parse_users_from_toml_str(AUTHORIZED_USERS)
    except Exception:
        pass

    return {}

def _load_users_from_sources():
    """
    轉成 {username(區分大小寫): {...}}。
    - 可用 section 名稱或內層 username 欄位登入。
    - AUTH_<USERNAME>_PASSWORD 可覆蓋密碼（例：AUTH_GRACE_PASSWORD）
    """
    users = {}
    raw = _read_authorized_users_raw()
    for section_name, d in raw.items():
        if not isinstance(d, dict):
            continue
        username = d.get("username", section_name)  # 相容兩種寫法
        pwd_env = os.environ.get(f"AUTH_{username.upper()}_PASSWORD")
        users[username] = {
            "name": d.get("name", username),
            "username": username,
            "password": pwd_env if pwd_env is not None else d.get("password", ""),
            "start_date": d.get("start_date", "1970-01-01"),
            "end_date": d.get("end_date", "2099-12-31"),
            "role": d.get("role", "member"),
        }
    return users

USERS = _load_users_from_sources()

def check_credentials(input_username: str, input_password: str):
    """區分大小寫；支援環境變數覆蓋密碼；檢查有效期間。"""
    if not USERS:
        return False, None, "尚未設定授權名單（authorized_users）。請在 secrets 或環境變數設定。"
    info = USERS.get(input_username)
    if not info:
        return False, None, "查無此使用者"
    if input_password != info["password"]:
        return False, None, "密碼錯誤"
    try:
        start_date = datetime.strptime(info["start_date"], "%Y-%m-%d").date()
        end_date = datetime.strptime(info["end_date"], "%Y-%m-%d").date()
        today = datetime.today().date()
        if not (start_date <= today <= end_date):
            return False, None, "您的使用權限尚未啟用或已過期"
    except Exception:
        return False, None, "帳號日期設定格式有誤"
    return True, info, ""

# ======================================================
# 3) 頂部抬頭（Logo RWD + 2x，與標題對齊）— 放大版
# ======================================================
st.markdown("""
<style>
.header { display:flex; align-items:center; justify-content:space-between; gap:12px; }
.brand { display:flex; align-items:center; gap:14px; }
.brand-title { margin:0; font-size:26px; color:#000; line-height:1; }
.brand-logo { height:96px; image-rendering:auto; }   /* ← 桌機 80px */
@media (max-width:1200px){ .brand-logo{ height:64px; } .brand-title{ font-size:24px; } }
@media (max-width:768px){  .brand-logo{ height:52px; } .brand-title{ font-size:22px; } }
.header-right { display:flex; align-items:center; gap:8px; }
</style>
""", unsafe_allow_html=True)

# 支援 Retina：若有 logo@2x.png 就用 srcset
logo_1x = _asset_path("logo.png")
logo_2x = "assets/logo@2x.png" if os.path.exists("assets/logo@2x.png") else None
logo_img_tag = (
    f"<img src='{logo_1x}' class='brand-logo' alt='logo'>" if not logo_2x else
    f"<img src='{logo_1x}' srcset='{logo_1x} 1x, {logo_2x} 2x' class='brand-logo' alt='logo'>"
)

st.markdown("<div class='header'>", unsafe_allow_html=True)
st.markdown(
    f"<div class='brand'>{logo_img_tag}<h1 class='brand-title'>影響力傳承策略平台</h1></div>",
    unsafe_allow_html=True
)
right_col = st.container()
st.markdown("</div>", unsafe_allow_html=True)

# ======================================================
# 4) 右上角登入/登出（單一登入＋60分鐘逾時）
# ======================================================
if "auth" not in st.session_state:
    st.session_state.auth = {
        "authenticated": False, "username": "", "name": "", "role": "",
        "end_date": "", "session_id": ""
    }

# 檢查現有 session 是否仍有效
if st.session_state.auth["authenticated"]:
    u = st.session_state.auth["username"]
    sid = st.session_state.auth["session_id"]
    if not _valid(u, sid):
        st.session_state.auth = {
            "authenticated": False, "username": "", "name": "", "role": "", "end_date": "", "session_id": ""
        }
    else:
        _touch(u, sid)

with right_col:
    if not st.session_state.auth["authenticated"]:
        with st.form("top_login_inline", clear_on_submit=False):
            c1, c2, c3 = st.columns([2, 2, 1])
            input_username = c1.text_input("帳號", placeholder="帳號", label_visibility="collapsed")
            input_password = c2.text_input("密碼", placeholder="密碼", type="password", label_visibility="collapsed")
            submitted = c3.form_submit_button("登入")
            if submitted:
                ok, info, msg = check_credentials(input_username, input_password)
                if ok:
                    sid = uuid.uuid4().hex
                    st.session_state.auth = {
                        "authenticated": True,
                        "username": input_username,
                        "name": info["name"],
                        "role": info["role"],
                        "end_date": info["end_date"],
                        "session_id": sid
                    }
                    # 單一登入：新登入直接覆蓋舊裝置
                    _touch(input_username, sid)
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
                st.session_state.auth = {
                    "authenticated": False, "username": "", "name": "", "role": "",
                    "end_date": "", "session_id": ""
                }

st.markdown("<hr style='margin-top:6px;margin-bottom:14px;'>", unsafe_allow_html=True)

# ======================================================
# 5) 置頂頁籤（平台子模組）
# ======================================================
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
