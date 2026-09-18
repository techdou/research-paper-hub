# Research Paper Hub

这是一个面向长期科研与论文写作的**单入口 Agent Skill**。它路由两个上游技能族——CCFA-Skills（CS/CCF 系期刊会议）与 nature-skills（Nature 系期刊）——并保证任何两个技能永远不会争抢同一个产物。

核心设计：

```text
用户科研任务
    ↓
research-paper-hub   ← 唯一隐式入口
    ↓
内部 Router：任务拆解 + 每一步唯一 owner
    ↓
内部 Orchestrator：状态 / 存档 / 版本 / 证据链
    ↓
按需读取 .research/vendor 中的 CCFA / Nature playbook
```

## 核心特性

1. **每步唯一 owner**：复合请求（如"找一篇最近的论文，精读后做组会汇报"）被拆解成有序步骤，每步恰好指派一个上游技能；辅助能力只做审计或前置产物，不产出同一种主产物。
2. **单一入口，按需加载**：只有一个可发现的 `SKILL.md`，Router/Orchestrator 是内部模块而非顶层技能，显著降低宿主级触发竞争。
3. **版本锁定的上游**：上游技能同步到项目 `.research/vendor/` 下作为 playbook，每个都带 commit / git tree SHA / 内容 SHA-256；更新可随时检查，但**只有明确请求才应用**，保证已写内容可复现。
4. **持久化研究状态**：run 记录、产物、claim–evidence 链、稿件修订历史、审稿意见台账、快照都存于 `<project>/.research/`，跨会话存活。
5. **范文桥梁**：`ccf-paper-to-exemplar` 负责从参考论文提取故事结构、段落角色与论证编排（绝不抄句子），打通"读论文 → 写自己的论文"。

## 安装

将整个 `research-paper-hub/` 文件夹放到 Agent Skills 用户技能目录：

```text
$HOME/.agents/skills/research-paper-hub/
```

或者直接作为 Skill ZIP 导入支持 Agent Skills 格式的产品。

依赖：

```bash
pip install -r requirements.txt
```

- Python 3.11+（推荐）
- `git` 仅在上游技能同步时需要

## 第一次使用

```bash
python scripts/hub.py init /path/to/my-paper \
  --profile examples/remote-sensing-profile.yaml

python scripts/hub.py sync --project /path/to/my-paper --apply --recommended
```

这会把选定的 CCFA / Nature playbook 同步到：

```text
/path/to/my-paper/.research/vendor/
```

不会把它们注册成独立的顶层隐式技能。

## 常用命令

```bash
# 路由一个复合任务
python scripts/hub.py route \
  --project /path/to/my-paper \
  --task "找一篇最近的多模态多标签遥感论文，精读后做组会汇报"

# 只检查更新，不应用
python scripts/hub.py sync --project /path/to/my-paper --check

# 单独更新某个技能（会自动带上必要的 shared dependency）
python scripts/hub.py sync --project /path/to/my-paper \
  --apply --skill ccf-paper-to-exemplar

# 回滚该技能到上一个项目本地版本
python scripts/hub.py sync --project /path/to/my-paper \
  --rollback --skill ccf-paper-to-exemplar

# 大改稿前创建快照
python scripts/hub.py snapshot --project /path/to/my-paper \
  --note "before Introduction restructure"

# 校验项目状态
python scripts/hub.py validate --project /path/to/my-paper
```

更新原则：默认允许检查更新，但不自动应用。论文写到一半时突然切换上游技能规则会破坏可复现性，所以每次 run 都记录实际使用的 commit/tree hash。

## 论文写作链路

```text
nature-academic-search
  → nature-reader
  → ├─ nature-paper-card        学研究内容
    └─ ccf-paper-to-exemplar   学 Story / Moves / Evidence
                 ↓
          venue-aware writer
                 ↓
        one primary reviewer
                 ↓
  ccf-integrity-auditor + nature-ref-verifier
                 ↓
          revision + snapshot
```

写作主笔按目标期刊会议二选一：CCF/AAAI/CVPR/NeurIPS/ACM/IEEE/TGRS 系 → `ccf-paper-writer`；Nature 系 → `nature-writing`。润色仅在主写作 pass 之后进行。

## 目录结构

```text
research-paper-hub/
├── SKILL.md              # 前门：工作流规则与调用契约
├── agents/openai.yaml    # 宿主调用元数据
├── references/           # Router / Orchestrator / 产物模型 / 策略
├── config/               # 能力、路由、阶段、同步契约
├── scripts/              # hub.py CLI 及支撑模块
├── evals/                # 触发与路由回归用例
├── examples/             # 示例项目 profile
├── assets/               # 项目 profile 模板
└── tests/                # 测试套件
```

## 上游技能

本仓库不分发上游代码；上游技能在 sync 时按需拉取到用户项目中，并保留其原始许可证：

| 技能族 | 上游仓库 | 许可证 | 覆盖能力 |
|---|---|---|---|
| CCFA-Skills | [mikubaka88/CCFA-Skills](https://github.com/mikubaka88/CCFA-Skills) | MIT | 文献检索/监控、idea 评审、实验设计、写作、审稿、人性化润色、rebuttal、完整性审计、科研图、投稿检查 |
| nature-skills | [Yuan1z0825/nature-skills](https://github.com/Yuan1z0825/nature-skills) | Apache-2.0 | 文献发现、精读、论文卡片、统计、引用核验、结果图、语言润色、写作、审稿、返修、组会 PPT |

## 测试

```bash
python tests/test_all.py
```

覆盖路由回归（复合检索/精读/PPT、范文→写作、期刊切换、产物复用、更新路由、归档路由）与基于 fake-Git 的逐技能同步行为。

## 许可证

[MIT](LICENSE.txt)。上游 playbook 保持其各自许可证（见上表），本仓库不重新分发上游代码。
