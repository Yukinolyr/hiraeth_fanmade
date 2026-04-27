# 工作区流程

本项目的 `reference/` 目录只作为只读样本。所有自制谱面、替换实验和文件重命名都应在 `work/` 下进行。

## 创建工作副本

使用脚本把参考曲复制到工作目录：

```bash
python3 scripts/create_work_copy.py reference/m_c0047_chopin_etude10_4 work/custom_song_001
```

脚本限制：

- 源目录和目标目录都必须在项目目录内。
- 目标目录必须位于 `work/` 下。
- 如果目标目录已存在，脚本会拒绝覆盖。

## 验证工作副本

创建后先运行：

```bash
python3 validate_song.py work/custom_song_001
```

如果验证通过，说明工作副本在结构上仍与参考样本一致。后续实验应只修改 `work/custom_song_001`，不修改 `reference/m_c0047_chopin_etude10_4`。

当前状态：

- 已创建 `work/custom_song_001`。
- `python3 validate_song.py work/custom_song_001` 结果为 `PASS`。
- `errors: 0`，`warnings: 0`。
- 文件 SHA256 与 `docs/file_inventory.md` 中的 reference 清单一致。

## 最小改名实验

为验证工具链是否能识别自定义曲目 ID，已创建一个只改文件名、不改 XML 内容的实验副本：

```bash
python3 scripts/create_renamed_song_copy.py work/custom_song_001 work/custom_song_001_renamed m_f0001_custom_test
python3 validate_song.py work/custom_song_001_renamed
```

结果：

- 已创建 `work/custom_song_001_renamed`。
- 文件 basename 从 `m_c0047_chopin_etude10_4` 改为 `m_f0001_custom_test`。
- `python3 validate_song.py work/custom_song_001_renamed` 结果为 `PASS`，但有内部 bank 名 warning。
- `errors: 0`，`warnings: 4`。
- 文件 SHA256 与原副本一致，说明本次实验只改了文件名，没有改文件内容。

注意：这个实验只证明当前项目内的验证脚本能识别改名后的文件集合，不证明游戏本体一定能加载改名曲目。`.xsb/.xwb` 内部是否包含 cue 名称或其他引用仍需后续只读分析确认。

后续只读分析已确认：`.xsb/.xwb` 内部仍保留 `M_C0047_chopin_etude10_4` / `M_C0047_chopin_etude10_4_pre`，没有同步为 `m_f0001_custom_test`。因此文件名改名不足以代表完整自制曲目重命名。

## Closeup 整合实验

已创建完整工作目录：

```text
work/custom_song_closeup_test
```

说明：这一版使用 `m_f0002_closeup_test`。后续根据“前缀可能对应游戏内歌曲分类标签”的假设，已生成一套 `m_l0002_closeup_test` 版本用于实际替换测试；优先测试 `m_l` 版本。

组成：

- 谱面 XML：从 `reference/m_t0168_marigoldjazzy` 复制并重命名为 `m_f0002_closeup_test_*`。
- 主音频：由 `reference/closeup.wav` 封装为 `m_f0002_closeup_test.xwb`。
- 主 XSB：由主音频模板改 bank name 为 `M_F0002_closeup_test`，cue 保持 `_backtrack`。
- 预览音频：由 `reference/closeup.wav` 封装为 `m_f0002_closeup_test_pre.xwb`。
- 预览 XSB：由预览模板改 bank name 为 `M_F0002_closeup_test_pre`，cue 保持 `_preview`。
- 曲目列表：包含 `M_F0002_closeup_test` 条目的 `music_list.xml` 副本。

复现命令：

```bash
python3 scripts/wav_to_xwb.py reference/closeup.wav work/wav_pack_test/m_f0002_closeup_test.xwb --bank-name M_F0002_closeup_test
python3 scripts/patch_bank_names.py reference/m_t0168_marigoldjazzy/m_t0168_marigoldjazzy.xsb work/wav_pack_test/m_f0002_closeup_test.xsb M_F0002_closeup_test
python3 scripts/wav_to_xwb.py reference/closeup.wav work/wav_pack_test/m_f0002_closeup_test_pre.xwb --bank-name M_F0002_closeup_test_pre
python3 scripts/patch_bank_names.py reference/m_t0168_marigoldjazzy/m_t0168_marigoldjazzy_pre.xsb work/wav_pack_test/m_f0002_closeup_test_pre.xsb M_F0002_closeup_test_pre
python3 scripts/assemble_custom_song.py work/custom_song_closeup_test \
  --basename m_f0002_closeup_test \
  --template-dir reference/m_t0168_marigoldjazzy \
  --main-xwb work/wav_pack_test/m_f0002_closeup_test.xwb \
  --main-xsb work/wav_pack_test/m_f0002_closeup_test.xsb \
  --preview-xwb work/wav_pack_test/m_f0002_closeup_test_pre.xwb \
  --preview-xsb work/wav_pack_test/m_f0002_closeup_test_pre.xsb \
  --music-list work/music_list_test/music_list.xml
```

验证：

```bash
python3 validate_song.py work/custom_song_closeup_test
python3 scripts/inspect_banks.py work/custom_song_closeup_test
python3 scripts/inspect_music_list.py work/custom_song_closeup_test/music_list.xml M_F0002_closeup_test
python3 scripts/xwb_to_wav.py work/custom_song_closeup_test -o work/custom_song_closeup_test_decoded
```

结果：

- `validate_song.py`：`PASS`，`errors: 0`。
- 有 1 个 warning：`music_list.xml` 不是谱面 XML，被歌曲验证器跳过。
- 主/预览 `.xwb` 均可反向解码为普通 PCM WAV。
- 主 bank name：`M_F0002_closeup_test`。
- 预览 bank name：`M_F0002_closeup_test_pre`。
- 主 cue：`_backtrack`。
- 预览 cue：`_preview`。
- `music_list.xml` 中存在 `M_F0002_closeup_test`，index 为 `595`。

限制：

- 当前预览音频直接使用完整 `closeup.wav`，不是截短预览片段。
- 谱面来自 `m_t0168_marigoldjazzy`，只用于结构整合，不与 `closeup.wav` 音乐匹配。
- `.xsb` 的 GUID/hash 字段仍来自模板，没有重建。
- 该目录只证明项目内结构一致和工具链闭环，不代表可以直接替换游戏文件。

## Closeup m_l 分类前缀实验

假设：`m_c`、`m_t`、`m_l` 这类前缀可能与游戏内歌曲分类/搜索标签有关。`m_f` 不是已确认的官方分类，因此下一轮测试改用 `m_l`，同时保持编号和曲名主体不变，方便和上一版对比。

已创建完整工作目录：

```text
work/custom_song_closeup_test_l
```

组成：

- 谱面 XML：从 `reference/m_t0168_marigoldjazzy` 复制并重命名为 `m_l0002_closeup_test_*`。
- 主音频：由 `reference/closeup.wav` 封装为 `m_l0002_closeup_test.xwb`。
- 主 XSB：由主音频模板改 bank name 为 `M_L0002_closeup_test`，cue 保持 `_backtrack`。
- 预览音频：由 `reference/closeup.wav` 封装为 `m_l0002_closeup_test_pre.xwb`。
- 预览 XSB：由预览模板改 bank name 为 `M_L0002_closeup_test_pre`，cue 保持 `_preview`。
- 曲目列表：包含 `M_L0002_closeup_test` 条目的 `music_list.xml` 副本。

复现命令：

```bash
python3 scripts/wav_to_xwb.py reference/closeup.wav work/wav_pack_test_l/m_l0002_closeup_test.xwb --bank-name M_L0002_closeup_test
python3 scripts/patch_bank_names.py reference/m_t0168_marigoldjazzy/m_t0168_marigoldjazzy.xsb work/wav_pack_test_l/m_l0002_closeup_test.xsb M_L0002_closeup_test
python3 scripts/wav_to_xwb.py reference/closeup.wav work/wav_pack_test_l/m_l0002_closeup_test_pre.xwb --bank-name M_L0002_closeup_test_pre
python3 scripts/patch_bank_names.py reference/m_t0168_marigoldjazzy/m_t0168_marigoldjazzy_pre.xsb work/wav_pack_test_l/m_l0002_closeup_test_pre.xsb M_L0002_closeup_test_pre
python3 scripts/create_music_list_entry.py reference/music_list.xml work/music_list_test_l/music_list.xml --template M_T0168_marigoldjazzy --basename M_L0002_closeup_test --title CloseupTest --artist Fanmade --levels 3/6/9/12
python3 scripts/assemble_custom_song.py work/custom_song_closeup_test_l \
  --basename m_l0002_closeup_test \
  --template-dir reference/m_t0168_marigoldjazzy \
  --main-xwb work/wav_pack_test_l/m_l0002_closeup_test.xwb \
  --main-xsb work/wav_pack_test_l/m_l0002_closeup_test.xsb \
  --preview-xwb work/wav_pack_test_l/m_l0002_closeup_test_pre.xwb \
  --preview-xsb work/wav_pack_test_l/m_l0002_closeup_test_pre.xsb \
  --music-list work/music_list_test_l/music_list.xml
```

验证：

```bash
python3 validate_song.py work/custom_song_closeup_test_l
python3 scripts/inspect_banks.py work/custom_song_closeup_test_l
python3 scripts/inspect_music_list.py work/custom_song_closeup_test_l/music_list.xml M_L0002_closeup_test
```

结果：

- `validate_song.py`：`PASS`，`errors: 0`。
- 有 1 个 warning：`music_list.xml` 不是谱面 XML，被歌曲验证器跳过。
- 主 bank name：`M_L0002_closeup_test`。
- 预览 bank name：`M_L0002_closeup_test_pre`。
- 主 cue：`_backtrack`。
- 预览 cue：`_preview`。
- `music_list.xml` 中存在 `M_L0002_closeup_test`，index 为 `595`。

## Marigold Jazzy 音频占位替换测试

为了先测试生成的 `.xwb` 是否被游戏接受，已准备一个更小变量的测试包：保留 `m_t0168_marigoldjazzy` 原曲身份，只替换两个 `.xwb` 音频文件。

测试包：

```text
work/install_package_marigoldjazzy_audio_only
```

包含：

```text
contents/data_op3/sound/music/m_t0168_marigoldjazzy/m_t0168_marigoldjazzy.xwb
contents/data_op3/sound/music/m_t0168_marigoldjazzy/m_t0168_marigoldjazzy_pre.xwb
```

不包含：

- `.xsb`
- 谱面 XML
- `music_list.xml`

生成命令：

```bash
python3 scripts/wav_to_xwb.py reference/closeup.wav work/audio_replace_marigoldjazzy_closeup_test/m_t0168_marigoldjazzy.xwb --bank-name M_T0168_marigoldjazzy
python3 scripts/wav_to_xwb.py reference/closeup.wav work/audio_replace_marigoldjazzy_closeup_test/m_t0168_marigoldjazzy_pre.xwb --bank-name M_T0168_marigoldjazzy_pre
```

验证：

```bash
python3 scripts/inspect_banks.py work/audio_replace_marigoldjazzy_closeup_test
python3 scripts/xwb_to_wav.py work/audio_replace_marigoldjazzy_closeup_test -o work/audio_replace_marigoldjazzy_closeup_test_decoded
```

结果：

- 主 XWB bank name：`M_T0168_marigoldjazzy`。
- 预览 XWB bank name：`M_T0168_marigoldjazzy_pre`。
- 两个 XWB 均为 `PCM`、2 channels、44100 Hz。
- 两个 XWB 均可反向解码为普通 WAV。

限制：

- 原始 `m_t0168_marigoldjazzy.xwb` 是 ADPCM，本测试包是 PCM，用于确认游戏是否接受 PCM XWB。
- 预览 XWB 暂时使用完整 `closeup.wav`，不是短预览片段。
- 这个测试必须只安装到游戏测试副本，不要覆盖原始游戏目录。

### 测试反馈与下一步

用户反馈：进入歌曲预览画面时成功播放音频，但点击游玩后游戏无响应。

第一次读取 `reference/log.txt` 时，日志没有出现 `m_t0168_marigoldjazzy`、`.xwb`、`.xsb` 相关的明确加载错误；日志尾部只显示窗口关闭和音频系统停止。

后续用户补充了进入歌曲瞬间的日志，关键行如下：

```text
I:SoundCtrl: Load wave=data_Op3/sound/music/M_T0168_marigoldjazzy/M_T0168_marigoldjazzy.xwb
I:SoundCtrl: Load sound = data_Op3/sound/music/M_T0168_marigoldjazzy/M_T0168_marigoldjazzy.xsb
I:SoundCtrl: END
W:CTHLoad::LOAD: ... [ 3,0,-1 ]
W:Class_Wavebank::Load: pbWaveBank ... /...:0/data_Op3/sound/music/M_T0168_marigoldjazzy/M_T0168_marigoldjazzy.xwb
W:Class_Soundbank::Load: ... : data_Op3/sound/music/M_T0168_marigoldjazzy/M_T0168_marigoldjazzy.xsb
```

日志中的日文部分显示为乱码，但按常见 mojibake 可读为：

- `メモリ確保に失敗しました`：内存分配失败。
- `サウンド使用メモリ`：sound 使用内存。
- `キューの作成に失敗しました`：cue 创建失败。

因此现象更像是主 `.xwb` 加载阶段分配 sound memory 失败，随后 `.xsb` cue 创建失败。它不像是谱面 XML 长度不一致直接导致的错误。

已确认的时长差异：

| 项目 | 格式 | 时长 |
|---|---|---:|
| 原 `m_t0168_marigoldjazzy.xwb` | ADPCM | 111.412s |
| 原 `m_t0168_marigoldjazzy_pre.xwb` | PCM | 15.158s |
| 谱面 `music_finish_time_msec` | XML | 111.157s |
| `reference/closeup.wav` | PCM WAV | 307.925s |

结论：时长不一致是合理嫌疑，但不是唯一嫌疑。因为原主音频是 ADPCM，而替换主音频是 PCM；预览原本也是 PCM，所以“预览能播”只说明 PCM 预览 XWB 可用，不能证明主游玩 XWB 的 PCM 形式一定可用。

已准备第二个测试包，先排除时长/文件大小变量：

```text
work/install_package_marigoldjazzy_duration_matched
```

这个包仍只替换两个 `.xwb`，但将 closeup 裁剪为：

- 主音频：111.412s，对齐原主 XWB 解码时长。
- 预览音频：15.158s，对齐原预览 XWB 解码时长。

生成命令：

```bash
python3 scripts/trim_wav.py reference/closeup.wav work/audio_replace_marigoldjazzy_duration_matched/closeup_main_111412.wav --duration 111.412
python3 scripts/trim_wav.py reference/closeup.wav work/audio_replace_marigoldjazzy_duration_matched/closeup_pre_15158.wav --duration 15.158
python3 scripts/wav_to_xwb.py work/audio_replace_marigoldjazzy_duration_matched/closeup_main_111412.wav work/audio_replace_marigoldjazzy_duration_matched/m_t0168_marigoldjazzy.xwb --bank-name M_T0168_marigoldjazzy
python3 scripts/wav_to_xwb.py work/audio_replace_marigoldjazzy_duration_matched/closeup_pre_15158.wav work/audio_replace_marigoldjazzy_duration_matched/m_t0168_marigoldjazzy_pre.xwb --bank-name M_T0168_marigoldjazzy_pre
```

验证结果：

- 主 XWB：`PCM`、2 channels、44100 Hz、111.412s、约 19.65MB。
- 预览 XWB：`PCM`、2 channels、44100 Hz、15.158s、约 2.67MB。
- 两个 XWB 均可反向解码为普通 WAV。

判断方式：

- 如果裁剪版能进入游玩，上一版问题大概率来自 307.925s 主音频或 54.3MB 文件大小。
- 如果裁剪版仍然无响应，下一步应研究生成 ADPCM XWB，因为原主音频是 ADPCM。

测试反馈：`work/install_package_marigoldjazzy_duration_matched` 可以进入游戏。

结论：

- 主 `.xwb` 使用 PCM 并非必然失败；至少在 `111.412s`、约 19.65MB 的测试条件下可进入游玩。
- 上一版完整 `closeup.wav` 替换失败，主要原因更可能是 `307.925s` 主音频过长或 54.3MB PCM XWB 过大，导致 sound memory 分配失败。
- 在只替换现有曲目的策略下，音频时长应优先对齐目标曲目的 `music_finish_time_msec` / 原主 XWB 时长。
- 若要使用完整 307.925s 音频，需要同步制作对应长度的谱面 XML，并确认游戏能接受更长/更大的主 XWB；更稳的方向是进一步研究 ADPCM XWB 生成，以降低文件大小和内存压力。

### Marigold Jazzy 时长阶梯测试包

为区分“主音频必须接近谱面结束时间”和“只是完整 closeup 过长/过大”，已生成三个只改变主 XWB 时长的测试包。预览 XWB 均使用已验证的 15.158s 版本。

| 测试包 | 主 XWB 时长 | 主 XWB 大小 | 相对原主音频 |
|---|---:|---:|---:|
| `work/install_package_marigoldjazzy_minus5s` | 106.412s | 18.77MB | -5.000s |
| `work/install_package_marigoldjazzy_duration_matched` | 111.412s | 19.65MB | 0.000s |
| `work/install_package_marigoldjazzy_plus5s` | 116.412s | 20.54MB | +5.000s |
| `work/install_package_marigoldjazzy_plus10s` | 121.412s | 21.42MB | +10.000s |

生成命令：

```bash
python3 scripts/trim_wav.py reference/closeup.wav work/audio_replace_marigoldjazzy_plus_tests/minus5s/closeup_main_106412.wav --duration 106.412
python3 scripts/trim_wav.py reference/closeup.wav work/audio_replace_marigoldjazzy_plus_tests/plus5s/closeup_main_116412.wav --duration 116.412
python3 scripts/trim_wav.py reference/closeup.wav work/audio_replace_marigoldjazzy_plus_tests/plus10s/closeup_main_121412.wav --duration 121.412
python3 scripts/wav_to_xwb.py work/audio_replace_marigoldjazzy_plus_tests/minus5s/closeup_main_106412.wav work/audio_replace_marigoldjazzy_plus_tests/minus5s/m_t0168_marigoldjazzy.xwb --bank-name M_T0168_marigoldjazzy
python3 scripts/wav_to_xwb.py work/audio_replace_marigoldjazzy_plus_tests/plus5s/closeup_main_116412.wav work/audio_replace_marigoldjazzy_plus_tests/plus5s/m_t0168_marigoldjazzy.xwb --bank-name M_T0168_marigoldjazzy
python3 scripts/wav_to_xwb.py work/audio_replace_marigoldjazzy_plus_tests/plus10s/closeup_main_121412.wav work/audio_replace_marigoldjazzy_plus_tests/plus10s/m_t0168_marigoldjazzy.xwb --bank-name M_T0168_marigoldjazzy
```

验证结果：

- 三个主 XWB 均为 `PCM`、2 channels、44100 Hz。
- bank name 均为 `M_T0168_marigoldjazzy`。
- 三个主 XWB 均可用 `scripts/xwb_to_wav.py` 反向解码。

建议测试顺序：

1. `minus5s`
2. `plus5s`
3. `plus10s`

如果 `minus5s` 和 `duration_matched` 成功、`plus5s` 失败，则更支持“结束时间后不能有额外主音频”的假设。如果 `plus5s/+10s` 也成功，则完整 307.925s 失败更可能来自更大的长度/内存阈值。

### 完整时长但容量匹配测试包

为了进一步区分“完整歌曲时长导致失败”和“44100 Hz PCM XWB 体积太大导致失败”，已生成完整 `closeup.wav` 时长但接近已通过包容量的测试包：

```text
work/install_package_marigoldjazzy_full_16k_size_matched
```

主音频处理方式：

- 输入：`reference/closeup.wav`
- 处理：使用 `ffmpeg` 重采样为 16000 Hz、stereo、16-bit PCM。
- 时长：307.925s，保持完整 closeup。
- 主 XWB 大小：约 19.71MB，接近已通过的 `duration_matched` 主 XWB 19.65MB。
- bank name：`M_T0168_marigoldjazzy`。

生成命令：

```bash
ffmpeg -y -hide_banner -loglevel error -i reference/closeup.wav -ar 16000 -ac 2 -sample_fmt s16 work/audio_replace_marigoldjazzy_full_16k_size_matched/closeup_full_16k.wav
python3 scripts/wav_to_xwb.py work/audio_replace_marigoldjazzy_full_16k_size_matched/closeup_full_16k.wav work/audio_replace_marigoldjazzy_full_16k_size_matched/m_t0168_marigoldjazzy.xwb --bank-name M_T0168_marigoldjazzy
```

验证结果：

- 主 XWB：`PCM`、2 channels、16000 Hz、307.925s、约 19.71MB。
- `scripts/inspect_banks.py` 可解析。
- `scripts/xwb_to_wav.py` 可反向解码。

判断方式：

- 如果该包能进入游玩，说明完整 `307.925s` 时长本身不是主要问题；之前失败更可能是 44100 Hz PCM 主 XWB 约 54.3MB，超过 sound memory 或 wavebank 加载预算。
- 如果该包仍失败，说明长时长、16000 Hz 采样率、或其他 timeline/load 假设仍可能影响进入游玩；之后应优先做 ADPCM XWB 测试。

测试反馈：`work/install_package_marigoldjazzy_full_16k_size_matched` 可以进入游戏。

结论：

- 完整 `307.925s` 时长本身可以被游戏接受。
- 之前完整 `44100 Hz` PCM 版本失败，更可能是主 XWB 约 54.3MB 导致 sound memory / wavebank 加载失败。
- 当前可运行的完整版本使用 `16000 Hz` PCM，主 XWB 约 19.71MB；这说明降低容量可以绕开进入游玩时的加载失败。
- 后续若要保留更好的音质，应优先研究 ADPCM XWB 生成，而不是继续依赖低采样率 PCM。

## Himawari 谱面导入测试

用户提供：

```text
reference/himawari/Yoru_no_himawari.xml
reference/himawari/夜の向日葵.wav
reference/himawari/register.json
reference/himawari/夜の向日葵.png
```

测试策略：继续使用已验证的 `m_t0168_marigoldjazzy` 作为歌曲入口，不修改 `music_list.xml`、title、artist 或 `.xsb`。只替换主/预览 XWB 和 Expert/Extreme 槽 XML：

```text
m_t0168_marigoldjazzy_02extreme.xml
```

原因：

- `m_t0168_marigoldjazzy` 的曲目入口和 `.xsb` 已验证可用。
- 不引入新增曲目、解锁、分类或 title 显示变量。
- 只在 Expert/Extreme 难度槽验证 himawari 谱面是否能加载。

Himawari 原始 XML 观察：

- root：`music_score`
- `music_finish_time_msec`：164756
- notes：883
- 缺少官方样本中的 `event_data`
- 多出 `time_signature_changes`
- note 中有额外 `measure_index`
- 多数 note 原本没有 `sub_note`

已新增脚本：

```bash
python3 scripts/normalize_chart_xml.py reference/himawari/Yoru_no_himawari.xml work/himawari_on_marigoldjazzy_extreme/m_t0168_marigoldjazzy_02extreme.xml
```

规范化处理：

- 修正 `first_bpm`：`82` -> `8200000`
- 补 `event_data`，包含 `type=0` BPM 事件和 `type=1..8` 初始化事件
- 移除 `time_signature_changes`
- 移除 note 的 `measure_index`
- 统一 note 字段顺序
- 对没有 `sub_note` 的 note 生成默认 `sub_note`
- 将 `key_kind` 强制归零；`otherswork` 中记录该字段在已分析官方谱面中恒为 `0`，用途未知

音频处理：为了先测试谱面格式，仍使用临时可用的低容量 PCM 方案：

```bash
ffmpeg -y -hide_banner -loglevel error -i reference/himawari/夜の向日葵.wav -ar 16000 -ac 2 -sample_fmt s16 work/himawari_on_marigoldjazzy_extreme_audio/himawari_full_16k.wav
ffmpeg -y -hide_banner -loglevel error -i reference/himawari/夜の向日葵.wav -t 15.158 -ar 16000 -ac 2 -sample_fmt s16 work/himawari_on_marigoldjazzy_extreme_audio/himawari_pre_16k.wav
python3 scripts/wav_to_xwb.py work/himawari_on_marigoldjazzy_extreme_audio/himawari_full_16k.wav work/himawari_on_marigoldjazzy_extreme_audio/m_t0168_marigoldjazzy.xwb --bank-name M_T0168_marigoldjazzy
python3 scripts/wav_to_xwb.py work/himawari_on_marigoldjazzy_extreme_audio/himawari_pre_16k.wav work/himawari_on_marigoldjazzy_extreme_audio/m_t0168_marigoldjazzy_pre.xwb --bank-name M_T0168_marigoldjazzy_pre
```

生成的测试包：

```text
work/install_package_marigoldjazzy_himawari_extreme
```

包内只包含：

```text
contents/data_op3/sound/music/m_t0168_marigoldjazzy/m_t0168_marigoldjazzy.xwb
contents/data_op3/sound/music/m_t0168_marigoldjazzy/m_t0168_marigoldjazzy_pre.xwb
contents/data_op3/sound/music/m_t0168_marigoldjazzy/m_t0168_marigoldjazzy_02extreme.xml
```

验证结果：

- `python3 validate_song.py work/himawari_on_marigoldjazzy_extreme_full`：`PASS`，`errors: 0`。
- 主 XWB：`PCM`、2 channels、16000 Hz、166.814s、约 10.68MB。
- 预览 XWB：`PCM`、2 channels、16000 Hz、15.158s、约 0.97MB。
- XWB 可反向解码。
- 当前 warnings 剩余 50 个，全部来自 `scale_piano > 88`。
- `scale_piano > 88` 分布：`90` 出现 23 次，`92` 出现 12 次，`95` 出现 9 次，`97` 出现 6 次。
- 因默认补齐 sub_note 会沿用主 note 的 `scale_piano`，当前 sub_note 中也有 50 个 `scale_piano > 88`。
- 如果游戏加载失败或显示/判定异常，下一步优先生成一版将 `scale_piano` clamp 到 `88` 的 A/B 测试包。

测试反馈：`work/install_package_marigoldjazzy_himawari_extreme` 可以运行，Himawari 音频和 Expert/Extreme 谱面均成功替换进游戏。

结论：

- 使用已有 `m_t0168_marigoldjazzy` 曲目入口作为测试壳可行。
- 保留 `.xsb`、`music_list.xml`、title/artist，仅替换主/预览 XWB 和 `02extreme.xml` 可行。
- `normalize_chart_xml.py` 当前的基础规范化策略可被游戏接受：
  - 补 `event_data`
  - 修正 `first_bpm`
  - 移除 `time_signature_changes`
  - 移除 `measure_index`
  - 补缺失 `sub_note`
  - `key_kind=0`
- 当前版本存在 `scale_piano > 88`，但不会阻止游戏加载和游玩；是否影响显示/发声效果仍需实际观察。
- 当前 16000 Hz PCM XWB 是临时可用音频方案，后续优化音质时应研究 ADPCM XWB。

## 回滚方法

如果工作副本被改坏，保留 `reference/` 不动，重新创建一个新的工作目录，例如：

```bash
python3 scripts/create_work_copy.py reference/m_c0047_chopin_etude10_4 work/custom_song_002
```

不要通过覆盖 `reference/` 来回滚。
