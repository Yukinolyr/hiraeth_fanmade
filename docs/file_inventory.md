# reference/m_c0047_chopin_etude10_4 文件清单

本文记录对 `reference/m_c0047_chopin_etude10_4` 的只读扫描结果。扫描内容包括文件大小、扩展名、magic bytes、SHA256 和用途推测。

复现命令：

```bash
python3 scripts/inspect_folder.py reference/m_c0047_chopin_etude10_4
```

机器可读输出：

```bash
python3 scripts/inspect_folder.py --json reference/m_c0047_chopin_etude10_4
```

## 总览

目录中共有 8 个文件：

- 4 个 `.xml`：四个难度的谱面 XML。
- 2 个 `.xwb`：疑似 XACT Wave Bank 音频容器。
- 2 个 `.xsb`：疑似 XACT Sound Bank 声音索引/事件容器。

未修改任何 `reference` 原始样本。

## 文件明细

| 文件 | 大小 | 扩展名 | magic ascii | magic hex | SHA256 |
|---|---:|---|---|---|---|
| `m_c0047_chopin_etude10_4.xsb` | 268 | `.xsb` | `SDBK..+.$D.a....` | `53 44 42 4b 2e 00 2b 00 24 44 e0 61 0a f3 db 9e` | `f366ba59dbb513785bc5fcac2e7df947ee87690930425158f103bf3d43db6046` |
| `m_c0047_chopin_etude10_4.xwb` | 8152 | `.xwb` | `WBND....,...4...` | `57 42 4e 44 2e 00 00 00 2c 00 00 00 34 00 00 00` | `f4063986d23918a27881a7842afd4192d2470c924d3a6dac5aadf2ef17f87cee` |
| `m_c0047_chopin_etude10_4_00normal.xml` | 1472604 | `.xml` | `...<?xml version` | `ef bb bf 3c 3f 78 6d 6c 20 76 65 72 73 69 6f 6e` | `492814112194f7d0eec95cd16995def6b2dda4132c069f6103ab40f2746320b2` |
| `m_c0047_chopin_etude10_4_01hard.xml` | 1583921 | `.xml` | `...<?xml version` | `ef bb bf 3c 3f 78 6d 6c 20 76 65 72 73 69 6f 6e` | `ecdfd117842e55e9ccc3e580b9edb59071c10deac51542128b9c313927eb6d7d` |
| `m_c0047_chopin_etude10_4_02extreme.xml` | 1891648 | `.xml` | `...<?xml version` | `ef bb bf 3c 3f 78 6d 6c 20 76 65 72 73 69 6f 6e` | `098ef7a4b63d2564d0c915440d67aa3b6333ff649ed094cc0c2387ef99c9c675` |
| `m_c0047_chopin_etude10_4_03real.xml` | 2249861 | `.xml` | `...<?xml version` | `ef bb bf 3c 3f 78 6d 6c 20 76 65 72 73 69 6f 6e` | `eb0eb21f3426ee2a5d70a26146dfe7cfb3873d61b22ab58ef833af972b34bab2` |
| `m_c0047_chopin_etude10_4_pre.xsb` | 297 | `.xsb` | `SDBK..+.........` | `53 44 42 4b 2e 00 2b 00 a2 da f0 88 0a f3 db 9e` | `ed0c64b2cddc295c8e4f763eb2af90ef011d44f9584c15f1d0cf0ad2709ec0ce` |
| `m_c0047_chopin_etude10_4_pre.xwb` | 669372 | `.xwb` | `WBND....,...4...` | `57 42 4e 44 2e 00 00 00 2c 00 00 00 34 00 00 00` | `3af837d58f2eedd5a2202a9217ce7337e305aa962c634ea2aae0e51240298814` |

## XML 文件摘要

| 文件 | root | 顶层节点 | notes | events | beats |
|---|---|---|---:|---:|---:|
| `m_c0047_chopin_etude10_4_00normal.xml` | `music_score` | `header, note_data, event_data, beat_data, track_info, velocity_zone_data` | 1007 | 16 | 336 |
| `m_c0047_chopin_etude10_4_01hard.xml` | `music_score` | `header, note_data, event_data, beat_data, track_info, velocity_zone_data` | 1168 | 16 | 336 |
| `m_c0047_chopin_etude10_4_02extreme.xml` | `music_score` | `header, note_data, event_data, beat_data, track_info, velocity_zone_data` | 1614 | 16 | 336 |
| `m_c0047_chopin_etude10_4_03real.xml` | `music_score` | `header, note_data, event_data, beat_data, track_info, velocity_zone_data` | 2133 | 16 | 336 |

## 用途推测

- `m_c0047_chopin_etude10_4_00normal.xml`、`01hard.xml`、`02extreme.xml`、`03real.xml`：四个难度的谱面数据。结构细节见 `docs/format_notes.md`。
- `m_c0047_chopin_etude10_4.xwb`：疑似主音频 Wave Bank，文件较小，可能只包含被本曲引用的短音频或音频 bank 数据。
- `m_c0047_chopin_etude10_4.xsb`：疑似主 Sound Bank，文件极小，可能是 `.xwb` 的索引、cue 或事件描述。
- `m_c0047_chopin_etude10_4_pre.xwb`：疑似预览音频 Wave Bank，大小明显大于主 `.xwb`。
- `m_c0047_chopin_etude10_4_pre.xsb`：疑似预览 Sound Bank。

## 观察点

- `.xwb` 文件 magic bytes 为 `57 42 4e 44`，ASCII 为 `WBND`。
- `.xsb` 文件 magic bytes 为 `53 44 42 4b`，ASCII 为 `SDBK`。
- XML 文件开头为 `ef bb bf 3c 3f 78 6d 6c ...`，即 UTF-8 BOM 后接 `<?xml version`。
- 四个谱面 XML 的 `event_data` 和 `beat_data` 数量一致，说明 BPM/节拍时间线是曲目级数据。
- 四个谱面 XML 的文件大小随难度上升而增大，和 note 数量增长一致。

## 待确认项

- `.xwb` / `.xsb` 内部结构目前只记录了 magic bytes、大小和 hash，尚未解析 chunk 或 cue 表。
- `_pre` 文件是否一定对应游戏内试听/预览音频，需要更多曲目样本验证。
- 主 `.xwb` 文件较小而 `_pre.xwb` 较大，可能与本曲实际音频引用方式有关，暂不做绕过、提取或替换层面的结论。
