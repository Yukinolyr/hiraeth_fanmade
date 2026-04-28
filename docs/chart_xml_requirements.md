# NOSTALGIA 谱面 XML 识别要求

本文整理当前已通过实机测试验证的谱面 XML 条件。目标是说明“自制谱面必须整理成什么格式，游戏才会识别并进入游玩”。

结论基于以下测试：

- Himawari 谱面导入 `M_T0168_marigoldjazzy`：可进入游玩。
- Fengbei 原始规范化版：预览可播放，但进歌失败。
- Fengbei 修正版：可进入游玩。

## 文件命名

谱面文件名必须匹配歌曲 basename 和难度后缀：

```text
{basename}_00normal.xml
{basename}_01hard.xml
{basename}_02extreme.xml
{basename}_03real.xml
```

例如占用 `M_T0168_marigoldjazzy` 时，Op3 实际加载路径是：

```text
data_Op3/sound/music/M_T0168_marigoldjazzy/M_T0168_marigoldjazzy_02extreme.xml
```

为了兼容当前 LayeredFS/Omni 测试环境，包内通常同时放两套路径：

```text
data_Op3/sound/music/M_T0168_marigoldjazzy/
data_op3/sound/music/m_t0168_marigoldjazzy/
```

## 顶层 XML 结构

根节点必须是：

```xml
<music_score>
```

推荐顶层子节点按官方样本顺序排列：

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

已知风险：

- 源谱面常见的 `time_signature_changes` 不应直接保留在顶层。
- 缺少 `event_data` 的自制 XML 需要补齐，否则不是官方样本形状。

## header

必须包含以下字段：

```xml
<max_scale __type="s32">88</max_scale>
<min_scale __type="s32">0</min_scale>
<file_version __type="s16">1</file_version>
<first_bpm __type="s64">16500000</first_bpm>
<music_finish_time_msec __type="s32">159001</music_finish_time_msec>
```

字段说明：

- `first_bpm` 使用定点整数，实际 BPM = `first_bpm / 100000`。
- `music_finish_time_msec` 是曲目结束时间，单位毫秒。
- `max_scale` / `min_scale` 应覆盖谱面中使用的音高范围。

实机安全范围：

- `scale_piano` 建议限制在 `0..88`。
- 如果源谱面超过 88，应先 clamp 到 88；Fengbei 源谱最大到 107，修正到 88 后成功进入游玩。

## note_data

每个 `note` 推荐使用固定字段顺序：

```xml
<note>
  <index __type="s32">0</index>
  <start_timing_msec __type="s32">0</start_timing_msec>
  <end_timing_msec __type="s32">363</end_timing_msec>
  <gate_time_msec __type="s32">363</gate_time_msec>
  <scale_piano __type="u8">83</scale_piano>
  <min_key_index __type="s32">12</min_key_index>
  <max_key_index __type="s32">13</max_key_index>
  <note_type __type="s32">0</note_type>
  <hand __type="s32">1</hand>
  <key_kind __type="s32">0</key_kind>
  <param1 __type="s32">0</param1>
  <param2 __type="s32">0</param2>
  <param3 __type="s32">0</param3>
  <sub_note_data>
    ...
  </sub_note_data>
</note>
```

硬性/高风险规则：

- `index` 在单个 XML 内应唯一。
- `gate_time_msec` 应等于 `end_timing_msec - start_timing_msec`。
- `scale_piano` 应在 `0..88`。
- 每个 note 必须有 `sub_note_data`，且至少一个 `sub_note`。
- 自制谱导入时建议移除 `measure_index` 等非官方字段。
- `key_kind` 当前规范化工具强制为 `0`；这是保守策略，已通过 Himawari 和 Fengbei 修正版测试。

已观察 note 类型：

```text
0, 2, 4, 8, 10, 12, 64
```

当前自制导入最稳的是普通 note：

```text
note_type=0
note_type=2
```

Glissando 链一般使用 `note_type=4` 或相关类型，并通过 `param1` / `param2` 串联；如果导出工具没有正确生成链，不建议手工猜测。

## sub_note_data

每个 `sub_note` 字段形状：

```xml
<sub_note>
  <start_timing_msec __type="s32">0</start_timing_msec>
  <end_timing_msec __type="s32">363</end_timing_msec>
  <scale_piano __type="u8">83</scale_piano>
  <velocity __type="u8">127</velocity>
  <track_index __type="s32">1</track_index>
</sub_note>
```

这是本次最重要的实机结论：

- `sub_note/track_index` 必须能在 `track_info` 中找到。
- 官方样本的 `track_info` 从 `index=1` 开始。
- `track_index=0` 会导致游戏进歌失败。

Fengbei 失败 log：

```text
W:MusicScoreManager: ... track number:0
W:CMainPlayMusic: ... M_T0168_marigoldjazzy_02extreme.xml
W:ErrorManager: HDD ERROR, ERROR CODE : 5-1501-0000
```

Fengbei 源谱的 `sub_note/track_index` 为 `0/1`。修正为 `1/2` 后可以进入游玩。

推荐规则：

- 如果 `track_info` 是 `1,2,3`，则 `sub_note/track_index` 也必须只使用 `1,2,3`。
- 不要使用 `0`。
- `sub_note/scale_piano` 也应限制在 `0..88`。
- `velocity` 建议使用 `0..127`，官方样本常见 `76..127`。

## event_data

缺少 `event_data` 的自制谱应补齐。当前工具使用以下保守初始化事件：

```xml
<event_data>
  <event>
    <index __type="s32">0</index>
    <start_timing_msec __type="s32">0</start_timing_msec>
    <type __type="s32">0</type>
    <value __type="s64">16500000</value>
  </event>
  ...
</event_data>
```

已确认：

- `type=0` 是 BPM 事件。
- `value` 使用与 `first_bpm` 相同的定点整数。

当前规范化工具会补 `type=0..8` 共 9 个初始化事件。`type=1..8` 的精确语义还未完全确认，但该形状已通过实机测试。

## beat_data

`beat_data` 必须存在，包含按时间递增的 beat：

```xml
<beat>
  <index __type="s32">0</index>
  <start_timing_msec __type="s32">0</start_timing_msec>
</beat>
```

推荐规则：

- `index` 从 0 开始递增。
- `start_timing_msec` 单调递增。
- 最后一个 beat 应覆盖到歌曲接近结束的位置。

## track_info

必须存在，并且 `sub_note/track_index` 必须引用这里定义过的 index：

```xml
<track_info>
  <track>
    <index __type="s32">1</index>
    <name __type="str">key_apiano1</name>
  </track>
  <track>
    <index __type="s32">2</index>
    <name __type="str">key_apiano1</name>
  </track>
</track_info>
```

实机规则：

- `index=0` 不安全；本次会失败。
- `name=key_apiano1` 已验证可用。
- 引用不存在的 track 会导致 `MusicScoreManager` 报错并进歌失败。

## velocity_zone_data

必须存在。字段形状参考官方样本：

```xml
<velocity_zone>
  <index __type="s32">0</index>
  <start_timing_msec __type="s32">0</start_timing_msec>
  <end_timing_msec __type="s32">1000</end_timing_msec>
  <velocity_type __type="s32">0</velocity_type>
</velocity_zone>
```

当前还未完全确认 `velocity_type` 的玩法语义，但保留源谱或官方样本形状均可被解析。

## 导入前检查清单

导入前至少检查：

```bash
python3 scripts/normalize_chart_xml.py input.xml output.xml \
  --clamp-scale-piano \
  --shift-sub-note-track-index 1

python3 validate_song.py work/song_folder

python3 scripts/inspect_xml_structure.py work/song_folder/m_t0168_marigoldjazzy_02extreme.xml
```

`validate_song.py` 应满足：

```text
errors: 0
warnings: 0
```

如果仍有 warning，需要逐项判断。已知高风险 warning：

- `scale_piano is outside 0..88`
- 缺少 `.xsb` / `.xwb`
- 缺少难度 XML
- XML basename 与目录 basename 不匹配

## 常见失败现象

### 预览能播，进歌卡死

通常说明：

- 音频 XWB 路径和 preview XWB 是有效的。
- 问题集中在游玩谱面 XML。

优先检查：

- `sub_note/track_index` 是否引用了不存在的 track，尤其是否存在 `0`。
- `scale_piano` / `sub_note.scale_piano` 是否超过 `88`。
- XML 顶层是否缺 `event_data`。
- note 字段是否缺失或顺序异常。

### log 出现 `HDD ERROR 5-1501-0000`

这不一定是真正的磁盘错误。本次 Fengbei 失败就是谱面内容不合规导致：

```text
MusicScoreManager ... track number:0
CMainPlayMusic ... _02extreme.xml
HDD ERROR, ERROR CODE : 5-1501-0000
```

处理方向应优先看 XML 内容，而不是音频或文件路径。

## 当前规范化策略

`scripts/normalize_chart_xml.py` 当前做以下处理：

- 移除 `time_signature_*` / `time_signature_changes`。
- 补齐 `event_data`。
- 补齐缺失的 `sub_note`。
- 强制 `key_kind=0`。
- 可选：`--clamp-scale-piano`，将 note 和 sub_note 的 `scale_piano` 限制到 `0..88`。
- 可选：`--shift-sub-note-track-index N`，将所有已有 sub_note 的 `track_index` 加上 `N`。

对 Fengbei 这类源谱，当前成功命令是：

```bash
python3 scripts/normalize_chart_xml.py \
  "reference/fengbei/グラウンドスライダー協奏曲第一番「風唄」Real 3.5 Ver.1 (1).xml" \
  work/fengbei_on_marigoldjazzy_clamp88/m_t0168_marigoldjazzy_02extreme.xml \
  --clamp-scale-piano \
  --shift-sub-note-track-index 1
```

