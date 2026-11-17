# AGENTS.md — Fleet Carrier Command

## 目标与边界

本目录是 Starfield 1.16.244 (+ Shattered Space) 的独立舰队 Mod 开发项目，不与仓库其他项目共享运行时。当前阶段为 P0 技术验证源码、M0 设计；**没有可运行的安装包**。用户已经实测 SFSE 在其环境成功启动。

## 不可更改的用户约束

1. 旗舰及所有护航舰必须能选玩家通过 Ship Builder 创建/修改的真实自有飞船。
2. 独立玩家船 1 艘，旗舰 1 艘，护航舰 0..N；舰船身份不得重叠，全部计入自有飞船总数。
3. 护航舰围绕旗舰；不是围绕玩家。旗舰可在玩家离开后独立行动。
4. 每艘舰船最多 1 名同伴舰长，同伴不可重复分配；可不指定舰长；无舰长时尝试真正的飞船 AI；禁止创建隐藏 NPC 冒充 AI。
5. 不写死护航舰数量上限；运行环境/游戏所有权上限依实际情况处理。
6. 可使用 SFSE/C++，但必须先证明兼容 1.16.244。不要以“SFSE 已启动”推断新 DLL 可运行。
7. 保持飞船改名、Ship Builder、出售、停靠和读档数据完整；失败时优先禁用功能并保存诊断信息，不做破坏性修复。

## 当前内容与入口

- Sources/Papyrus/FCC_P0_InventoryProbe.psc：只读枚举，不改写游戏状态。
- Sources/Papyrus/FCC_P0_AIProbe.psc：手动受控测试，仅针对非 Home Ship。其 PathToReference 是**一次性**寻路，不是 Follow AI 实现。
- docs/API_EVIDENCE.md、docs/P0_VALIDATION.md：API 与测试证据；优先读。
- docs/M0_SPEC.md、docs/IMPLEMENTATION_PLAN.md：架构与里程碑。

## 本地构建和测试

当前没有 ESM/PEX，不具备自动构建命令。必须通过安装了对应 Starfield 源脚本的 Creation Kit 编译 .psc、在实验 Quest 上挂载，并在隔离测试存档中执行。日志只能用于本地核查，不要提交个人文件或真实存档。原生 DLL 工程还未建立，不得宣称编译或游戏内测试通过。

如果新增 .esm/.pex/.dll：记录 Creation Kit、SFSE、编译器、依赖版本以及有效的测试证据；把生成物留在发布工作流而不是随意提交至源目录。严禁把修改后的 Bethesda 可执行文件、破解补丁或付费 Creation 资源入库。

## 关键假设与失败条件

- Game.GetPlayerOwnedShips() 返回数组，但不证明所有非 Home Ship 都同时有实体可用。
- SpaceshipReference.EnableAI() 只表示启用 AI，不证明无人驾驶舰船会动。
- SpaceshipReference.PathToReference() 是潜伏单次导航调用，不能直接证明护航舰持续跟随旗舰。
- ReferenceAlias 可动态绑定引用，但长期占用可能影响 Ship Builder 行为，必须测试改名、改装、出售等生命周期操作。
- 任何基于运行时船名或数组顺序的永久身份键都不可靠。

## 协作步骤

1. 先复核最新真实源码、API 定义及版本，再更新证据矩阵。
2. 最小化实验；每次只验证一个行为。对每个测试记录前置条件、输入、现象、异常和回滚。
3. 对失败或未测功能标注 UNVERIFIED，不能将设计当作实现。
4. 推送前核查非本项目内容未被修改；更新 README、Agent 指南、验收结果。
5. 不得误改任何已有游戏目录/存档；用户自己在测试档中进行实验。

## CI/发布

尚无专用 CI；目前只能进行静态人工审查，需后续配套可重现的编译与运行环境。独立构建工程准备好后再引入 CI。

## 变更记录

- 2026-11-17：创建 P0 开发分支，加入验证探针、M0 目标、风险矩阵和 Agent 文档。
