# m_c0047_chopin_etude10_4 XML 结构摘要

本文记录对 `reference/m_c0047_chopin_etude10_4` 中四个谱面 XML 的只读分析结果，并结合 `otherswork` 中已有资料进行归纳。

## 分析范围

参考文件：

- `m_c0047_chopin_etude10_4_00normal.xml`
- `m_c0047_chopin_etude10_4_01hard.xml`
- `m_c0047_chopin_etude10_4_02extreme.xml`
- `m_c0047_chopin_etude10_4_03real.xml`

参考资料：

- `otherswork/render/NOSTALGIAChartRender/谱面格式解析.md`
- `otherswork/render/NOSTALGIAChartRender/parser.py`
- `otherswork/render/NOSTALGIAChartRender/element.py`
- `otherswork/克劳德通过对比蝎火3个难度的谱面得出的钢琴几谱面格式.docx`

## 顶层结构

四个 XML 的根节点均为 `music_score`，顶层子节点顺序固定：

```xml
<music_score>
  <header>
  <note_data>
  <event_data>
  <beat_data>
  <track_info>
  <velocity_zone_data>
</music_score>
```

文件带 UTF-8 BOM。Python 脚本可直接使用 `xml.etree.ElementTree.parse()` 读取；如果手动按文本读取，建议使用 `utf-8-sig`。

## header

四个难度的 `header` 完全一致：

| 字段 | 值 | 说明 |
|---|---:|---|
| `max_scale` | `80` | 本曲最高钢琴音高编号 |
| `min_scale` | `5` | 本曲最低钢琴音高编号 |
| `file_version` | `1` | 谱面格式版本 |
| `first_bpm` | `16000000` | 初始 BPM，实际值为 `160.0` |
| `music_finish_time_msec` | `126562` | 曲目结束时间，单位毫秒 |

`first_bpm` 使用定点整数编码，实际 BPM = 存储值 / `100000`。

## note_data

每个 `note` 的字段顺序固定：

```xml
<note>
  <index>
  <start_timing_msec>
  <end_timing_msec>
  <gate_time_msec>
  <scale_piano>
  <min_key_index>
  <max_key_index>
  <note_type>
  <hand>
  <key_kind>
  <param1>
  <param2>
  <param3>
  <sub_note_data>
</note>
```

字段观察：

- `index`：单文件内唯一，但不连续。本曲四个难度的 index 范围都是 `1..2206`。
- `start_timing_msec` / `end_timing_msec`：note 判定或显示的开始/结束时间，单位毫秒。
- `gate_time_msec`：等于 `end_timing_msec - start_timing_msec`。本曲四个难度均未发现不一致。
- `scale_piano`：音高编号。本曲 note 层范围为 `5..80` 或 `17..80`，取决于难度。
- `min_key_index` / `max_key_index`：可视键盘区域。本曲范围为 `1..28`。
- `note_type`：本曲只出现 `0`、`2`、`4`。
- `hand`：`0` 为右手，`1` 为左手，`2` 在参考资料中解释为低难度辅助/隐藏或不指定手。渲染器中会过滤 `hand=2`。
- `key_kind`：本曲全部为 `0`。
- `param1` / `param2`：在 `note_type=4` 的 Glissando 链中表示前后节点 index；非链式 note 中通常为 `0`。
- `param3`：本曲全部为 `0`。
- `sub_note_data`：每个 note 均存在，且至少包含一个 `sub_note`。

## 四难度 note 统计

| 难度 | note 总数 | `hand!=2` | `note_type` 分布 | `hand` 分布 |
|---|---:|---:|---|---|
| `00normal` | 1007 | 499 | `0:963`, `2:9`, `4:35` | `0:283`, `1:216`, `2:508` |
| `01hard` | 1168 | 1119 | `0:1023`, `2:56`, `4:89` | `0:550`, `1:569`, `2:49` |
| `02extreme` | 1614 | 1613 | `0:1465`, `2:134`, `4:15` | `0:898`, `1:715`, `2:1` |
| `03real` | 2133 | 2133 | `0:1993`, `2:140` | `0:1114`, `1:1019` |

本曲未出现 `note_type=8`、`10`、`12`、`64`。这些类型在 `otherswork` 资料中有记录，但不应从本曲样本强行推断其行为。

## Glissando 链

本曲使用 `note_type=4` 表示 Glissando。链式结构通过 `param1` / `param2` 连接：

- 链头：`param1 = -1`，`param2 = 下一节点 index`
- 链中：`param1 = 上一节点 index`，`param2 = 下一节点 index`
- 链尾：`param1 = 上一节点 index`，`param2 = -1`

统计：

| 难度 | Glissando 节点 | 链头 | 链尾 |
|---|---:|---:|---:|
| `00normal` | 35 | 7 | 7 |
| `01hard` | 89 | 23 | 23 |
| `02extreme` | 15 | 3 | 3 |
| `03real` | 0 | 0 | 0 |

## sub_note_data

每个 `sub_note` 字段固定：

```xml
<sub_note>
  <start_timing_msec>
  <end_timing_msec>
  <scale_piano>
  <velocity>
  <track_index>
</sub_note>
```

观察结果：

- 四个难度的 sub_note 音频层总量和分布一致。
- `track_index=1` 出现 `1178` 次。
- `track_index=2` 出现 `1028` 次。
- `track_index=3` 在 `track_info` 中存在，但本曲 sub_note 未实际引用。
- `sub_note.scale_piano` 范围为 `5..80`。
- `velocity` 范围为 `76..127`。

这表明本曲四个难度共享同一套或高度一致的音频触发层，难度差异主要体现在 note 如何组合、显示和指定左右手。

## event_data

四个难度的 `event_data` 完全一致，共 16 个事件。

初始化事件：

| index | time | type | value |
|---:|---:|---:|---:|
| 0 | 0 | 0 | 16000000 |
| 1 | 0 | 1 | 122 |
| 2 | 0 | 2 | 9 |
| 3 | 473 | 3 | 30 |
| 4 | 473 | 4 | 50 |
| 5 | 473 | 5 | 15 |
| 6 | 949 | 6 | 127 |
| 7 | 949 | 7 | 0 |
| 8 | 949 | 8 | 65 |

结尾 BPM 下降事件：

| index | time | value | BPM |
|---:|---:|---:|---:|
| 9 | 121688 | 15700024 | 157.00024 |
| 10 | 121879 | 15400015 | 154.00015 |
| 11 | 122073 | 15100113 | 151.00113 |
| 12 | 122272 | 14800087 | 148.00087 |
| 13 | 122475 | 14500003 | 145.00003 |
| 14 | 122682 | 14200074 | 142.00074 |
| 15 | 122893 | 13900021 | 139.00021 |

`type=0` 可确认是 BPM 事件。`type=1..8` 暂按未知初始化/演出/节拍相关参数记录，不提供未验证结论。

## beat_data

四个难度的 `beat_data` 完全一致：

- beat 数量：`336`
- index 范围：`0..335`
- 时间范围：`0..126130ms`
- 主体 beat 间隔大多为 `375ms`，对应 `160 BPM`
- 结尾出现 `379`、`393`、`410`、`427`、`431`、`432ms` 等间隔，与 `event_data` 中结尾 BPM 下降吻合

## track_info

四个难度的 `track_info` 完全一致：

| index | name |
|---:|---|
| 1 | `key_apiano1` |
| 2 | `key_apiano1` |
| 3 | `key_apiano1` |

目前本曲 sub_note 只引用 `track_index=1` 和 `track_index=2`。

## velocity_zone_data

四个难度均有 16 个 `velocity_zone`，字段为：

```xml
<velocity_zone>
  <index>
  <start_timing_msec>
  <end_timing_msec>
  <velocity_type>
</velocity_zone>
```

`velocity_type` 只出现 `0` 和 `1`。不同难度的 zone 数量一致，但部分边界时间有几十毫秒差异。当前只记录为力度区域或演奏区域，不将其作为已确认玩法语义。

## 待确认项

- `event_data` 中 `type=1..8` 的精确语义。
- `velocity_zone_data.velocity_type` 的实际判定含义。
- `hand=2` 在不同上下文中是隐藏音符、双手均可，还是低难度辅助提示，需要结合实机或更多谱面验证。
- `track_index=3` 在本曲未使用，但是否为备用轨或其他音频层，需要更多样本确认。
- 本曲未覆盖 `note_type=8/10/12/64`，这些类型应继续参考其他曲目样本。

## 复现脚本

可使用以下脚本重新生成结构摘要：

```bash
python3 scripts/inspect_xml_structure.py reference/m_c0047_chopin_etude10_4
```

如需机器可读输出：

```bash
python3 scripts/inspect_xml_structure.py --json reference/m_c0047_chopin_etude10_4
```
