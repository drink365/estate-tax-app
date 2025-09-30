# app.py — 影響力傳承策略平台（logo可見性＋避開工具列＋登入後顯示姓名與到期日）
import os, uuid, hmac
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, Tuple
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

# ------------------------- Logo / Favicon -------------------------
MAIN_LOGO_CANDIDATES = ["logo.png", "Logo.png", "logo.PNG", "logo.jpg", "logo.jpeg", "logo.webp"]  # 主Logo容錯
FAVICON_CANDIDATES   = ["logo2.png", "logo.png", "logo.jpg", "logo.jpeg", "logo.webp"]             # favicon優先logo2.png

def _find_first(cands) -> Optional[Path]:
    for name in cands:
        p = ASSETS_DIR / name
        if p.exists():
            return p
    return None

def _open_image_safe(p: Path) -> Optional[Image.Image]:
    try:
        return Image.open(p)
    except Exception:
        return None

# 設定頁面 favicon
favicon_path = _find_first(FAVICON_CANDIDATES)
page_icon = _open_image_safe(favicon_path) if favicon_path else "🧭"
st.set_page_config(page_title="影響力傳承策略平台", page_icon=page_icon, layout="wide")

# ------------------------- Styles -------------------------
st.markdown("""
<style>
.block-container { padding-top: 1rem; }

/* 標題與右側資訊的基本字型 */
.brand-title { margin:0; font-size:26px; color:#2b2f36; line-height:1.1; }
.info-pill { font-size:14px; color:#334155; }

/* 右上資訊區：預留空間，避免被 Streamlit 工具列(右上角)遮住 */
.avoid-toolbar { padding-right: 160px; }   /* 若仍被蓋到可把 160 調大些 */

/* 讓右上資訊 pill 看起來更像標籤 */
.user-pill {
  display:inline-block;
  padding:6px 10px;
  border:1px solid #E6E8EF;
  border-radius:10px;
  background:#fff;
}

/* 響應式微調 */
@media (max-width: 1200px){
  .brand-title { font-size:24px; }
  .avoid-toolbar { padding-right: 140px; }
}
@media (max-width: 768px){
  .brand-title { font-size:22px; }
  .avoid-toolbar { padding-right: 120px; }
}
</style>
""", unsafe_allow_html=True)

# ------------------------- Header（主Logo用 st.image，最小寬度120） -------------------------
logo_path = _find_first(MAIN_LOGO_CANDIDATES)
col_logo, col_title, col_right = st.columns([1, 8, 3], vertical_alignment="center")

with col_logo:
    if logo_path:
        img = _open_image_safe(logo_path)
        if img is not None:
            w, h = img.size
            target_h = 36
            # 依比例計算寬度，同時設定最小寬度 120，避免看起來太小
            target_w = max(120, int(w * (target_h / max(1, h))))
            st.image(img, width=target_w)

with col_title:
    st.markdown("<h1 class='brand-title'>影響力傳承策略平台</h1>", unsafe_allow_html=True)

with col_right:
    # 放一個容器，登入後會在這裡顯示歡迎文字（並預留空間避開工具列）
    right_col = st.container()

# ------------------------- 認證與使用者 -------------------------
def _load_users_from_secrets() -> Dict[str, Any]:
    try:
        return dict(st.secrets.get("users", {}))
    except Exception:
        return {}

def _find_user(username_input: str, users: Dict[str, Any]) -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
    """支援：帳號鍵或顯示名稱（皆不分大小寫）"""
    u = (username_input or "").strip()
    if not u: return None, None
    lower_map = {k.lower(): k for k in users.keys()}
    key = lower_map.get(u.lower())
    if key:
        return key, users[key]
    for k, info in users.items():
        name = str(info.get("name", "")).strip()
        if name and name.lower() == u.lower():
            return k, info
    return None, None

def _check_password(pwd_plain: str, pwd_hash: str) -> bool:
    try:
        if pwd_hash is None: return False
        return bcrypt.checkpw((pwd_plain or "").encode(), str(pwd_hash).strip().encode())
    except Exception:
        return False

def _check_credentials(username: str, password: str):
    users = _load_users_from_secrets()
    if not users:
        return False, "", "", "尚未設定 users（請至 Settings ▸ Secrets 貼上使用者設定）"
    key, info = _find_user(username, users)
    if not info:
        return False, "", "", "查無此使用者（請確認輸入的「帳號」或「姓名」與 Secrets 一致）"
    if not _check_password(password, info.get("pwd_hash", "")):
        return False, "", "", "帳密錯誤"

    s, e = info.get("start_date"), info.get("end_date")
    if s and e:
        try:
            start_date = datetime.fromisoformat(s)
            end_date = datetime.fromisoformat(e)
            if not (start_date <= datetime.today() <= end_date):
                return False, "", "", "權限尚未啟用或已過期"
        except Exception:
            return False, "", "", "日期格式錯誤（YYYY-MM-DD）"

    display = info.get("name", key)
    end_date_text = e if e else "未設定"
    return True, key, display, end_date_text

# Session 狀態
if "auth" not in st.session_state:
    st.session_state.auth = {
        "authenticated": False,
        "username": "",
        "name": "",
        "session_id": "",
        "end_date": ""
    }

# ------------------------- 登入區（登入後隱藏表單） -------------------------
with right_col:
    if not st.session_state.auth["authenticated"]:
        with st.form("top_login_inline", clear_on_submit=False):
            c1, c2, c3 = st.columns([2, 2, 1])
            u = c1.text_input("帳號或姓名", placeholder="帳號或姓名", label_visibility="collapsed")
            p = c2.text_input("密碼", placeholder="密碼", type="password", label_visibility="collapsed")
            ok_btn = c3.form_submit_button("登入")
            if ok_btn:
                ok, key, display, end_date_text = _check_credentials(u, p)
                if ok:
                    new_sid = uuid.uuid4().hex
                    REGISTRY.upsert(key, new_sid)         # 單一登入（後登入踢前者）
                    REGISTRY.cleanup_expired()
                    st.session_state.auth = {
                        "authenticated": True,
                        "username": key,
                        "name": display,
                        "session_id": new_sid,
                        "end_date": end_date_text
                    }
                    st.success(f"登入成功！歡迎 {display} 😀（到期日：{end_date_text}）")
                    st.rerun()  # 讓表單消失
                else:
                    st.error(end_date_text or "登入失敗")
    else:
        # 右上角顯示歡迎資訊，並預留空間避開工具列
        st.markdown(
            f"<div class='info-pill avoid-toolbar' style='text-align:right;'>"
            f"<span class='user-pill'>歡迎 {st.session_state.auth['name']} 😀（到期日：{st.session_state.auth.get('end_date','未設定')}）</span>"
            f"</div>",
            unsafe_allow_html=True
        )
        if st.button("登出", use_container_width=True):
            REGISTRY.delete_if_match(st.session_state.auth["username"], st.session_state.auth["session_id"])
            st.session_state.auth = {"authenticated": False, "username": "", "name": "", "session_id": "", "end_date": ""}
            st.rerun()

# ------------------------- 單一登入守護 -------------------------
def _guard_session():
    auth = st.session_state.auth
    if not auth["authenticated"]:
        return
    row = REGISTRY.get(auth["username"])
    if not row:
        st.warning("你的登入已失效，請重新登入。")
        st.session_state.auth = {"authenticated": False, "username": "", "name": "", "session_id": "", "end_date": ""}
        st.stop()
    reg_sid, _ = row
    if not hmac.compare_digest(reg_sid, auth["session_id"]):
        st.warning("你已在其他裝置登入，已將此處登出。")
        st.session_state.auth = {"authenticated": False, "username": "", "name": "", "session_id": "", "end_date": ""}
        st.stop()
    REGISTRY.touch(auth["username"])
    REGISTRY.cleanup_expired()

_guard_session()

st.markdown("<hr style='margin:6px 0 14px;'>", unsafe_allow_html=True)

# ------------------------- 兩個模組 -------------------------
tab1, tab2 = st.tabs(["AI秒算遺產稅", "保單贈與規劃"])
if not st.session_state.auth["authenticated"]:
    with tab1: st.info("此功能需登入後使用。請在右上角先登入。")
    with tab2: st.info("此功能需登入後使用。請在右上角先登入。")
else:
    with tab1: run_estate()
    with tab2: run_cvgift()
