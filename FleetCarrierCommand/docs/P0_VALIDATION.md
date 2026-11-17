# P0 Runtime Validation — Starfield 1.16.244

**状态：全部 UNVERIFIED。** 本文是人工验证操作规范，不是测试报告。

## 前置准备

- Starfield 1.16.244 + Shattered Space；独立测试存档；至少三艘不同的玩家自有飞船（A、B、C），其中 A 是 Home Ship。
- CK 中建立 FCC_P0_QST，附加 P0 探针脚本并编译。没有可用 ESM/PEX 时**不能直接安装**。
- 对只读枚举，先执行 ProbeOwnedShips。记录输出的数量、索引、Home Ship。
- 对 MutationsEnabled = True 的试验，必须在单独测试档中进行、确认 B/C 飞船**实际已经实体化并加载于同一可见太空场景**。API 枚举到一个非 Home Ship，并不表示它已部署为 3D 实体。
- ProbeShipIndex 与 TargetShipIndex 只用于一次性测试；在存档、改装、购买或出售后重新枚举。不要把索引当持久 ID。
- 原生 Papyrus 脚本编译及 CK 表单设置依赖本地游戏安装。禁止在正式存档盲目运行 EnableAI、PathToReference。

## P0-01：只读所有权与身份

执行 ProbeOwnedShips。

通过条件：列出全部自有舰船、正确识别 Home Ship；索引数与游戏飞船菜单一致；修改/重命名飞船后重新枚举不会误认为同名船唯一。失败则停止后续测试。

## P0-02：无人舰长 AI

在只读识别之后，确认非 Home Ship B 实际在太空中加载。设置 MutationsEnabled=True，ProbeShipIndex 指向 B，调用 RunAIProbe。

通过条件：日志 IsAIEnabled=True；B 受控可以进行 AI 导航/姿态控制；不存在自动生成的 NPC 舰长。只返回 IsAIEnabled=True 不构成“能运动”的通过证据。

若 B 不动：记录是未部署、没有 AI Package、驾驶员限制、还是 AI 运动被别的系统禁止；不要私自生成 NPC。

## P0-03：B 舰朝 C 舰单次寻路

要求 B、C 在同一已加载太空场景中，A 为 Home Ship。将 ProbeShipIndex 指向 B、TargetShipIndex 指向 C，手动执行 RunOneShotPathProbe。

观察 B 是否朝 C 运动、潜伏调用结束返回的状态（0 Success/1 Failure/2 Stopped/3 Cleared/4 Timeout）。禁止把此结果直接标注为“持续 Follow”。

## P0-04：持续舰船对舰船 Follow Package

需要独立制作 AI Package，在 CK 里把目标设置为动态旗舰引用 B，再让护航舰 C 执行该 Package；玩家 A 朝反方向离开，观察 C 是否仍追随 B，而非 A。若 C 只在第一次接近后停止，记录是否有 Wait Package 及重新评估行为。

通过条件：离开/返回数次仍稳定跟随 B；保持距离/等待/恢复符合阈值；没有迫使 C 跟随玩家，也没有每秒传送硬纠偏。

**目前尚未编写或编译这一 Package；现有源码仅包含 API 探针。**

## P0-05：0 escort、3 escort、角色唯一性

- 只有 A + B 且没有护航舰，旗舰逻辑不应出错。
- 再添加 C、D、E，测试至少三艘护航舰（玩家真实拥有的不同飞船）。
- 同一个 Actor 或飞船不得被重复分配，无法分配时必须给出错误并保留原状态。

## P0-06：改装/出售与存档幂等

- 登记后依次测试改名、Ship Builder 改装、更换 Home Ship、解除舰长、出售非 Home Ship。
- 保存/退出/重新读取：没有重复实体，没有消失的自有舰船，没有船名重置或错误座位占用。
- 如果失败，需要安全撤回至实验档并记录清晰复现步骤。

## 记录模板

测试 ID / 游戏版本 / CK 版本 / SFSE 版本 / .esm 文件及脚本 SHA / 前置存档信息 / 舰船角色与数量 / 命令 / 日志摘要 / 画面行为 / 是否出现额外 NPC / 返回状态 / PASS-FAIL-UNVERIFIED / 回滚结果。

不得上传含个人本机路径、完整个人存档或受版权保护游戏资产的日志到公开仓库。
