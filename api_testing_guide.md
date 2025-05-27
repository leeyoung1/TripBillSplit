# API 测试指南 (cURL)

本文档提供了使用 `curl` 命令测试用户相关 API 接口的步骤。请注意，某些接口依赖于先前接口的成功调用（例如，您需要先注册并登录才能访问受保护的端点）。

**基础 URL:** 假设您的 FastAPI 应用运行在 `http://127.0.0.1:8000`。所有 API 路径都以 `/api/v1` 为前缀，并基于此基础 URL。例如，注册接口的完整路径是 `http://127.0.0.1:8000/api/v1/users/register`。

**重要提示:**
*   在实际测试中，请将占位符（如 `<YOUR_ACCESS_TOKEN>`，`<USER_EMAIL>`，`<VERIFICATION_TOKEN>` 等）替换为实际值。
*   某些操作（如发送邮件）是后台任务，`curl` 的直接响应可能不会立即反映邮件发送状态。请检查您的邮件客户端或应用日志。
*   为了方便，您可以将获取到的 `access_token` 存储在一个环境变量中，例如 `ACCESS_TOKEN`，然后在后续命令中使用 `$ACCESS_TOKEN`。

## 1. 用户注册

创建一个新用户。成功后会发送一封邮箱验证邮件。

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/users/register" \
-H "Content-Type: application/json" \
-d '{
  "email": "yeaonaiwohe1211@163.com",
  "password": "SecurePassword123!",
  "nickname": "Test User",
  "phone": "13800138000"
}'
```

**预期响应 (示例):**
```json
{
  "user_id": "some-uuid-string",
  "nickname": "Test User",
  "email": "yeaonaiwohe1211@163.com",
  "phone": "13800138000",
  "is_verified": false,
  "created_at": "YYYY-MM-DDTHH:MM:SS.ffffff",
  "updated_at": "YYYY-MM-DDTHH:MM:SS.ffffff"
}
```
记下返回的 `email` (例如 `yeaonaiwohe1211@163.com`) 和 `user_id` (例如 `some-uuid-string`)，后续步骤可能会用到。同时，检查您的邮箱，应该会收到一封验证邮件，其中包含一个验证令牌。

## 2. 用户登录 (OAuth2 表单方式)

使用邮箱和密码通过 OAuth2 表单方式登录，获取访问令牌。

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/auth/token" \
-H "Content-Type: application/x-www-form-urlencoded" \
-d "username=testuser%40example.com&password=SecurePassword123!"
```
**注意:** `username` 字段对应的是用户的邮箱，并且需要进行 URL 编码 (例如 `@` 变为 `%40`)。

**预期响应 (示例):**
```json
{
  "access_token": "your_jwt_access_token_here",
  "token_type": "bearer",
  "expires_in": 86400,
  "user": {
    "user_id": "some-uuid-string",
    "nickname": "Test User",
    "email": "yeaonaiwohe1211@163.com",
    "is_verified": false
  }
}
```
复制 `access_token` 的值，后续需要授权的接口会用到它。

## 3. 用户登录 (JSON方式)

使用邮箱和密码通过 JSON 方式登录，获取访问令牌。

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/auth/login" \
-H "Content-Type: application/json" \
-d '{
  "email": "yeaonaiwohe1211@163.com",
  "password": "SecurePassword123!"
}'
```

**预期响应 (示例):**
```json
{
  "access_token": "your_jwt_access_token_here",
  "token_type": "bearer",
  "expires_in": 86400,
  "user": {
    "user_id": "some-uuid-string",
    "nickname": "Test User",
    "email": "yeaonaiwohe1211@163.com",
    "is_verified": false
  }
}
```
复制 `access_token` 的值。

## 4. 执行邮箱验证

使用从注册邮件中获取的验证令牌来验证用户的邮箱。

**假设您的验证令牌是:** `your_email_verification_token_from_email`

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/auth/email-verification/execute" \
-H "Content-Type: application/json" \
-d '{
  "verification_token": "your_email_verification_token_from_email"
}'
```

**预期响应 (示例):**
```json
{
  "message": "邮箱验证成功"
}
```
现在用户的 `is_verified` 状态应该变为 `true`。

## 5. 获取当前用户信息

获取当前已登录用户的信息。需要有效的访问令牌。

**将 `<YOUR_ACCESS_TOKEN>` 替换为您在登录步骤中获取的令牌。**

```bash
curl -X GET "http://127.0.0.1:8000/api/v1/users/me" \
-H "Authorization: Bearer <YOUR_ACCESS_TOKEN>"
```

**预期响应 (示例):**
```json
{
  "user_id": "some-uuid-string",
  "nickname": "Test User",
  "email": "yeaonaiwohe1211@163.com",
  "phone": "13800138000",
  "is_verified": true, // 如果已验证
  "created_at": "YYYY-MM-DDTHH:MM:SS.ffffff",
  "updated_at": "YYYY-MM-DDTHH:MM:SS.ffffff"
}
```

## 6. 更新当前用户信息

更新当前已登录用户的信息（例如昵称或手机号）。需要有效的访问令牌。

**将 `<YOUR_ACCESS_TOKEN>` 替换为您在登录步骤中获取的令牌。**

```bash
curl -X PATCH "http://127.0.0.1:8000/api/v1/users/me" \
-H "Authorization: Bearer <YOUR_ACCESS_TOKEN>" \
-H "Content-Type: application/json" \
-d '{
  "nickname": "Updated Test User",
  "phone": "13900139000"
}'
```

**预期响应 (示例):**
```json
{
  "user_id": "some-uuid-string",
  "nickname": "Updated Test User",
  "email": "yeaonaiwohe1211@163.com",
  "phone": "13900139000",
  "is_verified": true,
  "created_at": "YYYY-MM-DDTHH:MM:SS.ffffff",
  "updated_at": "YYYY-MM-DDTHH:MM:SS.ffffff" // 更新时间会改变
}
```

## 7. 修改当前用户密码

修改当前已登录用户的密码。需要有效的访问令牌，并且用户的邮箱必须已验证。

**将 `<YOUR_ACCESS_TOKEN>` 替换为您在登录步骤中获取的令牌。**

```bash
curl -X PUT "http://127.0.0.1:8000/api/v1/users/me/password" \
-H "Authorization: Bearer <YOUR_ACCESS_TOKEN>" \
-H "Content-Type: application/json" \
-d '{
  "current_password": "SecurePassword123!",
  "new_password": "NewSecurePassword456!"
}'
```

**预期响应:**
*   `HTTP/1.1 204 No Content` (成功)
*   `HTTP/1.1 403 Forbidden` (如果当前密码错误或邮箱未验证)

之后，您需要使用新密码 (`NewSecurePassword456!`) 重新登录。

## 8. 请求密码重置

如果用户忘记密码，可以请求密码重置。系统会向注册邮箱发送一封包含重置令牌的邮件。

**将 `<USER_EMAIL>` 替换为注册时使用的邮箱。**

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/auth/password-reset/request" \
-H "Content-Type: application/json" \
-d '{
  "email": "<USER_EMAIL>"
}'
```

**预期响应 (示例):**
```json
{
  "message": "如果该邮箱已注册，我们已向其发送了密码重置指导"
}
```
检查您的邮箱，应该会收到一封密码重置邮件，其中包含一个重置令牌。

## 9. 执行密码重置

使用从密码重置邮件中获取的令牌来设置新密码。

**假设您的密码重置令牌是:** `your_password_reset_token_from_email`

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/auth/password-reset/execute" \
-H "Content-Type: application/json" \
-d '{
  "reset_token": "your_password_reset_token_from_email",
  "new_password": "AnotherNewPassword789!"
}'
```

**预期响应 (示例):**
```json
{
  "message": "密码重置成功，请使用新密码登录"
}
```
现在用户可以使用新密码 (`AnotherNewPassword789!`) 登录。

## 10. 请求重新发送邮箱验证邮件

如果用户在注册后没有收到验证邮件，或者令牌已过期，可以请求重新发送。需要有效的访问令牌，并且用户邮箱尚未验证。

**将 `<YOUR_ACCESS_TOKEN>` 替换为您在登录步骤中获取的令牌。**

**注意:** 此接口仅在用户邮箱 `is_verified` 为 `false` 时有效。如果已验证，会返回 409 Conflict。

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/auth/email-verification/request" \
-H "Authorization: Bearer <YOUR_ACCESS_TOKEN>"
```

**预期响应 (示例):**
```json
{
  "message": "验证邮件已发送，请查收"
}
```
检查您的邮箱，应该会收到新的验证邮件。然后可以参考步骤 4 执行邮箱验证。

---

请根据您的实际应用配置和需求调整上述命令。