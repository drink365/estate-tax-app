# 影響力傳承策略平台（雲端部署包-完整）

## 使用步驟（Streamlit Cloud）
1. 上傳這個專案（指向 `app.py`）。
2. 在 **Settings ▸ Secrets** 貼入：
   ```toml
   [users.grace]
   name       = "Grace"
   pwd_hash   = "$2b$12$...（用 hash_once.py 產生）"
   role       = "admin"
   ```
3. 如果沒有雜湊，在 Cloud 開一個小 App 指向 `hash_once.py` 產生，貼回主 App 的 Secrets，完畢後刪掉小 App。
4. 把你的 Logo 命名為 `assets/logo.png` 上傳，就會顯示 36px 高度。
