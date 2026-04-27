# Nostalgia Fanmade Tools

用于研究音乐游戏本地歌曲、谱面与音频文件结构的 Python 工具和文档集合，重点是可复现、仅在本地进行的自制谱面实验。

本仓库只包含工具和研究文档。不包含游戏原始文件、受版权保护的音乐、生成的替换包或样本素材。

## 用前必看
当前仅验证了群内'夜的向日葵.zip'内的内容经过封装可以成功替换到歌曲文件夹marigold中。
进行替换前一定要备份游戏文件 射射。

## v1.0

当前已经验证的流程：

- 将简单 XWB 音频包解码为 WAV。
- 将 PCM WAV 封装为简单的单 entry XWB 音频包。
- 将导入的 `music_score` XML 规范化为目前观察到的游戏谱面结构。
- 在测试前验证一个歌曲工作目录的基础合法性。
- 使用现有歌曲文件夹作为测试壳，只替换指定的音频或谱面文件。

已知限制：

- XSB 中的 GUID、hash 和未知表尚未重建；当前流程主要复用现有 XSB 文件，或只修改可见 bank name。
- 本项目不绕过 DRM、签名、联网校验、反作弊、授权或完整性系统。

## 安全规则

- 不要直接修改原始游戏文件。


## 环境要求

- 推荐 Python 3.11 或更新版本。
- `ffmpeg` 不是必须项，但建议安装，便于在封装 XWB 前重采样 WAV。

## 实验步骤

当前推荐策略是保留原曲入口、标题、`.xsb` 和 `music_list.xml`，只替换：

```text
m_t0168_marigoldjazzy.xwb
m_t0168_marigoldjazzy_pre.xwb
m_t0168_marigoldjazzy_02extreme.xml
```

也就是说，游戏里仍会显示原本的 marigoldjazzy 信息，但进入 Expert/Extreme 难度时会加载你的音频和谱面。这样变量最少，适合第一次测试。

## 重要注意事项

- 不要直接修改原始游戏目录。
- 请先复制一份游戏作为测试副本，只在测试副本里替换文件。
- 不要把自己的音频、游戏文件、生成包提交到 GitHub。
- `reference/` 只放本地样本，`work/` 只放生成结果，这两个目录里的实际内容默认不会上传。
- 如果游戏加载失败，先恢复备份文件，不要继续覆盖原始文件。

## 需要准备的东西

你需要准备：

```text
1. Python 3
2. 本项目文件夹
3. 找到原版 m_t0168_marigoldjazzy 文件夹
4. 你自己的 WAV 音频
5. 你自己的 XML 谱面
```

推荐把文件放成这样：

```text
nostalgia_fanmade/
  reference/
    m_t0168_marigoldjazzy/
      m_t0168_marigoldjazzy.xsb
      m_t0168_marigoldjazzy.xwb
      m_t0168_marigoldjazzy_pre.xsb
      m_t0168_marigoldjazzy_pre.xwb
      m_t0168_marigoldjazzy_00normal.xml
      m_t0168_marigoldjazzy_01hard.xml
      m_t0168_marigoldjazzy_02extreme.xml
      m_t0168_marigoldjazzy_03real.xml
    import/
      my_song.wav
      my_chart.xml
```

其中：

- `reference/m_t0168_marigoldjazzy/` 是你从测试用游戏副本中复制出来的原曲文件夹。
- `reference/import/my_song.wav` 是你自己的音频。
- `reference/import/my_chart.xml` 是你自己的谱面。

## 第 1 步：打开终端

在 WSL 终端中进入项目目录：

```bash
cd /home/yukino/code/nostalgia_fanmade
```

如果你的项目在别的位置，请把上面的路径换成自己的项目路径。

## 第 2 步：创建安全工作副本

不要直接改 `reference/`。先把 marigoldjazzy 复制到 `work/`：

```bash
python3 scripts/create_work_copy.py reference/m_t0168_marigoldjazzy work/my_marigoldjazzy_import
```

成功后会出现：

```text
work/my_marigoldjazzy_import/
```

之后所有生成文件都放在这个目录或其他 `work/` 子目录里。

## 第 3 步：把 WAV 降采样为临时可用格式

当前工具生成的是 PCM XWB。为了避免文件太大导致游戏加载失败，第一次测试建议先使用 16000 Hz。

如果你的 WAV 是普通 PCM WAV，可以执行：

```bash
python3 scripts/resample_wav.py reference/import/my_song.wav work/my_marigoldjazzy_audio/my_song_16k.wav --sample-rate 16000
```

如果这一步失败，通常说明你的 WAV 不是普通 PCM WAV。可以先用 `ffmpeg` 转换：

```bash
ffmpeg -y -i reference/import/my_song.wav -ar 16000 -ac 2 -sample_fmt s16 work/my_marigoldjazzy_audio/my_song_16k.wav
```

## 第 4 步：制作 15 秒预览音频

先从降采样后的 WAV 截取前 15.158 秒：

```bash
python3 scripts/trim_wav.py work/my_marigoldjazzy_audio/my_song_16k.wav work/my_marigoldjazzy_audio/my_song_preview_16k.wav --duration 15.158
```

`15.158` 是原 marigoldjazzy 预览音频的长度。第一次测试建议先沿用这个长度。

## 第 5 步：把 WAV 封装成 XWB

生成主音频 XWB：

```bash
python3 scripts/wav_to_xwb.py work/my_marigoldjazzy_audio/my_song_16k.wav work/my_marigoldjazzy_import/m_t0168_marigoldjazzy.xwb --bank-name M_T0168_marigoldjazzy
```

生成预览音频 XWB：

```bash
python3 scripts/wav_to_xwb.py work/my_marigoldjazzy_audio/my_song_preview_16k.wav work/my_marigoldjazzy_import/m_t0168_marigoldjazzy_pre.xwb --bank-name M_T0168_marigoldjazzy_pre
```

注意：

- 主音频 bank name 必须使用 `M_T0168_marigoldjazzy`。
- 预览音频 bank name 必须使用 `M_T0168_marigoldjazzy_pre`。
- 这里不修改 `.xsb`，继续复用原版 `.xsb`。

## 第 6 步：把你的谱面转成 Expert/Extreme 谱面

把自己的 XML 谱面规范化后写入 Expert/Extreme 文件：

```bash
python3 scripts/normalize_chart_xml.py reference/import/my_chart.xml work/my_marigoldjazzy_import/m_t0168_marigoldjazzy_02extreme.xml
```

这个脚本会做几件事：

- 补齐 `event_data`
- 修正 `first_bpm` 的数值格式
- 移除当前游戏样本中没有的部分字段
- 补齐缺失的 `sub_note`
- 将 `key_kind` 统一为 `0`

如果这一步显示 `FAIL`，说明你的 XML 和当前已知格式差异太大，需要先分析谱面结构，不能直接导入。

## 第 7 步：验证生成结果

执行：

```bash
python3 validate_song.py work/my_marigoldjazzy_import
```

如果看到：

```text
PASS
errors: 0
```

说明基础结构可以进入测试。

有 warning 不一定代表不能运行。比如 `scale_piano > 88` 曾经出现过，但已验证不阻止游戏加载。真正需要优先处理的是 `errors`。

也可以检查音频包：

```bash
python3 scripts/inspect_banks.py work/my_marigoldjazzy_import
```

确认能看到类似：

```text
bank_name: M_T0168_marigoldjazzy
bank_name: M_T0168_marigoldjazzy_pre
```

## 第 8 步：复制到游戏测试副本

在游戏测试副本中找到：

```text
contents/data_op3/sound/music/m_t0168_marigoldjazzy/
```

先备份这 3 个原文件：

```text
m_t0168_marigoldjazzy.xwb
m_t0168_marigoldjazzy_pre.xwb
m_t0168_marigoldjazzy_02extreme.xml
```

然后从这里复制新文件：

```text
work/my_marigoldjazzy_import/m_t0168_marigoldjazzy.xwb
work/my_marigoldjazzy_import/m_t0168_marigoldjazzy_pre.xwb
work/my_marigoldjazzy_import/m_t0168_marigoldjazzy_02extreme.xml
```

覆盖到游戏测试副本的：

```text
contents/data_op3/sound/music/m_t0168_marigoldjazzy/
```

不要覆盖原始游戏目录，只覆盖测试副本。

## 第 9 步：进游戏测试

进入游戏后：

```text
1. 找到原本的 marigoldjazzy
2. 进入歌曲预览画面，确认预览音频是否播放
3. 选择 Expert/Extreme 难度
4. 点击游玩
```

如果能进入游玩，说明这次导入成功。

如果预览能播但点击游玩无响应，常见原因是：

- 主 XWB 太大
- WAV 采样率太高导致 PCM XWB 体积过大
- 谱面 XML 有字段不兼容
- 谱面时间轴异常

第一次测试建议保持 16000 Hz PCM。如果之后要提升音质，应优先研究 ADPCM XWB，而不是直接使用 44100 Hz 长音频 PCM。

## 回滚方法

如果游戏无法进入或表现异常，把之前备份的 3 个原文件复制回去：

```text
m_t0168_marigoldjazzy.xwb
m_t0168_marigoldjazzy_pre.xwb
m_t0168_marigoldjazzy_02extreme.xml
```

如果 `work/my_marigoldjazzy_import` 被改坏，可以删除这个工作目录后重新创建：

```bash
python3 scripts/create_work_copy.py reference/m_t0168_marigoldjazzy work/my_marigoldjazzy_import_2
```

不要通过修改或覆盖 `reference/m_t0168_marigoldjazzy` 来回滚。

## 当前版本能保证什么

当前版本能帮助你完成：

- 把普通 PCM WAV 转成游戏可测试的 XWB。
- 把外部 XML 谱面转换为更接近官方样本的结构。
- 用 marigoldjazzy 作为测试壳替换音频和 Expert/Extreme 谱面。
- 在测试前检查文件是否明显缺失或结构错误。

当前版本还不能保证：

- 任意 XML 谱面都能直接导入。
- 任意 WAV 都能保持高音质导入。
- 新增歌曲、改标题、改分类、改 `music_list.xml` 后一定能被游戏识别。
- 生成的 XWB 与官方 ADPCM XWB 完全一致。

所以第一次实验请只替换 marigoldjazzy 的音频和 Expert/Extreme 谱面。确认成功后，再逐步测试改标题、新增曲目、提高音质等功能。