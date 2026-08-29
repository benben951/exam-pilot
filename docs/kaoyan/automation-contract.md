# 考研自动化共享事实协议

所有考研自动化共享项目文件，不共享彼此的聊天记录。

## 权威写入边界

| 任务 | 读取 | 允许写入 |
|---|---|---|
| 早间动态学习计划 | 月目标、配置、进度、历史记录 | 当日任务卡、计划索引 |
| 23:00日报 | 当日任务卡、用户当日汇报 | study-db、learning-events、dashboard、日报 |
| 21:30晚间督学 | 当日真实记录、任务卡 | 日报缺口提示、明日建议；不覆盖真实数据 |
| 周报 | 最近7天记录、日报、测评 | weekly-review、下周执行量 |
| 月报/录取预测 | 月记录、周报、测评注册 | monthly-report、forecast；概率缺数据时写“数据不足” |
| 报名核验 | 官方公告、progress-state | 报名状态和政策记录 |

## 统一事实源

- 计划：`daily-report/`、`data/daily-plan-index.json`
- 总体执行计划：`plan/final-kaoyan-war-plan-2026.md`
- 学习真实记录：`data/study-db.json`
- 题目/复习事件：`data/learning-events.json`
- 进度状态：`data/progress-state.json`
- 测评资格：`data/assessment-records.json`、`data/holdout-register.json`
- 目标：`data/monthly-targets.json`
- 政策：`plan/pku-policy-radar.md`
- 墨墨词汇统计：`data/maimemo-progress.json`（由 `.scripts/maimemo_sync.ps1` 生成）

## 交接规则

1. 自动化输出的聊天内容不是事实，只有写入上述文件的内容才是共享事实。
2. 缺失值写缺失，不写0，不从另一任务的聊天猜测。
3. 后运行的任务先读取前一任务已经写入的文件，再生成结果。
4. 同一字段冲突时保留原记录并标记冲突，不能静默覆盖。
5. 当前聊天、Obsidian和所有自动化都以这些文件为准。
