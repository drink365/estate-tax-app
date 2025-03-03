import streamlit as st

st.sidebar.header("字型設定")
base_font_size = st.sidebar.slider("選擇一般文字字型大小 (em)", 1.0, 2.5, 1.5, 0.1)
header_font_size = st.sidebar.slider("選擇主標題字型大小 (em)", 2.0, 4.0, 3.0, 0.1)

st.write("一般文字字型大小：", base_font_size, "em")
st.write("主標題字型大小：", header_font_size, "em")
