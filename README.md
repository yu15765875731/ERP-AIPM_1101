# ERP-AIPM 智能决策双项目评测基准与受控模型架构仓库

> **lybj@Huice** | 2026-11-26 | E-Commerce ERP AI Product & Algorithm Benchmark Suite (`ERP-AIPM_1101`)

---

## 一、项目介绍

本仓库是围绕**电商 ERP（旺店通/慧策生态）全业务链**构建的 AI 产品评测基准集（Benchmark Dataset）、受控双核模型架构骨架与可复跑自动化验证工程。仓库包含同一电商 ERP 业务主干上**上下游互补、职责严格解耦**的两个核心 AI 项目测试子库：

1. **[01_Procurement_Inventory_Risk_Assistant](./01_Procurement_Inventory_Risk_Assistant/)** —— **项目一：采购库存风险问答助手（供应链上游）**
   - 面向采购经办、仓库主管与负责人，解决供应商临时延期、拆批与微信口语含糊回复下的**到仓转可售（`R-SLA`）时序缺口复核与实物恢复追踪**。
2. **[02_Ecommerce_Operations_Agent](./02_Ecommerce_Operations_Agent/)** —— **项目二：电商运营Agent（经营复盘下游）**
   - 面向电商运营负责人、账务对接人与商家老板，解决多店多 SKU 周度经营问数、**贡献利润 `CM1` 双视角分解桥穿透、防底价差分反推与版本化核查跟进**。

### 仓库核心定位

- **标准化算法评测架构**：严格遵循大模型评测工程规范组织（`dataset/`、`models/`、`results/`、`scripts/`、`fig_use/`、`frontend/`、`docs/`、`arguments.py`、`experiments.py`）
- **确定性底座与七层护栏验证**：100% 零第三方黑盒依赖即可一键复跑全部算术守恒、乐观锁 CAS、权限隔离与 L1–L7 输出护栏测试
- **大模型盲评就绪（LLM-Ready）**：内置 Draft 2020-12 JSON Schema 强契约、物理隔离的 Few-Shot 调优集与无真值标签盲测导出文件（`blind_*_inputs.jsonl`）

---

## 二、双项目考查方向与评测指标总览（M01—M10）

### 1. 上下游双项目核心考查点对照

| 维度 | 项目一：采购库存风险问答助手（上游供给侧） | 项目二：电商运营Agent（下游经营侧） |
|-----|------------------------------------------|-----------------------------------|
| **核心算术引擎** | 离散日桶 FIFO 积压偿还守恒 ＋ `R-SLA` 有效作业日历换算 | `Decimal/Fraction` 精确有理数五项分项桥 ＋ 规模/费率反事实参照 |
| **核心防坑门禁** | `in_snapshot_qty` 部分收货水位防双计 ＋ 未到仓子批余额校验 | `TIER_1~3` 覆盖度分级（缺投流禁补0、店级广告禁粗暴拆SKU）＋ 账单水位锁 |
| **AI 语义子任务** | `T-INTENT` 路由 ＋ `T-EXTRACT` 口语/改口/复合不确定抽取 ＋ `T-EXPLAIN` | `T-PLAN` 白名单指标工具编排（轻量 Text2DSL）＋ `T-EXPLAIN` 事实/假设分离 |
| **敏感安全红线** | 跨租户隔离、禁止未知承诺自动升确认、禁止外部自动下采购单 | 局部店权禁静默裁剪冒充全盘、**无 `COGS` 底价权限封锁 `CM1` 防减法差分反推** |

### 2. 本次双项目十项正式评测指标体系对照表

| 编号 | 项目一指标（采购库存风险问答助手） | 项目二指标（电商运营Agent） | 共同防刷分与准入准则 |
|-----|----------------------------------|---------------------------|---------------------|
| **M01** | 库存原因未按承诺履约订单率（↓） | 全可标注任务正确终态率（↑，`≥90%`） | 超时与异常保留在分母，严禁剔除难题刷分 |
| **M02** | 风险遗漏率（↓）＋ 风险精确率（↑，报混淆矩阵） | 跨岗单次复盘净有效操作耗时（↓，降 `≥20%`） | 剥离系统等待，分角色统计防跨岗负担转嫁 |
| **M03** | 跨岗单次复核净有效操作耗时（↓，降 `≥20%`） | 查询语义与范围槽位全对率（↑，`≥95%`） | 配对任务平衡顺序消除学习效应 |
| **M04** | 全受理请求正确终态率（↑，`≥90%`） | 关键经营事实与 `pct_pts` 全对率（↑，`≥95%`） | 双报全量终态率与可计算子集完成率 |
| **M05** | 自由提问多意图集合完全匹配率（↑，`≥95%`） | 主张有据率（`≥98%`）＋**必需主张覆盖率（`=100%`）** | 空答或漏报核心亏损/延期直接判任务失败 |
| **M06** | 承诺批次集合完全正确率（↑，`≥95%`，再确认零误升） | 受控白名单工具轨迹与参数全对率（↑，`≥95%`） | 不用字段平均分掩盖致命状态错误 |
| **M07** | 必需口径证据 `Recall@5`（↑，`≥90%`） | 适用口径证据 `Recall@5`（↑，`≥90%`，停用标 `N/A`） | 测检索固定语料放开证据包；禁放大 TopK 混过关 |
| **M08** | 关键主张有据率（`≥98%`）＋**必需主张覆盖率（`=100%`）** | 四维安全红线台账（**真实逃逸事件数 `= 0`**） | 无权数据拼入外部模型请求出域即计为真实泄露逃逸 |
| **M09** | 四维安全红线台账（**真实逃逸事件数 `= 0`**） | 分终态服务端 P95（`≤15s`）＋ 浏览器渲染（`≤1s`） | 一票否决门禁，平均高分不可抵消任何红线事件 |
| **M10** | 服务端终态 P95（`≤10s`）＋ 浏览器渲染（`≤1s`） | 单正确完成任务全口径总成本（↓） | 计入失败重试 Token 与日常跨岗人审工时折算成本 |

---

## 三、技术栈与候选模型配置

| 层级 | 采用技术 / 候选组件 | 说明 |
|-----|-------------------|------|
| **评测与确定性底座** | Python `3.10+`（`decimal`, `fractions`, `hashlib`, `unittest/assert`） | 零外部黑盒依赖，跨 Windows / Linux 开箱即跑 |
| **业务后端对接栈** | Java 11 / Spring Boot / PostgreSQL 18（CAS + 受限角色 RLS） | 承接作者既有 [Smart-Warehouse](https://github.com/yu15765875731/Smart-Warehouse) 工程体系 |
| **候选生成大模型** | `Qwen/Qwen3-8B`、`Qwen/Qwen3-32B`、`DeepSeek-V3.2` | 私有化强制推荐 `vLLM`（`≥16k` 上下文，禁用 `Ollama` 防丢 System Prompt） |
| **按需检索与重排** | PostgreSQL 精确查询 ＞ BM25 + `pgvector`（`Qwen3-Embedding-0.6B` / `bge-m3`）+ `Qwen3-Reranker-0.6B` | 结构化快照与固定参数 100% 走关系库，严禁万物皆向量 |
| **架构可视化预览** | 原生 HTML5 交互式白板 + 高清分层架构图 | 每个子项目均配备 `frontend/index.html` 与 `fig_use/` 图集 |

---

## 四、仓库全局目录结构

```text
ERP-AIPM_1101/ (E:\AIPM CLASS\测试集)
├── 01_Procurement_Inventory_Risk_Assistant/    # 项目一：采购库存风险问答助手测试集与架构
│   ├── dataset/                                # 53条结构化集 + 30条口语种子 + 6条调优集 + 盲测JSONL + Schema
│   ├── docs/                                   # 《项目一PRD_1.0.md》完整正式定稿
│   ├── fig_use/                                # 全景图与6张高清彩色架构/泳道/UI原型插图
│   ├── frontend/                               # index.html 交互式缩放白板
│   ├── models/                                 # 水位日桶守恒引擎、七层护栏与可插拔LLM适配层
│   ├── results/                                # 实测输出JSON、CSV汇总、SHA256指纹与评测报告
│   ├── scripts/                                # 盲测数据导出脚本
│   ├── arguments.py                            # 命令行实验参数配置
│   ├── experiments.py                          # 项目一主评测入口
│   ├── FILE_INVENTORY.md                       # 项目一文件清单
│   └── README.md                               # 项目一详细使用指南与指标说明
├── 02_Ecommerce_Operations_Agent/              # 项目二：电商运营Agent测试集与架构
│   ├── dataset/                                # SIM-01快照 + 26条规则护栏集 + 30条运营种子 + 盲测JSONL + Schema
│   ├── docs/                                   # 《项目二PRD_V1.0.md》与《竞品分析-项目二_V1.0.md》
│   ├── fig_use/                                # 全景图与6张高清彩色架构/泳道/UI原型插图
│   ├── frontend/                               # index.html 交互式缩放白板
│   ├── models/                                 # Tier1-3门禁、防差分反推、Fraction双桥引擎与分层LLM骨架
│   ├── results/                                # 实测输出JSON、CSV汇总、SHA256指纹与评测报告
│   ├── scripts/                                # 盲测数据导出脚本
│   ├── arguments.py                            # 命令行实验参数配置
│   ├── experiments.py                          # 项目二主评测入口
│   ├── FILE_INVENTORY.md                       # 项目二文件清单
│   └── README.md                               # 项目二详细使用指南与指标说明
├── run_all_benchmarks.py                       # 一键串行运行双项目全量基准测试总控脚本
├── FILE_INVENTORY.md                           # 仓库全局文件索引
├── .gitignore                                  # 标准 Python / IDE / 缓存忽略规则
└── README.md                                   # 本总览说明文档
```

---

## 五、一键运行与快速验证

在仓库根目录下直接执行总控脚本，即可在 3 秒内复跑两个项目的全部确定性规则、随机物理/有理数守恒、故障变异注入与 60 条种子管线验证，并刷新两个子目录下的 `results/` 输出：

```bash
python run_all_benchmarks.py
```

也可单独进入任一子项目运行自定义实验参数：

```bash
# 单独运行项目一测试集
python 01_Procurement_Inventory_Risk_Assistant/experiments.py --num_property_runs 300

# 单独运行项目二测试集
python 02_Ecommerce_Operations_Agent/experiments.py --num_property_runs 200
```

---

## 六、双项目离线基准实测汇总（`results/` 已保存产物）

| 项目子库 | 结构化规则与护栏基准 | 故障变异注入捕获（Mutation） | 随机守恒属性测试（Property） | 高仿真业务种子管线 | 调优/评估交叉泄漏 |
|---------|--------------------|----------------------------|----------------------------|------------------|-----------------|
| **01 采购库存风险问答助手** | **`53 / 53` 通过** | **`8 / 8` 捕获（100%）** | **`300 / 300` 守恒** | **`30 / 30` 通过** | **`0` 重叠** |
| **02 电商运营Agent** | **`26 / 26` 通过** | **`6 / 6` 捕获（100%）** | **`200 / 200` 守恒** | **`30 / 30` 通过** | **`0` 重叠** |

- 项目一详细实测报告：[01_Procurement_Inventory_Risk_Assistant/results/benchmark_evaluation_report.md](./01_Procurement_Inventory_Risk_Assistant/results/benchmark_evaluation_report.md)
- 项目二详细实测报告：[02_Ecommerce_Operations_Agent/results/benchmark_evaluation_report.md](./02_Ecommerce_Operations_Agent/results/benchmark_evaluation_report.md)

---

> **lybj@Huice** | 电商 ERP 智能决策产品与评测基准工程 | 2026年11月
