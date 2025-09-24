import os
import json
import time
import secrets
import datetime as _dt
import threading
import streamlit as st

# tomllib / tomli
try:
    import tomllib as _toml
except Exception:
    import tomli as _toml  # type: ignore

from modules.wrapped_estate import run_estate
from modules.wrapped_cvgift import run_cvgift

# ------------------------------------------------------------
# Page config
# ------------------------------------------------------------
st.set_page_config(
    page_title="《影響力》傳承策略平台 | 整合版",
    layout="wide",
    page_icon="assets/logo2.png",
)

SESSION_STORE_PATH = os.environ.get("SESSION_STORE_PATH", ".sessions.json")
SESSION_TTL_SECONDS = int(os.environ.get("SESSION_TTL_SECONDS", "3600"))

# ------------------------------------------------------------
# CSS
# ------------------------------------------------------------
st.markdown(
    """
<style>
:root{
  --brand:#e11d48;
  --ink:#1f2937;
  --muted:#6b7280;
}

/* 隱藏 Streamlit 頂欄與頁尾 */
[data-testid="stToolbar"] {visibility:hidden;height:0;position:fixed;}
header {visibility:hidden;height:0;}
#MainMenu {visibility:hidden;}
footer {visibility:hidden;}

/* 背景 */
.stApp {
  background:linear-gradient(180deg, #fff, #fff9f9 30%, #fff 80%);
  padding-top:.75rem;
}
.block-container{padding-top:.5rem;max-width:1200px;}

/* Tabs 樣式（移除卡片化外框） */
.stTabs {padding-top:.5rem;}
.stTabs [role="tablist"]{gap:2rem;}
.stTabs [role="tab"]{
  font-size:1.06rem; padding:.6rem .25rem; color:var(--muted);
  border-bottom:2px solid transparent;
}
.stTabs [role="tab"][aria-selected="true"]{
  color:var(--brand); border-color:var(--brand);
  font-weight:700;
}

/* 登出按鈕：低調 */
.logout-btn>button{
  border-radius:4px !important;
  padding:.4rem .9rem !important;
  box-shadow:none !important;
  border:1px solid #d1d5db !important;
  color:#374151 !important;
  background:#f9fafb !important;
}
.logout-btn>button:hover{
  background:#f3f4f6 !important;
  color:#111827 !important;
}

/* Plotly：標籤白色 */
.js-plotly-plot .bartext{fill:#ffffff !important;}
.js-plotly-plot g.annotation text{fill:#ffffff !important;}
</style>
""",
    unsafe_allow_html=True,
)

# ------------------------------------------------------------
# Helpers
# ------------------------------------------------------------
_store_lock = threading.Lock()
def _load_store():
    if not os.path.exists(SESSION_STORE_PATH):
        return {}
    try:
        with open(SESSION_STORE_PATH,"r",encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}
def _save_store(store:dict):
    tmp=SESSION_STORE_PATH+".tmp"
    with open(tmp,"w",encoding="utf-8") as f:
        json.dump(store,f,ensure_ascii=False,indent=2)
    os.replace(tmp,SESSION_STORE_PATH)
def _cleanup_store(store:dict):
    now=int(time.time());changed=False
    for u in list(store.keys()):
        if now-int(store[u].get("last_seen",0))>SESSION_TTL_SECONDS:
            store.pop(u,None);changed=True
    if changed:_save_store(store)
def _set_active_session(u,t,meta):
    with _store_lock:
        s=_load_store();s[u]={"token":t,"last_seen":int(time.time()),"meta":meta};_save_store(s)
def _get_active_session(u):
    with _store_lock:
        s=_load_store();_cleanup_store(s);return s.get(u)
def _refresh_active_session(u,t):
    with _store_lock:
        s=_load_store();ss=s.get(u)
        if not ss or ss.get("token")!=t:return False
        ss["last_seen"]=int(time.time());_save_store(s);return True
def _invalidate_session(u):
    with _store_lock:
        s=_load_store()
        if u in s:s.pop(u);_save_store(s)

def _load_users(env_key="AUTHORIZED_USERS"):
    raw=os.environ.get(env_key,"");data=None
    if raw.strip():
        try:data=_toml.loads(raw.strip())
        except:st.error("授權設定錯誤");st.stop()
    if data is None:
        try:sec=st.secrets.get("AUTHORIZED_USERS",None)
        except:sec=None
        if isinstance(sec,str):
            try:data=_toml.loads(sec.strip())
            except:st.error("授權設定錯誤");st.stop()
        elif isinstance(sec,dict):data=dict(sec)
    if data is None:return {}
    users={};today=_dt.date.today();auth=data.get("authorized_users",{})
    for _,info in auth.items():
        try:
            u=info["username"].strip();u_l=u.lower()
            users[u_l]={"username":u,"name":info.get("name",u),"role":info.get("role","member"),
                        "password":info["password"],
                        "start_date":_dt.date.fromisoformat(info.get("start_date","1900-01-01")),
                        "end_date":_dt.date.fromisoformat(info.get("end_date","2999-12-31"))}
        except:continue
    return users

def _check_login(username,password,users):
    u=users.get(username.lower().strip())
    if not u or password!=u["password"]:return False,None
    return True,u

def do_login(users):
    st.markdown("### 會員登入")
    with st.form("login_form"):
        u=st.text_input("帳號")
        p=st.text_input("密碼",type="password")
        takeover=st.checkbox("允許搶下使用權",value=True)
        if st.form_submit_button("登入"):
            ok,info=_check_login(u,p,users)
            if not ok:st.error("帳號/密碼錯誤或已過期");return
            token=secrets.token_urlsafe(24)
            st.session_state.update({"authed":True,"user":info["name"],"username":info["username"],
                                     "username_l":info["username"].lower(),"role":info["role"],
                                     "end_date":info["end_date"],"session_token":token})
            _set_active_session(info["username"].lower(),token,{"ts":int(time.time())});st.rerun()

def ensure_auth():
    users=_load_users()
    if not st.session_state.get("authed"):
        do_login(users);return False
    u_l=st.session_state.get("username_l","");t=st.session_state.get("session_token","")
    if not _refresh_active_session(u_l,t):
        st.session_state.clear();do_login(users);return False
    return True

# ------------------------------------------------------------
# Header
# ------------------------------------------------------------
st.markdown("<h2>《影響力》傳承策略平台｜整合版</h2>",unsafe_allow_html=True)
st.markdown("---")

if ensure_auth():
    exp=st.session_state.get("end_date");exp_str=exp.strftime("%Y-%m-%d") if isinstance(exp,_dt.date) else "N/A"
    c1,c2=st.columns([8,1])
    with c1:st.markdown(f"歡迎 😀，{st.session_state.get('user')}｜有效期限至 {exp_str}")
    with c2:
        st.markdown("<div class='logout-btn'>",unsafe_allow_html=True)
        if st.button("登出"): _invalidate_session(st.session_state.get("username_l",""));st.session_state.clear();st.rerun()
        st.markdown("</div>",unsafe_allow_html=True)
else: st.stop()

# ------------------------------------------------------------
# Tabs
# ------------------------------------------------------------
tabs=st.tabs(["🏛️ 遺產稅試算","🎁 保單贈與規劃"])
with tabs[0]: run_estate()
with tabs[1]: run_cvgift()

st.markdown("---")
st.caption("《影響力》傳承策略平台｜永傳家族辦公室 ｜ 聯絡信箱：123@gracefo.com")
