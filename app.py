# tiny bootstrapper to avoid indentation/encoding issues

import streamlit as st

try:
    from app_impl import run
except Exception as e:
    st.write("Import error in app_impl:", e)
else:
    run()
