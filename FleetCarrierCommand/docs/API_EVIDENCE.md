# API Evidence & Open Questions

最后资料核查：2026-11-17。本文仅陈述公开接口存在性，不把 API 存在误写为 Mod 行为已完成。

## 可核查的原生接口

| 接口 | 说明 | 证据 |
| --- | --- | --- |
| Game.GetPlayerOwnedShips() | 返回 SpaceshipReference[]，可只读列举自有船 | https://papyrus.bellcube.dev/starfield/script/game/function/getplayerownedships/ |
| Game.GetPlayerHomeSpaceShip() | 取得玩家当前 Home Ship | https://papyrus.bellcube.dev/starfield/script/game/ |
| SpaceshipReference.EnableAI(bool,bool) | 开关舰船 AI | https://papyrus.bellcube.dev/starfield/script/spaceshipreference/ |
| SpaceshipReference.IsAIEnabled() | 查询舰船 AI 开关 | https://papyrus.bellcube.dev/starfield/script/spaceshipreference/ |
| SpaceshipReference.EvaluatePackage(bool) | 重新评估舰船 AI Package | https://papyrus.bellcube.dev/starfield/script/spaceshipreference/function/evaluatepackage/ |
| SpaceshipReference.PathToReference(ObjectReference,float,float,float,bool) | 一次性潜伏寻路，返回结果码 | https://papyrus.bellcube.dev/starfield/script/spaceshipreference/function/pathtoreference/ |
| ReferenceAlias.ForceRefTo(ObjectReference) | 可把引用填入 Alias；**不代表长期绑定对 Ship Builder 安全** | https://papyrus.bellcube.dev/starfield/script/referencealias/function/forcerefto/ |

## 外部真实代码样本

- 演示玩家自有飞船枚举和监听 Home Ship 变化的脚本：https://github.com/demon-7742/Starfield-Scripts/blob/main/ShipUnlockerScript.psc （仅参考思路，没有复制）。
- 原生飞船 API 可用于 AI/移动，不代表未加载的自有船有可见物理实体。
- 现有 Fleet Commander 功能说明可用于判断“跟随玩家”已经实现，但**不能外推**为“持续跟随任意非玩家旗舰”。

## 必须保留的未验证问题

1. 非 Home Ship 自有飞船在没有独立 spawn/deploy 操作时是否存在于活动太空场景？
2. 无实体驾驶员的玩家自有飞船能否仅靠 EnableAI + Package 自主运动？
3. CK Follow/Escort Package 是否可把另一个动态玩家自有 SpaceshipReference 作为目标？
4. 游戏改装/出售飞船后，是否会重建或替换引用/基础 Form？
5. 是否能在不影响 Ship Builder 的前提下维持跨存档身份映射？
6. 1.16.244 对未来 CommonLibSF/SFSE DLL ABI 与事件钩子的真实兼容状况？

下一步必须以 CK 编译 + 运行时实验回答，不可用接口名推断这些问题已解决。
