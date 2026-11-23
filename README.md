# d1_squeeze_failureprove

**布林带收缩突破（Bollinger squeeze）** 的失败档案，属于 [量化失败合集 quant-failure-archive](https://github.com/runningshark/quant-failure-archive)。

判定为 **"指标无效"**：它能赚钱靠的是"收盘站上布林上轨"这个突破本身；它的卖点"先收缩"不但没用，条件越严结果越差，完全去掉反而最好。

- 结论和全部数字：[FAILURE_REPORT.md](FAILURE_REPORT.md)
- 复现：`python verify.py`（只需要 Python 3，不用装库），结果写到 `results/output.txt`
- 代码：`strategies/`（策略原文件和对照用的普通突破策略，未改动）、`core/engine.py`（原项目回测引擎，未改动）
- 数据：`data/`，币安现货日线快照，截至 2026-11-23

不构成任何投资建议。
