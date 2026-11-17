# Fleet Carrier Command — M0 Specification

状态：设计目标 / 尚未经 Starfield 1.16.244 运行时确认。用户已确认 SFSE 可启动，未确认 FCC DLL。

## 角色及数量不变量

- PERSONAL: 玩家当前驾驶的 Home Ship，始终由玩家控制。
- FLAGSHIP: 一艘与个人船不同的玩家自有飞船；舰队根节点，可不配舰长。
- ESCORT: 零到多艘与 PERSONAL / FLAGSHIP 均不重复的玩家自有飞船。
- 任一自有飞船最多属于一个角色；任何一艘不再归玩家所有、正在改装、出售或丢失引用时，必须安全注销/暂停角色。
- 约束：1 + 1 + escort_count <= owned_ship_count。没有第二艘自有船时不得激活舰队。
- escort_count 不设置静态上限。实际可用上限由玩家拥有船数、动态场景与性能预算决定；不无限生成人工 NPC 舰船。

## 舰长

- per_ship captain = None 或 一个已存在的可分配同伴/船员 Actor。
- 同一个 Actor 不能被赋予多艘舰船；分配/解除应是可逆操作。
- None 意味着纯舰船 AI，不得创建实体驾驶员替代。
- 是否需要实体驾驶员才能令被拥有飞船运动，是 P0 强制验证门槛。
- 同伴在舰船变动/不可访问时需安全解除职位，不把 NPC 遗失在未加载内部。

## 行为

- FLAGSHIP 为所有 ESCORT 的唯一 Follow/Escort 目标；玩家离开不重新指定目标。
- FLAGSHIP 可被设置为驻留（hold position）、集结（rally）、跟随导航点等后续命令。
- ESCORT 在编队距离外回追，在距离内保持位置；不得高频硬传送保持队形。
- P0 仅证明可能性；M0 以同一加载的太空场景为测试边界。跨星系持久移动及离线模拟属于后续阶段。
- 玩家在母舰附近可用原版对接规则对接。不能据此保证离开星系仍有实体。

## 预期状态机（设计）

UNREGISTERED -> RESERVED -> DEPLOYING -> HOLDING/FOLLOWING -> COMBAT -> RECOVERING -> RESERVED

异常路径：
- MISSING_OWNERSHIP -> SUSPENDED，不立即销毁引用。
- EDITING_OR_SELLING -> SUSPENDED，待重建身份映射。
- CELL_UNLOADED -> ABSTRACT，存档状态保留但不强求物理持续模拟。
- LOAD_GAME -> VALIDATING -> REBIND/RECOVER，需幂等。

## 数据标识与持久化策略

保存 Reference 身份 + 明确角色 + 唯一舰长引用 + 状态；Ship Builder 改名、船体改装不得改变舰队选择。不得以船名、OwnedShips 数组索引作为持久主键。若游戏修改飞船后 Reference 身份改变，需要由事件/映射逻辑安全重新关联；绝不静默复制或丢船。

运行时舰队注册表可以采用 SFSE 原生插件；序列化选择必须优先证明安全读档、卸载与升级。不要在 Quest Alias 里永久绑定全部飞船而未经生命周期测试。

## M0 不包含

完整货船内部建造、货舱共享、商业调度、跨星系离线战争、全套可视化终端、舰队远征任务或自动修复游戏上限。
