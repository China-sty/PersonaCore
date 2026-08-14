# PersonaCore

通过**多模态线上测评**识别面试对象性格特质的**多智能体系统**。最终目标：在责任心、团队性、抗压、正向情绪等维度上量化打分，用于**筛选目标人群**。

> 当前为 **MVP（Phase 1）**：文字对话 → 大五人格（OCEAN）评分 → 报告。音频、视频模态见 [`plan.md`](plan.md)。

## 特性

- **多智能体协作**：面试官（自适应追问）→ 维度分析师（每维度打分）→ 裁决（融合/筛选判定）→ 报告。
- **大五人格（Big Five / OCEAN）**：尽责性、宜人性、情绪稳定性、外向性、开放性。
- **管理员可配置**：各维度权重、合格线、一票否决、行为锚点、题库（见 `config/dimensions.yaml`）。
- **证据可回溯**：每个评分都要求模型引用原文证据，无证据则降低置信度。
- **LLM 可插拔**：OpenAI 兼容接口，可接 OpenAI / DeepSeek / 通义千问 / 智谱等。

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置 LLM

复制 `.env.example` 为 `.env`，填入你的 OpenAI 兼容接口配置：

```bash
OPENAI_API_KEY=你的key
OPENAI_BASE_URL=https://api.openai.com/v1
LLM_MODEL=gpt-4o-mini
```

（DeepSeek / 通义 / 智谱 等示例见 `.env.example` 内注释。）

### 3. 运行

```bash
python -m personacore.main
```

按提示回答面试问题，结束后在终端输出**完整报告**（面试全记录 + 各维度得分 + 分析）。

每次测评都会保存为**独立文件**（互不覆盖），默认在 `report_output/` 目录：

- `report_output/<run_id>.md` —— 完整 Markdown 报告（所有问题与回复 + 最终分析）
- `report_output/<run_id>.json` —— 结构化数据（面试记录、各维度分数、证据、结论，供程序化分析/入库）

用 `--out-dir` 指定保存目录：

```bash
python -m personacore.main --out-dir my_reports
```

### 4. 冒烟测试（无需 API Key）

```bash
python tests/test_smoke.py
```

## 目录结构

```
PersonaCore/
├─ plan.md                      # 分阶段实施计划
├─ docs/architecture.md         # 架构文档（架构图 + 详细设计）
├─ config/dimensions.yaml       # 大五维度、锚点、题库、权重/阈值
├─ personacore/
│  ├─ main.py                   # CLI 入口
│  ├─ orchestrator.py           # 编排器
│  ├─ session.py                # 运行结果与报告渲染
│  ├─ llm.py                    # OpenAI 兼容 LLM 客户端
│  ├─ config.py                 # 配置加载
│  └─ agents/
│     ├─ interviewer.py         # 面试官 Agent
│     ├─ analyst.py             # 维度分析师 Agent
│     ├─ arbiter.py             # 裁决 Agent
│     ├─ report.py              # 报告 Agent
│     └─ _util.py
└─ tests/test_smoke.py          # 端到端冒烟测试
```

## 说明

本系统输出仅作为招聘辅助参考，最终判断由人工完成。详见 [`plan.md`](plan.md) 中的合规与伦理章节。
