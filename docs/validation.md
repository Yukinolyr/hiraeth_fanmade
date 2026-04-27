# validate_song.py 使用说明

`validate_song.py` 用于只读检查一个歌曲目录是否符合目前观察到的 NOSTALGIA 曲目文件结构。脚本不会修改输入目录。

## 基本用法

```bash
python3 validate_song.py reference/m_c0047_chopin_etude10_4
```

机器可读输出：

```bash
python3 validate_song.py --json reference/m_c0047_chopin_etude10_4
```

严格模式：

```bash
python3 validate_song.py --strict reference/m_c0047_chopin_etude10_4
```

## 检查范围

普通模式下，以下问题会作为错误：

- 输入路径不存在或不是目录。
- 无法推断曲目 basename。
- 缺少 `{basename}.xwb` 或 `{basename}.xsb`。
- `.xwb` magic bytes 不是 `WBND`。
- `.xsb` magic bytes 不是 `SDBK`。
- 没有任何谱面 XML。
- XML 无法解析，或根节点不是 `music_score`。
- 缺少 `header`、`note_data`、`event_data`、`beat_data`、`track_info`、`velocity_zone_data`。
- `header` 缺少已知必要字段。
- `note_data` 为空。
- note 缺少必要字段。
- `gate_time_msec != end_timing_msec - start_timing_msec`。
- note index 重复。
- note 没有 `sub_note`。
- Glissando 链引用不存在或引用到非链式 note。
- `event_data` 中没有 `type=0` BPM 事件。
- beat index 或 beat 时间倒序。

以下问题在普通模式下作为警告：

- 缺少 `{basename}_pre.xwb` 或 `{basename}_pre.xsb`。
- 缺少某些难度 XML。
- `.xwb/.xsb` 内部 ASCII 字符串中没有匹配当前 basename 的 bank name。
- XML 文件名不符合 `{basename}_{difficulty}.xml`。
- 顶层节点顺序和参考结构不同。
- `scale_piano` 超出 `0..88`。
- 出现未知 `note_type`。
- `key_kind` 或 `param3` 非 0。

`--strict` 模式会把缺少 `_pre` 文件和缺少难度 XML 也视为错误。

## 当前 reference 验证结果

`reference/m_c0047_chopin_etude10_4` 在普通模式和 strict 模式下均应通过。
