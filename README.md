# 《影響力》傳承策略平台｜整合版

- 單一登入整合：遺產稅試算 + 保單贈與（內嵌執行，無外連網址）
- 多使用者（TOML, 環境變數 `AUTHORIZED_USERS`）與**單一會話限制**（避免共用帳號）
- 60 分鐘無操作自動過期（可用 `SESSION_TTL_SECONDS` 調整）

## AUTHORIZED_USERS 範例（TOML）
```toml
[authorized_users.admin]
name = "管理者"
username = "admin"
password = "xxx"
role = "admin"
start_date = "2025-01-01"
end_date = "2026-12-31"

[authorized_users.grace]
name = "Grace"
username = "grace"
password = "xxx"
role = "vip"
start_date = "2025-01-01"
end_date = "2026-12-31"

[authorized_users.user1]
name = "使用者一"
username = "user1"
password = "xxx"
role = "member"
start_date = "2025-05-01"
end_date = "2025-07-31"
```
> 只有在 `start_date ≤ 今日 ≤ end_date` 的帳號會被當作有效。

## 其他環境變數
- `SESSION_TTL_SECONDS`：會話逾時秒數（預設 3600 = 60 分鐘）。
- `SESSION_STORE_PATH`：會話儲存檔案位置（預設 `.sessions.json`）。

## 執行
```bash
pip install -r requirements.txt
streamlit run app.py
```
