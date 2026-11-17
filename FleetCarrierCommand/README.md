# Fleet Carrier Command (FCC)

Starfield 独立旗舰与护航舰系统；目标是类似 No Man's Sky Freighter 的舰队玩法，而不是让所有飞船跟随玩家。

## 当前状态：P0 源码探针 / M0 设计（未发布）

本分支目前**只有项目设计、Papyrus 源码探针和人工验收方案**。尚未用 Creation Kit 编译，尚无 .esm / .pex / SFSE DLL，也没有在游戏进程内验证舰船实体化、持续 Follow Package 或驾驶员缺席时的自主驾驶。不能作为可安装 Mod 使用。

目标测试环境：Starfield 1.16.244 + Shattered Space；使用者实测 SFSE 启动成功。SFSE 可运行不代表本项目 DLL 已兼容；当前未包含 DLL。

## 硬性功能要求

- 玩家拥有的**任意 Ship Builder 飞船**均可成为旗舰和护航舰；不采用固定预制船或舰船外观克隆。
- 一艘 NPC/AI 控制旗舰 + 0 到任意数量护航舰；玩家驾驶另一艘独立飞船。
- 所有舰船是**玩家实际拥有的不同飞船**；成员数量不超过玩家可用飞船总数。不额外设定 4 艘限制；至少需要两艘不同玩家飞船才能同时拥有个人船与旗舰。
- 旗舰是舰队根节点；护航舰的追随目标是旗舰，**不是玩家**。玩家可驾驶个人船自由离开。
- 每艘舰船**最多一名舰长**：可指定已有同伴/船员；未指定则由舰船 AI 控制。绝不凭空创建、隐藏或替换 NPC 舰长。同一同伴不得同时占用两艘船。
- 不能破坏飞船改名、Ship Builder 改装、停泊、出售或存档。操作前需验证真实飞船身份/生命周期。
- 不擅自改变玩家 Home Ship，不吞掉舰船，不自动复制船体，不擅自部署测试飞船。

## 工程目录

- Sources/Papyrus/FCC_P0_InventoryProbe.psc：只读枚举玩家自有飞船与 Home Ship。
- Sources/Papyrus/FCC_P0_AIProbe.psc：显式授权后、仅针对非 Home Ship 的 AI 与一次性寻路探针（不是编队系统）。
- docs/M0_SPEC.md：目标行为、约束、状态与边界。
- docs/P0_VALIDATION.md：分阶段手动验证与通过/失败判据。
- docs/API_EVIDENCE.md：已核查 API 及未核查假设。
- docs/IMPLEMENTATION_PLAN.md：从 P0 到 M0 的计划。
- AGENTS.md：给后续 Agent 的项目边界与操作要求。

## 立即可做的验证

1. 在 Starfield Creation Kit 建立一个实验用 Start Game Enabled Quest（建议 Editor ID：FCC_P0_QST）。
2. 将两个脚本附加到 Quest 并编译，首先只运行 ProbeOwnedShips；记录 Papyrus 日志。
3. 必须先建立**独立测试存档**。至少拥有三艘不同的玩家飞船，其中一艘作为 Home Ship。
4. 如要执行会影响舰船行为的试验，显式将 MutationsEnabled 设置为 True，并确认测试船已经加载/部署在可见的同一太空场景中；对照 docs/P0_VALIDATION.md。
5. 逐一记录结果。**不得把编译通过写成“功能已验证”，也不得把 PathToReference 视为持续 Follow Package。**

需要本地安装 Creation Kit 和游戏脚本源文件来生成可安装 ESM/PEX。请勿提交 Bethesda 官方游戏资产、第三方 Mod 二进制、破解文件、存档、个人路径或日志。

## 研发优先级

P0：可复现 API 探针和行为观察 → P1：自建飞船安全部署/回收 → P2：旗舰为目标的持续跟随 → P3：多舰队成员与单舰长约束/存档恢复 → M0：可安装、可测试的基础舰队系统。跨星系自主远行、货舱和全套舰队 UI 在后续版本。

## 许可

沿用仓库根目录 LICENSE；仅新写源码及文字，未复制 Bethesda 或第三方 Mod 资产。
