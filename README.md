# PersonaCore

通过**多模态线上测评**识别面试对象性格特质的**多智能体系统**。最终目标：在责任心、团队性、抗压、正向情绪等维度上量化打分，用于**筛选目标人群**。

> 当前为 **MVP（Phase 1）**：文字对话 → 大五人格（OCEAN）评分 → 报告。音频、视频模态见 [`plan.md`](plan.md)。

## 特性

- **多智能体协作**：面试官（自适应追问）→ 维度分析师（每维度打分）→ 裁决（融合/筛选判定）→ 报告。
- **大五人格（Big Five / OCEAN）**：尽责性、宜人性、情绪稳定性、外向性、开放性。
- **管理员可配置**：各维度权重、合格线、一票否决、行为锚点、题库（见 `config/dimensions.yaml`）。
- **证据可回溯**：每个评分都要求模型引用原文证据，无证据则降低置信度。
- **LLM 可插拔**：OpenAI 兼容接口，可接 OpenAI / DeepSeek / 通义千问 / 智谱等。
- **CLI + Web 双入口**：命令行交互 + 浏览器在线测评（FastAPI + 简单前端）。
- **数据持久化 + 管理面板**：SQLite 自动落库，`/admin` 查看候选人列表、分数与报告。

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

### 4. Web 模式（在线访问）

```bash
python -m uvicorn personacore.web:app --host 0.0.0.0 --port 8000
```

浏览器打开 `http://localhost:8000`，即可聊天式进行面试。

```
POST /interview/start            开始面试
POST /interview/{sid}/message    提交回答
GET  /interview/{sid}/report     获取报告
```

### 5. 冒烟测试（无需 API Key）

```bash
python tests/test_smoke.py
```

## 管理员面板

面试结束后，结果会**自动落库到 SQLite**（`data/personacore.db`），管理员可随时查看。

- 访问 `http://<域名或IP>/admin`
- 登录密码在 `.env` 配：`ADMIN_PASSWORD=你的密码`（默认 `admin123`，**务必修改**）
- 功能：候选人列表（综合分 / 结论 / 各维度分）→ 点进去看完整报告

```bash
# .env 增加一行
ADMIN_PASSWORD=你的强密码
```

## 目录结构

```
PersonaCore/
├─ plan.md                      # 分阶段实施计划
├─ docs/architecture.md         # 架构文档（架构图 + 详细设计）
├─ config/dimensions.yaml       # 大五维度、锚点、题库、权重/阈值
├─ personacore/
│  ├─ main.py                   # CLI 入口
│  ├─ web.py                    # FastAPI Web 入口
│  ├─ engine.py                 # 面试状态机（CLI/Web 共用）
│  ├─ orchestrator.py           # CLI 编排（驱动 engine）
│  ├─ session.py                # 运行结果与报告渲染
│  ├─ store.py                  # SQLite 持久化
│  ├─ llm.py                    # OpenAI 兼容 LLM 客户端
│  ├─ config.py                 # 配置加载
│  └─ agents/
│     ├─ interviewer.py         # 面试官 Agent
│     ├─ analyst.py             # 维度分析师 Agent
│     ├─ arbiter.py             # 裁决 Agent
│     ├─ report.py              # 报告 Agent
│     └─ _util.py
├─ web/index.html               # Web 前端（聊天界面）
├─ web/admin.html               # 管理员面板前端
├─ data/                        # SQLite 数据库（gitignore）
├─ deploy/                      # 部署：systemd / nginx / deploy.sh
└─ tests/
   ├─ test_smoke.py             # CLI 冒烟测试
   ├─ test_web.py               # Web 冒烟测试
   └─ test_admin.py             # 管理面板冒烟测试
```

## 部署到服务器（阿里云 ECS）

Web 化后可用一键脚本部署（Ubuntu/Debian）：

```bash
sudo bash deploy/deploy.sh
```

脚本会自动：装系统依赖 → 拉代码 → 建 venv 装依赖 → 配 systemd → 配 nginx。

- 首次会提示你先编辑 `/opt/personacore/.env` 填入密钥，填完重跑脚本即可。
- 完成后浏览器访问 `http://<你的公网IP>`。
- 服务管理：`systemctl status personacore`；日志：`journalctl -u personacore -f`。
- 配置文件：`deploy/personacore.service`（systemd）、`deploy/nginx.conf`（反向代理）。

> 注意：会话目前存内存，重启进程会清空；报告生成（多智能体分析）约需数十秒。

## 说明

本系统输出仅作为招聘辅助参考，最终判断由人工完成。详见 [`plan.md`](plan.md) 中的合规与伦理章节。
