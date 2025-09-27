# hash_once.py —— 臨時用的 bcrypt 雜湊產生器（部署在 Streamlit Cloud）
import streamlit as st, bcrypt

st.set_page_config(page_title="bcrypt 產生器", layout="centered")
st.title("bcrypt 密碼雜湊產生器（臨時用）")

pwd = st.text_input("輸入你要設定的密碼", type="password")
if st.button("產生雜湊", type="primary") and pwd:
    hashed = bcrypt.hashpw(pwd.encode(), bcrypt.gensalt()).decode()
    st.code(hashed, language="text")
    st.success("已產生，請複製上面整串貼到主 App 的 Settings ▸ Secrets 的 pwd_hash。")
st.caption("用完即刪此 App，以免多餘入口。")
