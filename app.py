import streamlit as st
import time
import uuid
from datetime import datetime, timedelta

from modules.wrapped_estate import run_estate
from modules.wrapped_cvgift import run_cvgift

# ===============================
# 0) 平台一次性設定（標題、favicon）
# ===============================
st.set_page_config(
    page_title="影響力傳承策略平台",
    page_icon="assets/logo2.png",
    layout="wide"
)

# ===============================
# 1) 單一登入（防多人共用同帳號）與 60 分鐘逾時
# ===============================
@st.cache_resource
def _session_registry():
    # username -> {"session_id": str, "last_seen": float (epoch)}
    return {}

REG = _session_registry()
SESSION_TIMEOUT_SECS = 60 * 60  # 60 分鐘

def _now_epoch():
    return time.time()

def _cleanup_expired_sessions():
    # 清理超時的舊 session，以避免卡死
    now = _now_epoch()
    expired = []
    for u, data in REG.items():
        if now - data.get("last_seen", 0) > SESSION_TIMEOUT_SECS:
            expired.append(u)
    for u in expired:
        REG.pop(u, None)

def _touch_session(username: str, session_id: str):
    REG[username] = {"session_id": session_id, "last_seen": _now_epoch()}

def _is_active_session(username: str, session_id: str) -> bool:
    rec = REG.get(username)
    return bool(rec and rec.get("session_id") == session_id and (_now_epoch() - rec.get("last_seen", 0) <= SESSION_TIMEOUT_SECS))

def _logout_session(username: str):
    if username in REG:
        REG.pop(username, None)

_cleanup_expired_sessions()

# ===============================
# 2) 讀取授權名單 (st.secrets["authorized_users"])
#    注意：帳號區分大小寫
# ===============================
def check_credentials(input_username: str, input_password: str):
    au = st.secrets.get("authorized_users", {})
    # 區分大小寫：直接用鍵值查
    user_info = au.get(input_username)
    if not user_info:
        return False, None, "查無此使用者"
    if input_password != user_info.get("password"):
        return False, None, "密碼錯誤"
    # 檢查有效日期（含當日）
    try:
        start_date = datetime.strptime(user_info["start_date"], "%Y-%m-%d").date()
        end_date = datetime.strptime(user_info["end_date"], "%Y-%m-%d").date()
        today = datetime.today().date()
        if not (start_date <= today <= end_date):
            return False, None, "您的使用權限尚未啟用或已過期"
    except Exception:
        # 格式錯誤時，保守阻擋
        return False, None, "帳號日期設定格式有誤"
    return True, user_info, ""

# ===============================
# 3) 頂部抬頭（左：logo+平台名；右：登入區/歡迎+登出）
# ===============================
logo_col, title_col, user_col = st.columns([1, 8, 6], gap="small")

with logo_col:
    try:
        st.image("assets/logo.png", width=40)
    except Exception:
        st.write("")

with title_col:
    st.markdown(
        "<div style='display:flex;align-items:center;gap:12px;'>"
        "<h1 style='margin:0;font-size:26px;color:#000;'>影響力傳承策略平台</h1>"
        "</div>",
        unsafe_allow_html=True
    )

# 初始化 session 狀態
if "auth" not in st.session_state:
    st.session_state.auth = {
        "authenticated": False,
        "username": "",
        "name": "",
        "role": "",
        "end_date": "",
        "session_id": ""
    }

# 驗證現有 session 是否仍有效（單一登入 + 逾時控制）
if st.session_state.auth["authenticated"]:
    u = st.session_state.auth["username"]
    sid = st.session_state.auth["session_id"]
    if not _is_active_session(u, sid):
        # 逾時或被別處擠下線
        st.session_state.auth = {"authenticated": False, "username": "", "name": "", "role": "", "end_date": "", "session_id": ""}
    else:
        # 更新 last_seen
        _touch_session(u, sid)

with user_col:
    container = st.container()
    if not st.session_state.auth["authenticated"]:
        # 輕量登入表單（同排，低存在感）
        with container.form("top_login_inline", clear_on_submit=False):
            c1, c2, c3, c4 = st.columns([3, 3, 2, 2])
            with c1:
                input_username = st.text_input("帳號", key="login_user", label_visibility="collapsed", placeholder="帳號")
            with c2:
                input_password = st.text_input("密碼", key="login_pass", label_visibility="collapsed", placeholder="密碼", type="password")
            with c3:
                submitted = st.form_submit_button("登入")
            with c4:
                st.write("")  # 對齊

            if submitted:
                ok, info, msg = check_credentials(input_username, input_password)
                if ok:
                    # 單一登入：若已有其他裝置在用，直接踢下線（覆蓋 session_id）
                    sid = uuid.uuid4().hex
                    st.session_state.auth = {
                        "authenticated": True,
                        "username": input_username,
                        "name": info.get("name", input_username),
                        "role": info.get("role", ""),
                        "end_date": info.get("end_date", ""),
                        "session_id": sid
                    }
                    _touch_session(input_username, sid)
                    st.success(f"登入成功！歡迎 {info.get('name', input_username)} 😀")
                else:
                    st.error(msg)
    else:
        # 右上角一行顯示：歡迎 + 到期 + 登出
        name = st.session_state.auth["name"] or st.session_state.auth["username"]
        end_date = st.session_state.auth["end_date"]
        colA, colB = st.columns([8, 2])
        with colA:
            st.markdown(
                f"<div style='text-align:right;font-size:14px;color:#333;'>"
                f"歡迎 {name} 😀｜有效期限至 {end_date}"
                f"</div>", unsafe_allow_html=True
            )
        with colB:
            if st.button("登出", use_container_width=True):
                _logout_session(st.session_state.auth["username"])
                st.session_state.auth = {"authenticated": False, "username": "", "name": "", "role": "", "end_date": "", "session_id": ""}

st.markdown("<hr style='margin-top:6px;margin-bottom:14px;'>", unsafe_allow_html=True)

# ===============================
# 4) 置頂頁籤（不使用側邊欄）
# ===============================
tab1, tab2 = st.tabs(["AI秒算遺產稅", "保單贈與規劃"])

# 若未登入，兩頁內容都以「請先登入」提示
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
