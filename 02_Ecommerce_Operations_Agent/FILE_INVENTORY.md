# FILE INVENTORY - 02_Ecommerce_Operations_Agent

| 路径 | 类型 | 用途说明 |
| --- | --- | --- |
| `README.md` | 文档 | 项目二测试集使用手册、M01–M10 评测指标定义与分层模型架构说明 |
| `arguments.py` | 代码 | 命令行超参数、候选规划/解释模型标识与路径配置 |
| `experiments.py` | 代码 | 主实验与自动化基准评测运行入口 |
| `models/deterministic_engine.py` | 代码 | 三级指标可用度门禁、防差分反推锁、`Fraction` 有理数双分解桥与 L1–L7 解释护栏 |
| `models/llm_adapter.py` | 代码 | 固定看板基线、轻量规划模型与推理大模型分层架构骨架（固化 `vLLM` 规范） |
| `dataset/sim_01_baseline_snapshot.json` | 数据 | `SIM-01` 两店四品标准经营快照、账单水位与双分解桥真值样例 |
| `dataset/structured_cases_26.json` | 数据 | 26 条确定性算术、覆盖度、权限与七层护栏断言集 |
| `dataset/seed_eval_30.json` | 数据 | 30 条 6 大类电商运营高仿真种子评估集（`OPS-01`–`OPS-30`） |
| `dataset/tuning_fewshot_dev.json` | 数据 | 4 条与评估种子物理隔离的 Few-Shot 调优示例 |
| `dataset/blind_ops_seed_30_inputs.jsonl` | 数据 | 无真值标签的电商运营提问盲测输入文件 |
| `dataset/schemas/t_plan.schema.json` | 契约 | Draft 2020-12 受控指标工具规划 JSON Schema |
| `dataset/schemas/t_explain.schema.json` | 契约 | Draft 2020-12 事实/假设分离解释与核查草稿 JSON Schema |
| `results/verification_manifest.json` | 结果 | 运行环境、模型配置、通过统计与文件 SHA-256 指纹 |
| `results/structured_26_results.json` | 结果 | 26 条确定性指标与护栏断言逐例明细 |
| `results/mutation_6_results.json` | 结果 | 6 类高危业财变异注入捕获结果 |
| `results/seed_30_ops_results.json` | 结果 | 30 条运营种子管线评测详细输出 |
| `results/seed_30_ops_summary.csv` | 结果 | 30 条运营种子结果 CSV 汇总表 |
| `results/benchmark_evaluation_report.md` | 结果 | 自动生成的 Markdown 离线基准实测报告 |
| `scripts/export_blind_inputs.py` | 脚本 | 无标签盲测输入 JSONL 独立导出工具 |
| `docs/项目二PRD_V1.0.md` | 文档 | 项目二完整产品需求、架构契约与评测闭环主文档 |
| `docs/竞品分析-项目二_V1.0.md` | 文档 | 五大竞品（慧经营/聚胜算/金蝶/观远/帆软）深度检索分析报告 |
| `frontend/index.html` | 前端 | 全景三栏产品与技术白板交互式预览页 |
| `fig_use/*.png` | 图表 | 系统七层架构图、As-Is/To-Be 泳道图、UI 原型图与选型矩阵图 |
