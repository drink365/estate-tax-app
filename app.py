import os
import time
import uuid
import base64
from datetime import datetime

import streamlit as st
from PIL import Image
from pathlib import Path
from typing import Optional

BASE_DIR = Path(__file__).resolve().parent
ASSETS_DIR = BASE_DIR / "assets"

def _asset_path(name: str) -> str:
    return str(ASSETS_DIR / name)

@st.cache_data(show_spinner=False)
def _asset_b64(name: str) -> Optional[str]:
    try:
        with open(ASSETS_DIR / name, "rb") as f:
            return base64.b64encode(f.read()).decode()
    except Exception:
        return None

st.set_page_config(page_title="影響力傳承策略平台", layout="wide")

st.write("✅ 最小版 app.py 載入成功。")
st.write("Python/Streamlit 正常，表示先前的 IndentationError 來自檔案本體（BOM/隱形字元/舊檔）。")
