# License 授权管理指南

本系统支持 License 授权管理，可以控制软件的使用期限、功能权限和账号数量限制。

## 目录

- [License 结构](#license-结构)
- [生成 License](#生成-license)
- [导入 License](#导入-license)
- [验证机制](#验证机制)
- [常见问题](#常见问题)

## License 结构

每个 License 包含以下信息：

| 字段 | 说明 | 示例 |
|------|------|------|
| `license_id` | License 唯一标识 | LIC-20260329-4167 |
| `customer_name` | 客户名称 | 测试客户 |
| `expire_date` | 到期日期 (YYYY-MM-DD) | 2026-04-28 |
| `max_accounts` | 最大账号数 | 10 |
| `features` | 功能列表 | ["auto_reply", "knowledge_base"] |
| `issued_at` | 签发时间 | 2026-03-29 13:14:57 |
| `signature` | 数字签名 | (加密字符串) |

### 功能列表

- `all` - 启用所有功能
- `auto_reply` - 自动回复
- `knowledge_base` - 知识库
- `ai_learning` - AI 学习优化
- `emotion_alert` - 情绪告警

## 生成 License

### 基本用法

```bash
# 生成 30 天试用 License
python scripts/generate_license.py --customer "测试客户" --days 30

# 生成指定到期日期的 License
python scripts/generate_license.py --customer "正式客户" --expire "2025-12-31"

# 生成限制账号数的 License
python scripts/generate_license.py --customer "小型企业" --days 365 --max-accounts 5

# 生成指定功能的 License
python scripts/generate_license.py --customer "高级客户" --days 365 --features auto_reply,knowledge_base
```

### 参数说明

| 参数 | 简写 | 说明 | 默认值 |
|------|------|------|--------|
| `--customer` | `-c` | 客户名称（必填） | - |
| `--days` | `-d` | 有效期天数 | 30 |
| `--expire` | `-e` | 到期日期 (YYYY-MM-DD) | - |
| `--max-accounts` | `-m` | 最大账号数 | 999 |
| `--features` | `-f` | 功能列表（逗号分隔） | all |
| `--output` | `-o` | 输出文件路径 | licenses/<name>_<date>.key |
| `--plain` | - | 输出纯 JSON 格式 | False |
| `--key` | - | 签名密钥（高级） | - |

### 输出示例

```
==================================================
✅ License 生成成功！
==================================================

📋 License 信息：
  • License ID: LIC-20260329-4167
  • 客户名称: 测试客户
  • 到期日期: 2026-04-28
  • 剩余天数: 30 天
  • 最大账号数: 999
  • 功能列表: all
  • 签发时间: 2026-03-29 13:14:57

📁 文件路径: licenses/测试客户_20260329.key
==================================================
```

## 导入 License

### 通过界面导入

1. 打开软件，进入 **设置 > 软件授权管理**
2. 点击 **导入 License** 按钮
3. 选择 `.key` 或 `.lic` 文件
4. 查看状态确认导入成功

### 手动放置

将 License 文件复制到以下位置：

- **macOS**: `~/Library/Application Support/智能客服/license.key`
- **Windows**: `%APPDATA%/智能客服/license.key`
- **开发环境**: 项目根目录下的 `license.key`

## 验证机制

### 签名验证

每个 License 文件包含数字签名，用于验证文件是否被篡改。签名使用 HMAC-SHA256 算法生成。

### 过期检查

系统启动时和添加账号时会检查 License 是否过期。过期后：

- 软件仍可打开，但会显示警告
- 无法添加新账号
- 现有账号的自动回复功能可能受限

### 账号限制

添加账号时会检查当前账号数量是否超过 License 限制。超过限制时：

- 无法添加新账号
- 提示用户升级 License

## 常见问题

### Q: License 导入失败怎么办？

1. 检查文件格式是否正确（JSON 或 Base64 编码）
2. 确认文件未被修改（签名验证失败）
3. 检查到期日期是否有效
4. 查看系统日志获取详细错误信息

### Q: 如何延长 License 有效期？

生成新的 License 文件并导入，新文件会覆盖旧文件。

### Q: 可以同时在多台设备使用吗？

License 文件可以复制到多台设备，但建议根据实际购买数量控制使用范围。

### Q: 如何查看当前 License 信息？

在软件中进入 **设置 > 软件授权管理**，可以查看：
- 授权状态
- License ID
- 客户名称
- 到期日期和剩余天数
- 账号限额
- 授权功能

### Q: License 文件可以修改吗？

不可以。任何修改都会导致签名验证失败，License 将失效。

## 安全建议

1. **保管好密钥**：生成 License 使用的密钥应妥善保管
2. **定期备份**：客户应备份 License 文件
3. **不要修改**：任何对 License 文件的修改都会使其失效
4. **及时续费**：在 License 到期前及时申请续期

## 技术支持

如有 License 相关问题，请联系管理员获取支持。
