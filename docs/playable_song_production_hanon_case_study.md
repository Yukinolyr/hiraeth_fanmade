# 可游玩自制曲产出流程：Hanon 四 BPM 成功案例

本文记录 `E:\hiraeth` 中已经跑通的 Hanon 四版本制作流程。目标是作为以后制作新曲时的端到端参考：从音频、谱面、曲目列表、封面、文字纹理到游戏替换与验证。

当前案例不是“完全通用自动化发布工具”，而是一个已经验证可进入选曲、可预览、可进歌、有声音、四难度可玩的工作基线。

## 最终产物

四首曲目复用 `index=142-145`：

| index | basename | BPM | 大封面/小封面编号 | 等级字段 |
|---:|---|---:|---|---|
| 142 | `M_C0035_hanon_120` | 120 | `0142` | `7 / 9 / 12 / 15` |
| 143 | `M_C0036_hanon_108` | 108 | `0143` | `7 / 9 / 12 / 14` |
| 144 | `M_C0037_hanon_90` | 90 | `0144` | `7 / 9 / 12 / 13` |
| 145 | `M_C0038_hanon_78` | 78 | `0145` | `7 / 9 / 12 / 12` |

注意：REAL 难度显示不是简单等于 `level_real`。本次实测：

- `level_real=12/13` 都显示 REAL 2。
- `level_real=14/15` 显示 REAL 3。
- 目前采用 `15/14/13/12`，游戏实际显示为目标状态。

需要同步修改三份列表，否则游戏可能读到旧值：

```text
E:\hiraeth\contents\data\sound\music_list.xml
E:\hiraeth\contents\data_op2\sound\music_list.xml
E:\hiraeth\contents\data_op3\sound\music_list.xml
```

## 目录结构

主谱面和音频位于：

```text
E:\hiraeth\contents\data\sound\music\m_c0035_hanon_120
E:\hiraeth\contents\data\sound\music\m_c0036_hanon_108
E:\hiraeth\contents\data\sound\music\m_c0037_hanon_90
E:\hiraeth\contents\data\sound\music\m_c0038_hanon_78
```

每首目录包含：

```text
<basename>.xsb
<basename>.xwb
<basename>_pre.xsb
<basename>_pre.xwb
<basename>_00normal.xml
<basename>_01hard.xml
<basename>_02extreme.xml
<basename>_03real.xml
```

视觉 mod 位于：

```text
E:\hiraeth\contents\data_mods\hanon_visuals\jacket\jkms_l\afp_jkms0142_l_ifs
E:\hiraeth\contents\data_mods\hanon_visuals\jacket\jkms_l\afp_jkms0143_l_ifs
E:\hiraeth\contents\data_mods\hanon_visuals\jacket\jkms_l\afp_jkms0144_l_ifs
E:\hiraeth\contents\data_mods\hanon_visuals\jacket\jkms_l\afp_jkms0145_l_ifs
E:\hiraeth\contents\data_mods\hanon_visuals\jacket\jkms_s\afp_jkms014_s_ifs
```

## 音频

本次稳定方案：

- 主音频：每首一个 `.xwb`。
- 预览音频：每首一个 `_pre.xwb`。
- `.xsb` 沿用稳定模板 `M_C0036_strauss_radetzky` 的内部结构。
- `.xsb` 文件名改为目标 basename，但内部字符串仍是 `M_C0036_strauss_radetzky`。
- 这个不一致在本案例中可正常预览、进歌、有声音。

关键经验：

- 不要随意改 `.xsb` 内部 bank 字符串。之前反复测试表明，完整改名或不稳定模板更容易导致无声或进歌未响应。
- `m_c0036_strauss_radetzky.xsb` 目前是最稳模板。
- 主 `.xsb` cue 为 `_backtrack`。
- 预览 `.xsb` cue 为 `_preview`。
- `_pre.xwb` 正常后，选曲界面才有预览音乐。

当前文件规模可作为 sanity check：

| basename | 主 `.xwb` 大小 | `_pre.xwb` 大小 |
|---|---:|---:|
| `m_c0035_hanon_120` | 14,952,872 | 964,912 |
| `m_c0036_hanon_108` | 16,614,252 | 964,912 |
| `m_c0037_hanon_90` | 19,937,152 | 964,912 |
| `m_c0038_hanon_78` | 23,004,272 | 964,912 |

检查 bank：

```bash
python3 scripts/inspect_banks.py /mnt/e/hiraeth/contents/data/sound/music/m_c0035_hanon_120
```

预期主 `.xsb` 字符串中仍能看到：

```text
M_C0036_strauss_radetzky
_backtrack
```

## 谱面 XML

REAL 是完整谱面，低三难度由 REAL 自动降难度生成。

当前四首状态：

| difficulty | notes | moments | key width | scale range |
|---|---:|---:|---:|---|
| NORMAL | 2710 | 2258 | 5 | `36-79` |
| HARD | 3011 | 2258 | 4 | `35-79` |
| EXTREME | 3764 | 2258 | 3 | `35-79` |
| REAL | 4516 | 2258 | 3 | `35-79` |

各 BPM 的 `first_bpm` 和结束时间：

| basename | first_bpm | music_finish_time_msec |
|---|---:|---:|
| `m_c0035_hanon_120` | `12000000` | `315000` |
| `m_c0036_hanon_108` | `10800000` | `350000` |
| `m_c0037_hanon_90` | `9000000` | `420000` |
| `m_c0038_hanon_78` | `7800000` | `484615` |

低难度生成逻辑：

- NORMAL：保留所有时间点的高音主线，低音每 5 个时间点保留 1 个，键宽改为 5。
- HARD：保留所有高音，低音每 3 个时间点保留 1 个，键宽改为 4。
- EXTREME：保留所有高音，低音保留约 2/3，键宽为 3。
- REAL：不动。

这和官方统计接近：NORMAL 大约 REAL 的 60%，HARD 大约 65%，EXTREME 大约 83%。

重要 XML 规则：

- root 必须是 `music_score`。
- `header`、`note_data`、`event_data`、`beat_data`、`track_info`、`velocity_zone_data` 都要存在。
- `velocity_zone_data` 可以为空结构，但不能缺失。
- `event_data` 至少需要合理 BPM 事件。
- `scale_piano` 本案例最终用 `1-88` 表头，实际 note 落在 `35-79`。
- `sub_note/track_index` 必须能对应到 `track_info`。
- `velocity` 不要为了无声测试长期置 0。最终需要 backtrack 声音时，音频由 `.xwb/.xsb` 提供，note velocity 不应作为解决 backtrack 的手段。

## 曲目列表

修改三份 `music_list.xml`，并保持 `cp932/Shift_JIS` 编码：

```text
contents/data/sound/music_list.xml
contents/data_op2/sound/music_list.xml
contents/data_op3/sound/music_list.xml
```

四首的最终字段：

```text
M_C0035_hanon_120  7 / 9 / 12 / 15
M_C0036_hanon_108  7 / 9 / 12 / 14
M_C0037_hanon_90   7 / 9 / 12 / 13
M_C0038_hanon_78   7 / 9 / 12 / 12
```

必须注意：

- `data_op2` 和 `data_op3` 里也有对应 music_list。只改 `data` 可能导致游戏显示读到旧值。
- `music_list.xml` 是 Shift_JIS/cp932。不要用 UTF-8 强行写回。
- 修改后用 XML parser 验证一次。

验证命令：

```bash
python3 - <<'PY'
from pathlib import Path
from xml.etree import ElementTree as ET
for path in [
    Path('/mnt/e/hiraeth/contents/data/sound/music_list.xml'),
    Path('/mnt/e/hiraeth/contents/data_op2/sound/music_list.xml'),
    Path('/mnt/e/hiraeth/contents/data_op3/sound/music_list.xml'),
]:
    ET.fromstring(path.read_bytes().decode('cp932'))
    print(path, 'ok')
PY
```

## 封面

封面文件：

```text
jk0142_l.png ... jk0145_l.png
jk0142_s.png ... jk0145_s.png
```

格式：

```text
large: 326 x 326, RGBA PNG
small: 74 x 74, RGBA PNG
```

本案例四首使用同一张封面图，缩放后覆盖四个编号。

生成方式示例：

```bash
ffmpeg -y -i cover.png -vf "scale=326:326:flags=lanczos,format=rgba" -frames:v 1 jk_hanon_l.png
ffmpeg -y -i cover.png -vf "scale=74:74:flags=lanczos,format=rgba" -frames:v 1 jk_hanon_s.png
```

覆盖位置：

```text
contents/data_mods/hanon_visuals/jacket/jkms_l/afp_jkms0142_l_ifs/jk0142_l.png
contents/data_mods/hanon_visuals/jacket/jkms_l/afp_jkms0143_l_ifs/jk0143_l.png
contents/data_mods/hanon_visuals/jacket/jkms_l/afp_jkms0144_l_ifs/jk0144_l.png
contents/data_mods/hanon_visuals/jacket/jkms_l/afp_jkms0145_l_ifs/jk0145_l.png
contents/data_mods/hanon_visuals/jacket/jkms_s/afp_jkms014_s_ifs/jk0142_s.png
contents/data_mods/hanon_visuals/jacket/jkms_s/afp_jkms014_s_ifs/jk0143_s.png
contents/data_mods/hanon_visuals/jacket/jkms_s/afp_jkms014_s_ifs/jk0144_s.png
contents/data_mods/hanon_visuals/jacket/jkms_s/afp_jkms014_s_ifs/jk0145_s.png
```

## 文字纹理

文字纹理文件：

```text
ms0142_l.png ... ms0145_l.png
ms0142_s.png ... ms0145_s.png
```

格式：

```text
ms####_l: 326 x 50, RGBA PNG, transparent background
ms####_s: 248 x 64, RGBA PNG, transparent background
```

当前生成脚本：

```text
scripts/generate_ms_l_texture.py
scripts/generate_ms_s_texture.py
```

字体和颜色：

```text
font: DreamHanSerifJP-W10.ttf
color: rgb(68, 46, 14)
```

Hanon 文案：

```text
title: ピアノ基礎練習 No.1-10
artist: ハノン(<bpm> bpm)
description: 毎日の小さな反復が、確かな音をつくる
```

生成示例：

```bash
python3 scripts/generate_ms_l_texture.py \
  --title 'ピアノ基礎練習 No.1-10' \
  --artist 'ハノン(120 bpm)' \
  --output work/visual_samples/dream_han_serif_jp/game_install/ms0142_l.png

python3 scripts/generate_ms_s_texture.py \
  --title 'ピアノ基礎練習 No.1-10' \
  --artist 'ハノン(120 bpm)' \
  --description '毎日の小さな反復が、確かな音をつくる' \
  --output work/visual_samples/dream_han_serif_jp/game_install/ms0142_s.png
```

关键经验：

- 必须是透明背景，不能从白底扣图，否则游戏里会出现白底或白边。
- 竖线不是文字的一部分，生成器中固定绘制并对齐官方纹理。
- 当前字体基准来自梦源宋体日语子集 `DreamHanSerifJP-W10`。
- 不同电脑的 Edge/System.Drawing 抗锯齿可能有 1px 级差异，换电脑要重新对比官方样张。

## 替换顺序

建议顺序：

1. 复制或生成目标 song folder。
2. 放入主音频 `.xwb/.xsb` 和预览 `_pre.xwb/_pre.xsb`。
3. 放入四个难度 XML。
4. 同步修改三份 `music_list.xml`。
5. 生成并替换 `jk` 封面。
6. 生成并替换 `ms` 文字纹理。
7. 清理 `contents/data_mods/_cache`。
8. 启动 MonkeyBusiness，再启动游戏测试。

每次覆盖前备份：

```bash
STAMP=$(date +%Y%m%d_%H%M%S)
mkdir -p /mnt/e/hiraeth/contents/_backup_before_custom_song_$STAMP
```

清缓存：

```bash
rm -rf /mnt/e/hiraeth/contents/data_mods/_cache
```

## 验证清单

静态验证：

```bash
# 谱面 XML 能解析
python3 - <<'PY'
from pathlib import Path
from xml.etree import ElementTree as ET
base = Path('/mnt/e/hiraeth/contents/data/sound/music')
for p in base.glob('m_c003*_hanon_*/*.xml'):
    ET.parse(p)
print('hanon xml ok')
PY

# 列表 XML 能解析
python3 - <<'PY'
from pathlib import Path
from xml.etree import ElementTree as ET
for p in [
    Path('/mnt/e/hiraeth/contents/data/sound/music_list.xml'),
    Path('/mnt/e/hiraeth/contents/data_op2/sound/music_list.xml'),
    Path('/mnt/e/hiraeth/contents/data_op3/sound/music_list.xml'),
]:
    ET.fromstring(p.read_bytes().decode('cp932'))
print('music lists ok')
PY

# 图片格式
file /mnt/e/hiraeth/contents/data_mods/hanon_visuals/jacket/jkms_l/afp_jkms0142_l_ifs/jk0142_l.png
file /mnt/e/hiraeth/contents/data_mods/hanon_visuals/jacket/jkms_s/afp_jkms014_s_ifs/jk0142_s.png
file /mnt/e/hiraeth/contents/data_mods/hanon_visuals/jacket/jkms_l/afp_jkms0142_l_ifs/ms0142_l.png
file /mnt/e/hiraeth/contents/data_mods/hanon_visuals/jacket/jkms_s/afp_jkms014_s_ifs/ms0142_s.png
```

游戏内验证：

1. 能进入选曲界面。
2. 四首都显示封面、标题、作者、说明。
3. 预览音乐正常。
4. 四个难度都可选择。
5. NORMAL/HARD/EXTREME/REAL 都能进歌。
6. 进歌后 backtrack 有声音。
7. 游玩结束或退出不未响应。

## 常见故障

### 启动后闪退

优先看：

```text
E:\hiraeth\contents\log.txt
```

常见原因：

- `music_list.xml` 编码被写坏。
- XML 标签缺失或不闭合。
- 三份列表不一致。
- basename、文件夹名和文件名不匹配。

### 选曲可见但 REAL 不可选

检查：

- `_03real.xml` 是否存在。
- `real_unlock_type` 是否为可解锁/已解锁状态。
- MonkeyBusiness 是否已启动。
- 三份 `music_list.xml` 是否同步。

### 预览音乐有、进歌无声

检查：

- 主 `.xwb` 是否存在且大小合理。
- 主 `.xsb` 是否有 `_backtrack` cue。
- 不要只替换 `_pre.xwb`。
- 不要随意改 `.xsb` 内部 bank 字符串。

### 进歌未响应

常见原因：

- `.xsb/.xwb` 结构不稳定。
- XML 中 `track_info`、`sub_note/track_index`、`velocity_zone_data` 结构异常。
- `music_finish_time_msec` 和音频/谱面长度严重不匹配。

### 图片白底或白边

原因：

- 从白底图抠透明导致 alpha 边缘残留。
- 透明像素 RGB 被保留为白色。

解决：

- 直接在透明画布渲染文字。
- 使用当前 `generate_ms_*_texture.py` 的 no-fringe 后处理。

## 当前未完全自动化的部分

- XSB 的可靠全新生成仍未解决；当前依赖 `m_c0036_strauss_radetzky` 稳定模板。
- REAL 显示等级是分段映射，尚未完整反推出所有内部值到显示值的表。
- `filepath.info/xml` 没有明文 Hanon 项，但当前游戏可正常加载。后续做完全独立新增编号时仍要重新验证索引链路。
- 可视纹理生成依赖本机字体、Edge headless 和 Windows PowerShell/System.Drawing。

## 本次重要备份

本次过程中生成过的关键备份：

```text
E:\hiraeth\contents\data\sound\_backup_hanon_difficulty_rebuild_20260624_233507
E:\hiraeth\contents\_backup_hanon_level_lists_20260624_234146
E:\hiraeth\contents\_backup_hanon_real_level_fix_20260624_234612
E:\hiraeth\contents\_backup_hanon_real_level_15141312_20260624_235038
E:\hiraeth\contents\data_mods\hanon_visuals\_backup_jk_covers_20260624_232521
E:\hiraeth\contents\data_mods\hanon_visuals\_backup_ms_textures_20260624_232252
```

后续如果视觉或等级想回退，优先从这些备份中恢复对应文件。
