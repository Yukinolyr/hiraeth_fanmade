# Nostalgia Fanmade Tools

[English README](README.en.md)

用于研究 NOSTALGIA 本地歌曲、谱面、音频、`music_list.xml` 和 LayeredFS/MonkeyBusiness 导入流程的工具与文档集合。

当前仓库重点已经从“替换现有歌曲测试”推进到“通过 data_mods + MB songlist 新增歌曲测试”。目前已验证的测试包是风呗 `fbfn`。

## 当前状态

已验证：

- 使用 IFS LayeredFS `data_mods` 新增一首测试歌曲。
- 风呗测试曲可在游戏内显示、播放预览、进入游玩并显示封面。
- MonkeyBusiness 的 `modules/nostalgia/music_list.xml` 必须与游戏曲表对齐，并包含新增曲 `music_spec`。
- 游戏必须通过 `spice64.exe -k ifs_hook.dll` 启动，否则不会读取 `data_mods`，新增曲不会出现。
- 谱面 XML 需要满足当前记录的结构约束，尤其是 `scale_piano <= 88`、`sub_note/track_index` 不能为 `0`。

当前测试环境：

```text
NOSTALGIA op.3 PAN
music_list revision: 22621M
music_list release_code: 2024123100
MonkeyBusiness modules/nostalgia
```

## v0.1 测试发布包

当前推荐使用的测试发布包：

```text
work/hiraeth_fanmade_fengbei_v0.1_test.zip
```

解压后推荐直接双击：

```text
INSTALL_CLEAN.bat
```

它会：

- 备份并清空目标 `contents/data_mods`
- 安装风呗 `fbfn`
- 备份并强制替换 `contents/ifs_hook.dll`
- 生成 `contents/start_fengbei_layeredfs.bat`
- 初始化或合并 MonkeyBusiness 的 `modules/nostalgia/music_list.xml`
- 修补 MB `op3_common.py` 的版本号和缺失字段默认值
- 写入回滚状态

安装时会要求输入：

```text
PAN contents path
MonkeyBusiness-main path
```

示例：

```text
E:\Nostalgia\nostalgia\Nostalgia\PAN\contents
E:\Nostalgia\nostalgia\MonkeyBusiness-main
```

安装后不要直接运行普通 `spice64.exe`。请使用安装器生成的：

```text
contents/start_fengbei_layeredfs.bat
```

或者手动启动：

```powershell
.\spice64.exe -k ifs_hook.dll
```

回滚直接双击：

```text
ROLLBACK.bat
```

发布说明：

```text
docs/release_fengbei_v0.1_test.md
```

## 测试歌曲

风呗测试曲：

```text
index: 701
basename: M_T0169_filenameonly
title: Fengbei Filename Test
data_mods package: fbfn
```

注意：`index=701` 只是当前测试环境的可用值，不代表正式分配策略。后续多歌曲安装器需要做 index 冲突检测和 manifest 管理。

## 仓库结构

```text
scripts/             分析、转换、装配工具
docs/                当前研究记录和技术文档
validate_song.py     歌曲文件夹基础验证器
reference/           本地样本目录，默认不提交
work/                本地生成目录；当前强制提交了 v0.1 测试发布 zip
```

## 重要文档

- `docs/chart_xml_requirements.md`：已验证的谱面 XML 格式要求。
- `docs/ifs_layeredfs_notes.md`：LayeredFS、data_mods、新增曲和风呗测试记录。
- `docs/audio_bank_notes.md`：XSB/XWB 音频结构观察。
- `docs/music_list_notes.md`：`music_list.xml` 结构与条目生成记录。
- `docs/workflow.md`：早期替换歌曲、音频、谱面的测试流程。

## 常用脚本

检查文件夹：

```bash
python3 scripts/inspect_folder.py reference/m_t0168_marigoldjazzy
python3 scripts/inspect_banks.py reference/m_t0168_marigoldjazzy
python3 scripts/inspect_xml_structure.py reference/m_t0168_marigoldjazzy/*.xml
```

规范化谱面：

```bash
python3 scripts/normalize_chart_xml.py input.xml output.xml \
  --clamp-scale-piano \
  --shift-sub-note-track-index 1
```

生成 LayeredFS merged 曲表条目：

```bash
python3 scripts/create_music_list_entry.py input_music_list.xml output_music_list.merged.xml \
  --template M_T0168_marigoldjazzy \
  --basename M_T0169_filenameonly \
  --title "Fengbei Filename Test" \
  --artist "Fanmade" \
  --levels 5/9/13/15 \
  --index 701 \
  --merged
```

验证歌曲目录：

```bash
python3 validate_song.py work/custom_song_folder
```

## 安全规则

- 不要直接修改原始游戏目录，请使用测试副本。
- 修改 `contents/data_mods` 前先备份。
- MonkeyBusiness 和游戏内容目录必须来自同一套测试环境，否则 songlist 可能不对齐。
- 不要把个人日志、原始游戏文件或未授权素材提交到仓库。
- 如果新增曲不出现，先确认是否用 `spice64.exe -k ifs_hook.dll` 启动。

## 已知限制

- 当前 v0.1 测试发布包是风呗单曲测试包，不是通用多曲安装器。
- 当前 index、版本号、路径策略针对已验证的 PAN op.3 测试环境。
- XSB 仍主要复用或有限 patch，尚未完整重建未知表、GUID、hash。
- 生成的 XWB 仍以 PCM 工作流为主，ADPCM 生成尚未完成。
- 多歌曲正式安装需要增加 manifest、index 分配、冲突检测和跨版本曲表适配。

## License

MIT License. See `LICENSE`.
