# XSB/XWB 只读分析笔记

本文记录 `reference/m_c0047_chopin_etude10_4` 中 `.xsb` / `.xwb` 文件的只读结构观察。不涉及提取、绕过、解密或修改原始游戏文件。

复现命令：

```bash
python3 scripts/inspect_banks.py reference/m_c0047_chopin_etude10_4
```

也可检查工作副本：

```bash
python3 scripts/inspect_banks.py work/custom_song_001_renamed
```

## 文件角色

| 文件 | 类型 | 观察结论 |
|---|---|---|
| `m_c0047_chopin_etude10_4.xwb` | Wave Bank | `WBND`，包含 1 个 ADPCM entry，内部 bank name 为 `M_C0047_chopin_etude10_4` |
| `m_c0047_chopin_etude10_4.xsb` | Sound Bank | `SDBK`，包含可见字符串 `M_C0047_chopin_etude10_4` 和 cue 名 `_backtrack` |
| `m_c0047_chopin_etude10_4_pre.xwb` | Preview Wave Bank | `WBND`，包含 1 个 ADPCM entry，内部 bank name 为 `M_C0047_chopin_etude10_4_pre` |
| `m_c0047_chopin_etude10_4_pre.xsb` | Preview Sound Bank | `SDBK`，包含可见字符串 `M_C0047_chopin_etude10_4_pre` 和 cue 名 `_preview` |

## XWB 结构

两个 `.xwb` 文件都符合 XACT Wave Bank 风格段表：

- signature：`WBND`
- version：`46`
- header_version：`44`
- `bank_data` 段从 `0x34` 开始，长度 `96`
- `entry_metadata` 段从 `0x94` 开始，长度 `24`
- `wave_data` 段从 `0xAC` 开始
- `wave_data` 段一直延伸到文件末尾
- `entry_count = 1`
- `entry_metadata_element_size = 24`
- `entry_name_element_size = 64`
- `alignment = 4`
- `compact_format = 0`

主 `.xwb`：

| 字段 | 值 |
|---|---:|
| 文件大小 | `8152` |
| bank name | `M_C0047_chopin_etude10_4` |
| wave_data offset | `172` / `0xAC` |
| wave_data length | `7980` |
| entry format | `ADPCM` |
| format raw | `0x1815b64a` |
| channels guess | `2` |
| sample_rate guess | `44466` |
| block_align guess | `48` |
| play region | `(0, 7980)` |
| loop region | `(0, 7296)` |

预览 `.xwb`：

| 字段 | 值 |
|---|---:|
| 文件大小 | `669372` |
| bank name | `M_C0047_chopin_etude10_4_pre` |
| wave_data offset | `172` / `0xAC` |
| wave_data length | `669200` |
| entry format | `ADPCM` |
| format raw | `0x1815892a` |
| channels guess | `2` |
| sample_rate guess | `44105` |
| block_align guess | `48` |
| play region | `(0, 669200)` |
| loop region | `(82560, 529280)` |

说明：`sample_rate guess` 来自 XACT mini wave format 位域的当前脚本解析，仍需用更多样本或外部元数据验证。当前可稳妥确认的是格式标签为 ADPCM、双声道倾向、wave data 起点和长度。

## XSB 结构

两个 `.xsb` 文件都符合 Sound Bank 风格：

- signature：`SDBK`
- version_u16：`46`
- header_version_u16：`43`
- 头部存在 16 字节类似 GUID/hash 的数据。
- 可见 ASCII 字符串包含 bank 名和 cue 名。

主 `.xsb` 字符串：

| offset | text |
|---:|---|
| `0x004a` | `M_C0047_chopin_etude10_4` |
| `0x008a` | `M_C0047_chopin_etude10_4` |
| `0x0101` | `_backtrack` |

预览 `.xsb` 字符串：

| offset | text |
|---:|---|
| `0x004a` | `M_C0047_chopin_etude10_4_pre` |
| `0x008a` | `M_C0047_chopin_etude10_4_pre` |
| `0x0120` | `_preview` |

## 与改名实验的关系

`work/custom_song_001_renamed` 只改了文件名：

- 文件名 basename：`m_f0001_custom_test`
- `.xwb/.xsb` 内部字符串：仍为 `M_C0047_chopin_etude10_4` 和 `M_C0047_chopin_etude10_4_pre`

因此，文件名改名实验只能证明项目内验证脚本能按文件名识别目录结构，不能证明游戏会把它当作新曲目加载。`.xsb/.xwb` 内部 bank name/cue name 很可能也是加载链路的一部分。

## 验证器更新

`validate_song.py` 已加入内部 bank 名检查：

- 如果 `.xwb/.xsb` 中没有与当前 basename 匹配的 ASCII 字符串，会给出 warning。
- `reference/m_c0047_chopin_etude10_4` 应无 warning。
- `work/custom_song_001_renamed` 会出现 warning，因为文件名和内部 bank name 不一致。

## 待确认项

- `.xsb` 中除字符串外的表结构、cue 表和偏移表仍未完全解析。
- `.xwb` 的 mini wave format 位域解析需要更多样本校验。
- 是否可以安全生成新的 `.xsb/.xwb`，需要先在 `work/` 内做副本实验，不应修改 `reference` 或原始游戏目录。

## XWB 转 WAV

已新增脚本：

```bash
python3 scripts/xwb_to_wav.py reference/m_c0047_chopin_etude10_4 -o work/decoded_audio
```

脚本行为：

- 只读取 `.xwb`。
- 解析 `WBND` 段表和第 0 个 entry。
- 支持当前样本中出现的 XACT ADPCM 和 PCM entry。
- 将音频转换成标准 RIFF/WAVE PCM。
- 输出 16-bit stereo PCM WAV。
- 不修改输入文件。

转换结果：

| 输入 | 输出 | 声道 | 采样率 | 帧数 | 时长 | WAV 大小 |
|---|---|---:|---:|---:|---:|---:|
| `m_c0047_chopin_etude10_4.xwb` | `work/decoded_audio/m_c0047_chopin_etude10_4.wav` | 2 | 44466 | 7296 | 0.164s | 29228 |
| `m_c0047_chopin_etude10_4_pre.xwb` | `work/decoded_audio/m_c0047_chopin_etude10_4_pre.wav` | 2 | 44105 | 611840 | 13.872s | 2447404 |

用 `file` 检查，输出为：

```text
RIFF (little-endian) data, WAVE audio, Microsoft PCM, 16 bit, stereo
```

采样率说明：

- 当前脚本从 XACT mini wave format 位域解析出的采样率分别为 `44466` 和 `44105`。
- 这两个值接近但不完全等于常见的 `44100`，因此 mini wave format 位域仍需更多样本校验。
- 脚本支持强制采样率：

```bash
python3 scripts/xwb_to_wav.py reference/m_c0047_chopin_etude10_4 -o work/decoded_audio_44100 --sample-rate 44100
```

强制 `44100Hz` 后的输出仍是标准 PCM WAV：

| 输入 | 输出 | 声道 | 采样率 | 帧数 | 时长 | WAV 大小 |
|---|---|---:|---:|---:|---:|---:|
| `m_c0047_chopin_etude10_4.xwb` | `work/decoded_audio_44100/m_c0047_chopin_etude10_4.wav` | 2 | 44100 | 7296 | 0.165s | 29228 |
| `m_c0047_chopin_etude10_4_pre.xwb` | `work/decoded_audio_44100/m_c0047_chopin_etude10_4_pre.wav` | 2 | 44100 | 611840 | 13.874s | 2447404 |

如果后续遇到无法转换的 `.xwb`，常见原因会是：

- 文件不是 `WBND`。
- `.xwb` 内有多个 entry，但脚本只转换指定 entry。
- entry 不是 PCM/ADPCM，而是 XMA/WMA 等其他格式。
- entry metadata 或 play region 与当前样本结构不同。
- ADPCM block alignment 无法从当前规则推导，或数据长度不能按 block 对齐。

## m_t0168_marigoldjazzy 转换记录

新增参考曲 `reference/m_t0168_marigoldjazzy` 已完成转换：

```bash
python3 scripts/xwb_to_wav.py reference/m_t0168_marigoldjazzy -o work/decoded_audio_marigoldjazzy
```

转换结果：

| 输入 | XWB entry 格式 | 输出 | 声道 | 采样率 | 帧数 | 时长 | WAV 大小 |
|---|---|---|---:|---:|---:|---:|---:|
| `m_t0168_marigoldjazzy.xwb` | ADPCM | `work/decoded_audio_marigoldjazzy/m_t0168_marigoldjazzy.wav` | 2 | 44100 | 4913280 | 111.412s | 19653164 |
| `m_t0168_marigoldjazzy_pre.xwb` | PCM | `work/decoded_audio_marigoldjazzy/m_t0168_marigoldjazzy_pre.wav` | 2 | 44100 | 668463 | 15.158s | 2673896 |

用 `file` 检查，两个输出均为：

```text
RIFF (little-endian) data, WAVE audio, Microsoft PCM, 16 bit, stereo 44100 Hz
```

这首歌与 `m_c0047_chopin_etude10_4` 的差异：

- 主 `.xwb` 是 ADPCM，可由脚本解码。
- `_pre.xwb` 是 PCM，脚本已扩展支持直接封装为普通 WAV。
- 采样率位域解析结果正好是 `44100`，无需 `--sample-rate` 覆盖。

## WAV 封装为 XWB

已新增脚本：

```bash
python3 scripts/wav_to_xwb.py reference/closeup.wav work/wav_pack_test/closeup_test.xwb --bank-name M_F0002_closeup_test
```

脚本行为：

- 只读取输入 WAV。
- 仅支持未压缩 PCM WAV。
- 当前支持 8-bit / 16-bit PCM，已测试 16-bit stereo 44100 Hz。
- 生成单 entry PCM XWB。
- 输出写入 `work/`，不修改 `reference`。

本次输入：

| 文件 | 格式 | 声道 | 位深 | 采样率 | 帧数 | 时长 | 大小 |
|---|---|---:|---:|---:|---:|---:|---:|
| `reference/closeup.wav` | PCM WAV | 2 | 16-bit | 44100 | 13579513 | 307.925s | 54318130 |

封装输出：

| 文件 | XWB 格式 | bank name | 大小 |
|---|---|---|---:|
| `work/wav_pack_test/closeup_test.xwb` | PCM | `M_F0002_closeup_test` | 54318224 |

反向验证：

```bash
python3 scripts/xwb_to_wav.py work/wav_pack_test/closeup_test.xwb -o work/wav_pack_test/roundtrip_closeup.wav
```

结果：

| 文件 | 格式 | 声道 | 位深 | 采样率 | 帧数 | 时长 | PCM SHA256 |
|---|---|---:|---:|---:|---:|---:|---|
| `reference/closeup.wav` | PCM WAV | 2 | 16-bit | 44100 | 13579513 | 307.925s | `6511425d05ca365cbdc03aab5b70d79df67f5421347f27145e82426209348cee` |
| `work/wav_pack_test/roundtrip_closeup.wav` | PCM WAV | 2 | 16-bit | 44100 | 13579513 | 307.925s | `6511425d05ca365cbdc03aab5b70d79df67f5421347f27145e82426209348cee` |

结论：

- `WAV -> XWB -> WAV` 闭环成功。
- 原始 WAV 和反向解出的 WAV 的 PCM 数据完全一致。
- 当前封装结果是 PCM XWB，不是 ADPCM XWB。
- 这证明项目内可以生成结构可解析、可反向还原的 XWB；但还不等同于完整游戏替换可用，因为 `.xsb` cue、bank name、歌曲元数据和游戏加载链路仍需单独验证。

## XSB bank name 同步实验

已新增脚本：

```bash
python3 scripts/patch_bank_names.py <input.xsb|input.xwb> <output.xsb|output.xwb> <BANK_NAME>
```

用途：

- 修改简单 `.xsb` 中可见的 `M_*` bank name 字符串。
- 修改 `.xwb` 的 `bank_data.bank_name`。
- 只在输出文件写入，不修改输入文件。

当前 XSB 观察：

- 主音频 `.xsb` 有两个 64 字节 bank name 槽：
  - `0x004a`
  - `0x008a`
- 主音频 cue 名在 `0x0101`，值为 `_backtrack`。
- 预览 `.xsb` 的 cue 名是 `_preview`，当前尚未做生成实验。

本次用主音频模板生成了与 `closeup.wav` 对应的 XSB/XWB：

```bash
python3 scripts/wav_to_xwb.py reference/closeup.wav work/wav_pack_test/m_f0002_closeup_test.xwb --bank-name M_F0002_closeup_test
python3 scripts/patch_bank_names.py reference/m_t0168_marigoldjazzy/m_t0168_marigoldjazzy.xsb work/wav_pack_test/m_f0002_closeup_test.xsb M_F0002_closeup_test
```

检查结果：

| 文件 | 内部 bank name | cue |
|---|---|---|
| `work/wav_pack_test/m_f0002_closeup_test.xwb` | `M_F0002_closeup_test` | 不适用 |
| `work/wav_pack_test/m_f0002_closeup_test.xsb` | `M_F0002_closeup_test`，出现于 `0x004a` 和 `0x008a` | `_backtrack` |

`m_f0002_closeup_test.xwb` 仍可反向转换：

```bash
python3 scripts/xwb_to_wav.py work/wav_pack_test/m_f0002_closeup_test.xwb -o work/wav_pack_test/m_f0002_closeup_test_roundtrip.wav
```

结果：

- format：PCM
- channels：2
- sample rate：44100
- frames：13579513
- duration：307.925s

限制：

- `patch_bank_names.py` 只修改可见 ASCII bank name，不重建 `.xsb` 内部未知表。
- `.xsb` 头部的 GUID/hash 字段没有重新生成。
- cue 名 `_backtrack` 没有改变。
- 当前只验证了项目内结构和反向音频转换，不代表游戏一定接受该 XSB/XWB 组合。

## m_l bank name 实验

为配合歌曲分类前缀假设，已生成 `m_l0002_closeup_test` 版本：

```bash
python3 scripts/wav_to_xwb.py reference/closeup.wav work/wav_pack_test_l/m_l0002_closeup_test.xwb --bank-name M_L0002_closeup_test
python3 scripts/patch_bank_names.py reference/m_t0168_marigoldjazzy/m_t0168_marigoldjazzy.xsb work/wav_pack_test_l/m_l0002_closeup_test.xsb M_L0002_closeup_test
python3 scripts/wav_to_xwb.py reference/closeup.wav work/wav_pack_test_l/m_l0002_closeup_test_pre.xwb --bank-name M_L0002_closeup_test_pre
python3 scripts/patch_bank_names.py reference/m_t0168_marigoldjazzy/m_t0168_marigoldjazzy_pre.xsb work/wav_pack_test_l/m_l0002_closeup_test_pre.xsb M_L0002_closeup_test_pre
```

检查结果：

| 文件 | 内部 bank name | cue |
|---|---|---|
| `work/wav_pack_test_l/m_l0002_closeup_test.xwb` | `M_L0002_closeup_test` | 不适用 |
| `work/wav_pack_test_l/m_l0002_closeup_test.xsb` | `M_L0002_closeup_test`，出现于 `0x004a` 和 `0x008a` | `_backtrack` |
| `work/wav_pack_test_l/m_l0002_closeup_test_pre.xwb` | `M_L0002_closeup_test_pre` | 不适用 |
| `work/wav_pack_test_l/m_l0002_closeup_test_pre.xsb` | `M_L0002_closeup_test_pre`，出现于 `0x004a` 和 `0x008a` | `_preview` |

## m_c0064_hungary06 样本补充

新增参考曲 `reference/m_c0064_hungary06` 验证了前面的 bank/cue 规律：

主音频：

- `.xsb` signature：`SDBK`
- `.xwb` signature：`WBND`
- `.xsb` 内部 bank name：`M_C0064_hungary06`，出现在 `0x004a` 和 `0x008a`
- `.xsb` cue：`_backtrack`
- `.xwb` bank name：`M_C0064_hungary06`
- `.xwb` entry：ADPCM
- `.xwb` wave data offset：`0xAC`

预览音频：

- `.xsb` 内部 bank name：`M_C0064_hungary06_pre`，出现在 `0x004a` 和 `0x008a`
- `.xsb` cue：`_preview`
- `.xwb` bank name：`M_C0064_hungary06_pre`
- `.xwb` entry：ADPCM
- `.xwb` wave data offset：`0xAC`

这个样本说明：

- 主音频 cue `_backtrack` 和预览 cue `_preview` 在三个样本中保持一致。
- XSB 中两个 64 字节 bank name 槽位置稳定。
- XWB 的段表结构稳定。
- `_pre.xwb` 不一定是 PCM；`m_c0064_hungary06_pre.xwb` 是 ADPCM，而 `m_t0168_marigoldjazzy_pre.xwb` 是 PCM。
