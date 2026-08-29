---
tags: [英语, 墨墨, API, 数据记录]
---

# 墨墨背单词接入规则

墨墨官方开放API支持云词本管理、词汇查询和学习数据互通，可读取背诵进度与待复习词汇。

- 使用说明：https://www.maimemo.com/pages/openapi/introduction
- 技术文档：https://open.maimemo.com/

## 接入步骤

1. 在墨墨App打开“我的 → 更多设置 → 实验功能 → 开放API”。
2. 复制个人Token，只粘贴到本机环境变量或密码管理器，不要发到聊天、不写入项目。
3. 确认Token已在本机配置后，再编写本地只读同步脚本。
4. 测试通过后，每日晚报读取当天汇总并写入项目。

本地同步命令：

```powershell
.\.scripts\maimemo_sync.ps1
```

同步快照写入 `data/maimemo-progress.json`，日报只读取快照中的统计字段。

## 记录字段

```text
date
new_words
reviewed_words
due_words
mastery_or_recall_rate
source_notebook
api_sync_status
```

## 边界

- 默认只读学习统计，不自动修改云词本或删除词汇。
- 如需创建云词本，必须单独确认后再启用写入权限。
- Token不进入Markdown、JSON、Git、日志或日报正文。
- 墨墨数据用于英语过程追踪，不直接进入录取概率。
- API失败或字段缺失时写“数据不足”，不从打卡天数猜测掌握度。
