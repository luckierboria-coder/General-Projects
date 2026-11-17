# CK P0-01 安装、编译与只读枚举测试（Starfield 1.16.244）

状态：**操作指南，尚未有编译/游戏运行结果**。适用于已经能运行 Creation Kit 的开发机。

## 1. 编译器与官方脚本源

在当前可运行的 Creation Kit / Starfield 安装中确认：

- `Tools/Papyrus Compiler/PapyrusCompiler.exe`
- `Tools/ContentResources.zip`
- `Data/Starfield.esm`（以 CK 实际读取到的位置为准）

从 `ContentResources.zip` 取出 `Scripts` 下的脚本源到游戏/CK 能读取的 `Data/Scripts/Source`，保证不会多套一层 `Scripts`。注意压缩包内容可能在 `Base` 等子目录。

参考： https://pca.kiyozz.com/download 和 https://pca.kiyozz.com/docs/troubleshooting/common-errors

不要覆盖已有不同版本的官方脚本源；先记录来源版本并保留备份。

## 2. 第一阶段只编译不修改舰船的脚本

只处理：`Sources/Papyrus/FCC_P0_InventoryProbe.psc`

将 .psc 复制到适合本机的用户脚本源目录（通常为 `Data/Scripts/Source/User`），使用 CK 的 Papyrus Script Manager 或官方编译器尝试编译。应生成 `FCC_P0_InventoryProbe.pex`。

如遇到 `Starfield_Papyrus_Flags.flg`、找不到 `Game` 或 `SpaceshipReference` 等错误，先检查原版脚本源、flag 文件与导入目录；不要直接修改游戏可执行程序。

**提示：该 .psc 目前未在目标 CK 编译验证，编译出错属正常工程反馈。保留完整错误文本。**

## 3. 建立独立测试 Quest

- CK → File → Data：加载 `Starfield.esm`；切勿把它设为要保存的活动修改文件。
- 在 `Character → Quest`（具体 CK UI 名称依版本可能不同）新建空 Quest，Editor ID 推荐 `FCC_P0_QST`。
- 将 `FCC_P0_InventoryProbe` 附加到 Quest 的 Scripts 列表。
- 保存为单独的测试插件（例如 `FCC_P0_Test.esp` 或 CK 允许的开发格式），不要修改原版主文件。
- 建立专门的测试存档。先用一两艘玩家拥有的船进行 P0-01，后续 P0-03 才需要三艘。

如果 CK 中无法添加脚本，先检查 .pex 是否成功生成、源脚本名称是否与 Scriptname 完全一致、游戏与 CK 的脚本目录是否一致。

## 4. 游戏内只读调用

加载实验插件，使用控制台先确认 Quest 存在且可运行：

```text
startquest FCC_P0_QST
sqv FCC_P0_QST
cqf FCC_P0_QST ProbeOwnedShips
```

`cqf` = CallQuestFunction；不同引擎状态下解析重名函数可能需要前缀。若提示找不到函数，再尝试：

```text
cqf FCC_P0_QST "FCC_P0_InventoryProbe.ProbeOwnedShips"
```

不保证所有版本都接受 Editor ID：若无法解析，使用 CK 给出的该 Quest Form ID 重试。

预期 Papyrus trace 前缀：`[FCC P0]`。记录数量、Home Ship 引用与逐一枚举结果，检查与游戏的飞船列表是否一致。仅看到 Quest 存在还不算脚本已执行成功。

控制台用法资料：https://taosecurity.github.io/starfield-console-commands/

## 5. 暂时不要做的事

- 不编译或执行 `FCC_P0_AIProbe.psc` 的 MutationsEnabled 测试；
- 不对非 Home Ship 盲目执行 `EnableAI`、`PathToReference`；
- 不创建 NPC 舰长，不复制或直接生成船体；
- 不在正式游玩存档上使用实验插件。

## 6. 提供测试结果的最小材料

1. CK 所在目录中 `PapyrusCompiler.exe` 和 `ContentResources.zip` 是否存在（只答有/无；不需要上传 Bethesda 文件）；
2. `FCC_P0_InventoryProbe.psc` 编译成功/失败；
3. 若失败，复制编译器完整错误文本；若成功，复制 `[FCC P0]` 行；
4. 不提供用户名、路径、完整存档、游戏 ESM 或破解文件。

只有 P0-01 通过后，才按 `docs/P0_VALIDATION.md` 执行会改写 AI 的后续测试。
