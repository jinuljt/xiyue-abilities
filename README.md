# 喜悦 Voice 能力库

声明式语音流程样例、JSON Schema 和离线校验工具。流程可组合播报、等待确认和计时，实际播报和调度由喜悦 Agent 负责。

## 验证和预览

需要 Python 3.10 或更新版本，无第三方依赖。

```sh
python3 tools/check.py
python3 -m unittest discover -s tools -v
python3 tools/check.py capabilities/tea-guide.json --preview --value tea=乌龙茶
```

离线预览展示流程文本和步骤，无需连接音箱。

## 目录

| 路径 | 内容 |
| --- | --- |
| [`capabilities/`](capabilities/) | 十秒计时、确认式提醒、烹饪计时、起身休息和泡茶样例 |
| [`manifest.schema.json`](manifest.schema.json) | 流程声明格式 |
| [`tools/`](tools/) | 校验、文字预览和测试 |

编写流程时为每个能力指定稳定 ID 和版本，定义调用参数，并在步骤中使用同名变量。启用状态、实时参数、运行计划由使用该流程的 Agent 管理。
