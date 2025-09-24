# 《影響力》傳承策略平台｜整合版

# Integrated placeholder (will be replaced next step)

## 多使用者登入（環境變數）

請在部署環境設定環境變數 `AUTHORIZED_USERS`（TOML 格式）：

```toml
[authorized_users.admin]
name = "管理者"
username = "admin"
password = "xxx"
start_date = "2025-01-01"
end_date = "2026-12-31"

[authorized_users.grace]
name = "Grace"
username = "grace"
password = "xxx"
start_date = "2025-01-01"
end_date = "2026-12-31"

[authorized_users.user1]
name = "使用者一"
username = "user1"
password = "xxx"
start_date = "2025-05-01"
end_date = "2025-07-31"
```

> 只有在 `start_date ≤ 今日 ≤ end_date` 的帳號，才會被視為有效。
