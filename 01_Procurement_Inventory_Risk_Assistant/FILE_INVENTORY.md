# FILE INVENTORY - 01_Procurement_Inventory_Risk_Assistant

| 路径 | 类型 | 用途说明 |
| --- | --- | --- |
| `README.md` | 文档 | 测试集使用手册、M01–M10 评测指标定义与模型架构说明 |
| `arguments.py` | 代码 | 评测命令行超参数、随机种子与数据集/结果路径配置 |
| `experiments.py` | 代码 | 主实验与自动化评测执行入口 |
| `models/deterministic_engine.py` | 代码 | `R-SLA` 作业日历换算、部分收货数值水位守恒日桶引擎与七层护栏校验器 |
| `models/llm_adapter.py` | 代码 | 候选大模型（Qwen3-8B/32B、DeepSeek-V3.2）注册表与单轮调用预算骨架 |
| `dataset/structured_cases_v2_1.json` | 数据 | 53 条确定性规则、异常输入拦截与全生命周期策略基准集 |
| `dataset/seed_eval_30.json` | 数据 | 30 条 6 大类高仿真口语/多轮/越权/降级评估种子集（含 Gold） |
| `dataset/tuning_fewshot_dev.json` | 数据 | 6 条与评估种子物理隔离的 Few-Shot 调优样本 |
| `dataset/blind_structured_53_inputs.jsonl` | 数据 | 无真值标签的结构化盲测输入文件 |
| `dataset/blind_seed_30_inputs.jsonl` | 数据 | 无真值标签的口语对话盲测输入文件 |
| `dataset/schemas/t_extract.schema.json` | 契约 | Draft 2020-12 供应商承诺候选抽取 JSON Schema |
| `results/verification_manifest.json` | 结果 | 执行环境、混淆矩阵、通过统计与文件 SHA-256 指纹 |
| `results/structured_53_results.json` | 结果 | 53 条结构化基准逐例评测结果明细 |
| `results/mutation_8_results.json` | 结果 | 8 类人为故障变异注入捕获结果 |
| `results/seed_30_pipeline_results.json` | 结果 | 30 条种子端到端管线评测详细输出 |
| `results/seed_30_summary.csv` | 结果 | 30 条种子评测结果 CSV 汇总表 |
| `results/benchmark_evaluation_report.md` | 结果 | 自动生成的 Markdown 离线基准实测报告 |
| `scripts/export_blind_inputs.py` | 脚本 | 盲测无标签 JSONL 独立导出工具 |
| `docs/项目一PRD_1.0.md` | 文档 | 项目一完整产品需求、架构契约与评测闭环主文档 |
| `frontend/index.html` | 前端 | 全景三栏产品与技术白板交互式预览页 |
| `fig_use/*.png` | 图表 | 系统架构图、As-Is/To-Be 泳道图、UI 原型图与选型矩阵图 |
