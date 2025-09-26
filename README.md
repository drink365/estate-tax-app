
# 影響力傳承策略平台（單一登入版）

- 單一登入：後登入會踢掉前者（SQLite 共享 sessions）
- 密碼：只存 bcrypt 雜湊（放在 `.streamlit/secrets.toml` 的 `[users]` 節）

## Secrets 範例
```toml
[users.grace]
name       = "Grace"
pwd_hash   = "$2b$12$..."
start_date = "2024-01-01"
end_date   = "2030-12-31"
```
