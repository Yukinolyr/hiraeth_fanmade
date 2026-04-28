# IFS LayeredFS / Omni 更新包分析笔记

本文记录对 `reference/ifs_sample` 和 `reference/NOSTALGIAomni For 2024102200` 的只读分析结果，用于后续仿照官方/现成更新包格式制作自制曲测试包。

## LayeredFS 基本结论

`reference/ifs_sample/README.md` 说明 IFS LayeredFS 会拦截游戏文件访问，并优先使用 `data_mods` 下的 mod 文件。安装方式是把对应架构的 DLL 放到游戏 DLL 同级目录，把 `data_mods` 文件夹放到 `data` 文件夹同级位置。

mod 路径规则：

```text
data_mods/<mod_name>/<path_inside_data>
```

Nostalgia 这类存在额外数据目录的游戏，需要把额外数据目录名也放进 mod 路径：

```text
data_mods/<mod_name>/data_op2/...
data_mods/<mod_name>/data_op3/...
```

XML 有特殊追加机制：

```text
original: data_op3/sound/music_list.xml
append:   data_mods/<mod_name>/data_op3/sound/music_list.merged.xml
```

也就是说，新增曲目不一定需要替换整个 `music_list.xml`，可以仿照 Omni 使用 `.merged.xml` 追加 `<music_spec>`。

## Omni 包结构

当前更新包：

```text
reference/NOSTALGIAomni For 2024102200/data_mods/omni
```

已观察到的主要内容：

```text
data_mods/omni/
  sound/music/
  data_op2/sound/music/
  data_op3/sound/music/
  data_op3/sound/music_list.merged.xml
  jacket/jkms_l/
  jacket/jkms_s/
```

`data_mods/_cache/` 是 LayeredFS 生成的缓存，可以删除，不应作为手工包结构的源数据。

Omni 包中共有 49 个歌曲目录，同时 `music_list.merged.xml` 中也有 49 个 `music_spec` 条目。

## 歌曲目录文件集

样本：`m_l0003_himawari`

```text
data_mods/omni/sound/music/m_l0003_himawari/
  m_l0003_himawari.xsb
  m_l0003_himawari.xwb
  m_l0003_himawari_00normal.xml
  m_l0003_himawari_01hard.xml
  m_l0003_himawari_02extreme.xml
  m_l0003_himawari_pre.xsb
  m_l0003_himawari_pre.xwb
```

样本：`m_l0084_pretender`

```text
data_mods/omni/data_op3/sound/music/m_l0084_pretender/
  m_l0084_pretender.xsb
  m_l0084_pretender.xwb
  m_l0084_pretender_00normal.xml
  m_l0084_pretender_01hard.xml
  m_l0084_pretender_02extreme.xml
  m_l0084_pretender_pre.xsb
  m_l0084_pretender_pre.xwb
```

三难度曲目没有 `_03real.xml` 是正常情况。`music_list.merged.xml` 中对应 `level_real` 为 `0`，`real_start_date` 通常是未来占位值。

## music_list.merged.xml

文件路径：

```text
reference/NOSTALGIAomni For 2024102200/data_mods/omni/data_op3/sound/music_list.merged.xml
```

结构：

```xml
<?xml version='1.0' encoding='Shift_JIS'?>
<music_list>
  <music_spec __type='void' index='17'>
    <basename __type='str'>M_L0003_himawari</basename>
    ...
  </music_spec>
</music_list>
```

观察结果：

- 根节点是 `music_list`。
- 不需要 `revision` 或 `release_code`。
- 条目使用完整 `music_spec`，不是只写差异字段。
- 编码仍为 `Shift_JIS`。
- basename 使用大写 `M_...`。
- 文件夹和文件名使用小写 `m_...`。
- `.xsb/.xwb` 内部 bank name 使用大写 `M_...`。

样本条目摘要：

| index | basename | title | levels N/H/E/R | bgm | key | start | real_start |
|---:|---|---|---|---:|---:|---|---|
| 17 | `M_L0003_himawari` | `ひまわりの約束` | `3/5/7/0` | -6 | -2 | 2017-03-01 10:00 | 2100-01-01 00:00 |
| 349 | `M_L0084_pretender` | `Pretender` | `2/6/10/0` | 0 | 0 | 2019-12-25 10:00 | 2100-01-01 00:00 |
| 477 | `M_L0097_yorunikakeru` | `夜に駆ける` | `2/5/9/11` | -6 | -1 | 2021-07-15 10:00 | 2021-07-15 10:00 |

## 验证结果

`m_l0003_himawari`：

```bash
python3 validate_song.py "reference/NOSTALGIAomni For 2024102200/data_mods/omni/sound/music/m_l0003_himawari"
```

结果：

- `PASS`
- `errors: 0`
- `warnings: 1`
- warning 仅为缺少 `03real`
- XML：Normal/Hard/Extreme 三个难度

`m_l0084_pretender`：

```bash
python3 validate_song.py "reference/NOSTALGIAomni For 2024102200/data_mods/omni/data_op3/sound/music/m_l0084_pretender"
```

结果：

- `PASS`
- `errors: 0`
- `warnings: 1`
- warning 仅为缺少 `03real`
- XML：Normal/Hard/Extreme 三个难度

Bank 结构：

- 主 `.xsb` 包含 `M_L....` 和 `_backtrack`。
- 预览 `.xsb` 包含 `M_L...._pre` 和 `_preview`。
- 主 `.xwb` 是 ADPCM，当前样本主 XWB 大小为 8152 bytes。
- 预览 `.xwb` 是 ADPCM。

## 对自制曲包的影响

从 Omni 可以推导出一个更合理的新增曲测试包形态：

```text
data_mods/fanmade/
  data_op3/sound/music_list.merged.xml
  data_op3/sound/music/m_l9xxx_custom/
    m_l9xxx_custom.xsb
    m_l9xxx_custom.xwb
    m_l9xxx_custom_00normal.xml
    m_l9xxx_custom_01hard.xml
    m_l9xxx_custom_02extreme.xml
    m_l9xxx_custom_pre.xsb
    m_l9xxx_custom_pre.xwb
```

如果暂时没有 Real 难度：

- 不放 `_03real.xml`。
- `music_list.merged.xml` 中 `level_real` 设为 `0`。
- `real_start_date` 可参考 Omni 的非 Real 曲目设为 `2100-01-01 00:00`。

对于首个新增曲实验，推荐先不处理 jacket：

- 先确认歌曲是否能出现在列表。
- 再确认能进入预览和游玩。
- 最后再补 `jacket/jkms_s` 和 `jacket/jkms_l`。

## 已新增脚本

### 生成 music_list.merged.xml

`scripts/create_music_list_entry.py` 已支持 `--merged`，可以输出 Omni 同款的单条目追加 XML：

```bash
python3 scripts/create_music_list_entry.py reference/music_list.xml work/music_list_merged_test/music_list.merged.xml \
  --template M_T0168_marigoldjazzy \
  --basename M_L0002_closeup_test \
  --title CloseupTest \
  --artist Fanmade \
  --levels 3/6/9/12 \
  --index 9001 \
  --merged
```

输出结构：

```text
work/music_list_merged_test/music_list.merged.xml
```

如果输入文件是 Omni 的 `music_list.merged.xml`，一定要显式指定 `--index`，否则脚本只能根据该 merged 文件自身计算下一个 index，可能和本体 `music_list.xml` 中已有条目冲突。

### 装配 LayeredFS 歌曲包

新增脚本：

```bash
python3 scripts/assemble_layeredfs_song_mod.py work/layeredfs_smoke_closeup_test \
  --mod-name fanmade \
  --data-root data_op3 \
  --song-dir work/custom_song_closeup_test_l \
  --music-list-merged work/music_list_merged_test/music_list.merged.xml
```

输出结构：

```text
work/layeredfs_fanmade_test/data_mods/fanmade/data_op3/sound/...
```

脚本只复制当前歌曲 basename 对应的 `.xsb`、`.xwb`、谱面 `.xml`，不会把实验目录里的其他文件一起塞进歌曲文件夹。

烟测结果：

- `work/layeredfs_smoke_closeup_test` 已成功生成。
- `python3 validate_song.py work/layeredfs_smoke_closeup_test/data_mods/fanmade/data_op3/sound/music/m_l0002_closeup_test`：`PASS`，`errors: 0`，`warnings: 0`。

## 下一步

首个测试可以用已成功的 Himawari 音频和谱面，但改成新 basename，例如：

```text
m_l9001_himawari_fanmade
M_L9001_himawari_fanmade
```

这样可以从“替换 marigoldjazzy 壳”推进到“通过更新包机制新增曲目”。

## Himawari 新增曲测试反馈

`work/layeredfs_himawari_ml_raw` 测试失败。更新后的 `reference/log.txt` 只记录到：

```text
MainIOBootLoader_success_exit
AfpPackBootLoader_success_exit
```

日志中没有出现 `MusicList`、`M_L9001_himawari_fanmade`、`Load wave` 或 `Load sound`。这说明失败点很可能早于曲目列表和新增曲资源加载阶段。

当前日志里的游戏版本线索：

```text
soft id code: PAN:J:A:A:2023123100
```

但项目内 `reference/music_list.xml` 是：

```text
release_code="2024123100"
```

因此，`raw` 和 `full_list` 这种整份覆盖 `music_list.xml` 的方案存在明显版本不匹配风险。下一步应先测试 `work/layeredfs_music_list_identity`。如果 identity 包也失败，说明当前 `reference/music_list.xml` 不能作为这份 `PAN-2023123100` 游戏副本的整表覆盖基底；需要从当前游戏副本提取同版本原始 `music_list.xml` 后再生成 raw 插入包。

后续反馈：只保留 `work/layeredfs_music_list_identity` 时可以进入游戏。这说明整份 `music_list.xml` 覆盖本身可行，`raw` 失败更可能来自新增条目变量。

当前最大已用 `music_spec index` 为 `594`，而失败包使用了 `index=9001`。这可能导致游戏在曲表初始化时访问超出预期范围的索引。已生成新的 A/B 测试包：

```text
work/layeredfs_himawari_ml_raw_index595
```

相对失败的 raw 包，它只把新增条目改为：

```text
index="595"
```

basename、歌曲目录和歌曲文件仍保持 `M_L9001_himawari_fanmade` / `m_l9001_himawari_fanmade`，用于单独验证高 index 是否是失败原因。

后续反馈：`work/layeredfs_himawari_ml_raw_index595` 仍无法进入游戏。更新后的日志仍没有出现 `MusicList`、`M_L9001_himawari_fanmade`、`Load wave` 或 `Load sound`，只停在早期 boot loader 阶段。因此 `index=9001` 不是唯一原因。

已准备两个更小的隔离包：

```text
work/layeredfs_himawari_ml_raw_index595_list_only
work/layeredfs_himawari_ml_song_only
```

测试目的：

- `raw_index595_list_only`：只覆盖带新增条目的 `music_list.xml`，不包含歌曲文件。若仍无法进入游戏，说明新增 `music_spec` 条目本身有问题。
- `song_only`：只放 `m_l9001_himawari_fanmade` 歌曲目录，不覆盖 `music_list.xml`。若它无法进入游戏，说明新增目录或资源文件会影响启动；若它能进入，歌曲目录本身不是启动失败主因。

后续反馈：`work/layeredfs_himawari_ml_raw_index595_list_only` 仍无法进入游戏。因此歌曲文件和歌曲目录已排除，问题集中在新增 `music_spec` 条目。

进一步观察：当前 `reference/music_list.xml` 中 `M_L` 编号最高只到 `M_L0103_mixednuts`，而此前新增条目使用 `M_L9001_himawari_fanmade`。已生成更贴近官方范围的只曲表测试包：

```text
work/layeredfs_himawari_ml0104_list_only
```

该包只改新增条目的 basename：

```text
M_L9001_himawari_fanmade -> M_L0104_yoruhimawari
```

并保持 `music_spec index=595`，用于验证 `M_L9001` 这种超高 L 编号是否导致曲表初始化失败。

后续反馈：`work/layeredfs_himawari_ml0104_list_only` 仍无法进入游戏。因此 `M_L9001` 超高编号不是唯一原因。

新的可疑点是 `index=595`。虽然这是当前最大 index `594` 的下一个值，但游戏内部可能按已有索引范围或固定表分配；直接使用最大值之后的新 index 可能仍会越界。原表存在空洞：

```text
index=544
index=546
index=547
index=548
```

但没有 `index=545`。已生成下一轮只曲表包：

```text
work/layeredfs_himawari_ml0104_index545_list_only
```

该包使用：

```text
index=545
basename=M_L0104_yoruhimawari
```

用于验证是否必须占用原表范围内的空洞 index，而不能使用 `max(index)+1`。

后续反馈：`work/layeredfs_himawari_ml0104_index545_list_only` 仍无法进入游戏。到这里已经排除了：

- `M_L9001` 超高 basename 编号；
- `index=595` 超过当前最大 index；
- 新增歌曲目录和歌曲资源文件。

当前最强假设：整份 `music_list.xml` 覆盖可以工作，但不能通过简单增加一个 `music_spec` 把条目数从 544 变成 545；游戏可能还有其他表、缓存或固定数组与曲表条目数量绑定。

已生成下一轮验证包：

```text
work/layeredfs_music_list_modify_existing
```

这个包不新增条目、不包含歌曲目录，只把现有条目 `M_L0003_himawari` 的字段改为：

```text
offline: 0 -> 1
```

如果这个包能进入游戏，就说明“修改现有 `music_spec`”可行，失败集中在“新增 `music_spec` 数量”。后续新增曲应优先考虑占用/替换一个现有条目，而不是增加条目数量。

后续反馈：`work/layeredfs_music_list_modify_existing` 可以进入游戏。结论确认：

- LayeredFS 覆盖整份 `music_list.xml` 可行。
- 修改现有 `music_spec` 可行。
- 当前失败点集中在“增加 `music_spec` 条目数量”。

基于这个结论，已生成占用现有 Himawari 条目的完整测试包：

```text
work/layeredfs_replace_himawari_ml0104
```

该包不新增条目，而是把 `index=17` 的 `M_L0003_himawari` 改为：

```text
M_L0104_yoruhimawari
Yoru_no_Himawari
Fanmade
```

并放入对应歌曲目录：

```text
data_op3/sound/music/m_l0104_yoruhimawari/
```

`.xsb/.xwb` 内部 bank name 已同步为 `M_L0104_yoruhimawari` 和 `M_L0104_yoruhimawari_pre`。这个包用于验证“占用现有曲目入口”的完整路径是否可行。

## Elise 入口替换测试包

用户反馈 `M_C0003_lvb_elise` / `エリーゼのために` 更容易在游戏内找到。已生成不改曲表、只覆盖歌曲资源的测试包：

```text
work/layeredfs_replace_elise_himawari
```

目标条目：

```text
M_C0003_lvb_elise
エリーゼのために
```

包内路径：

```text
data_mods/replace_elise_himawari/data_op3/sound/music/m_c0003_lvb_elise/
```

处理内容：

- 从 `work/himawari_ml_song` 复制并重命名为 `m_c0003_lvb_elise`。
- `.xsb/.xwb` 内部 bank name 已改为 `M_C0003_lvb_elise` 和 `M_C0003_lvb_elise_pre`。
- 额外复制 `_02extreme.xml` 为 `_03real.xml`，避免 Real 难度回落到原曲谱面。
- 不覆盖 `music_list.xml`，所以游戏内仍按原曲 `エリーゼのために` 查找。

验证结果：

- `python3 validate_song.py work/layeredfs_replace_elise_himawari/data_mods/replace_elise_himawari/data_op3/sound/music/m_c0003_lvb_elise`：`PASS`，`errors: 0`。
- warnings 仍来自 Himawari 谱面中的 `scale_piano > 88`。

后续用户反馈：可以进入游戏，但没有预览音乐，点击进入歌曲后卡死。进入游戏 log 显示实际加载路径为：

```text
data/sound/music/M_C0003_lvb_elise/M_C0003_lvb_elise.xwb
data/sound/music/M_C0003_lvb_elise/M_C0003_lvb_elise.xsb
```

结论：`M_C0003_lvb_elise` 是基础 `data` 曲目，不是三代更新曲；LayeredFS 覆盖路径必须匹配基础路径和大小写。之前放在 `data_op3/sound/music/m_c0003_lvb_elise/` 或小写目录的包不能稳定命中该曲目。

已生成精确路径测试包：

```text
work/layeredfs_replace_elise_himawari_exactpath
```

包内路径：

```text
data_mods/replace_elise_himawari_exactpath/data/sound/music/M_C0003_lvb_elise/
```

该目录包含大写 basename 的主音频、预览音频和 4 个难度 XML：

```text
M_C0003_lvb_elise.xsb
M_C0003_lvb_elise.xwb
M_C0003_lvb_elise_pre.xsb
M_C0003_lvb_elise_pre.xwb
M_C0003_lvb_elise_00normal.xml
M_C0003_lvb_elise_01hard.xml
M_C0003_lvb_elise_02extreme.xml
M_C0003_lvb_elise_03real.xml
```

用户后续反馈：精确基础路径包仍显示/游玩原曲，推测老版本基础 `data` 曲目可能不能通过当前 `data_mods` 机制稳定覆盖。下一步回到已验证过的 Op3 曲目 `M_T0168_marigoldjazzy` 作为测试壳。

已生成 Op3 Marigold Jazzy 精确路径包：

```text
work/layeredfs_replace_marigoldjazzy_himawari_exactpath
```

策略：

- 不修改 `music_list.xml`。
- 不修改曲名、artist、解锁信息。
- 包含完整歌曲资源目录，包括 `.xsb`、主 XWB、预览 XWB 和四个难度 XML。
- 可见的自制谱面仍在 `_02extreme.xml`，其余难度用于补齐完整目录。

为适配路径大小写差异，包内同时包含：

```text
data_Op3/sound/music/M_T0168_marigoldjazzy/
data_op3/sound/music/m_t0168_marigoldjazzy/
```

测试时游戏内仍会显示 `Marigold (Jazzy Hip-Hop Remix)`，应选择 Expert/Extreme 难度验证 Himawari 音频和谱面是否生效。

## Fengbei on Marigold Jazzy

用户新增参考文件：

```text
reference/fengbei/グラウンドスライダー協奏曲第一番「風唄」.wav
reference/fengbei/グラウンドスライダー協奏曲第一番「風唄」Real 3.5 Ver.1 (1).xml
```

已将该曲封装为 `M_T0168_marigoldjazzy` 测试壳：

```text
work/fengbei_on_marigoldjazzy_full
work/omni_fengbei_mj
work/lf_fb_mj
```

处理内容：

- `normalize_chart_xml.py` 将原 XML 规范化为 `m_t0168_marigoldjazzy_02extreme.xml`，`fixed_bpm=16500000`。
- 主音频转为 16000 Hz stereo PCM XWB，bank name 为 `M_T0168_marigoldjazzy`，大小约 10.3 MB，时长 161.448s。
- 预览音频截取前 15.158s，转为 16000 Hz stereo PCM XWB，bank name 为 `M_T0168_marigoldjazzy_pre`。
- `.xsb` 和其他难度 XML 从原 `reference/m_t0168_marigoldjazzy` 补齐。
- 包内同时包含 `data_Op3/M_T...` 和 `data_op3/m_t...` 两套路径。

验证结果：

- `validate_song.py work/fengbei_on_marigoldjazzy_full`：`PASS`，`errors: 0`。
- `validate_song.py work/omni_fengbei_mj/contents/data_mods/mjfb/data_op3/sound/music/m_t0168_marigoldjazzy`：`PASS`。
- `validate_song.py work/omni_fengbei_mj/contents/data_mods/mjfb/data_Op3/sound/music/M_T0168_marigoldjazzy`：`PASS`。

当前保留原谱面的 `scale_piano` 数据，最大值到 107；验证器报告 183 条 `scale_piano > 88` warnings。首次测试先不 clamp，避免改变谱面语义。如果游戏进歌失败或显示异常，再生成 `scale_piano` clamp 到 88 的 A/B 测试包。

测试反馈：预览可以播放，但进歌卡死。log 关键行：

```text
W:MusicScoreManager: ... track number:0
W:MusicScoreManager: ... label:_01_A-1
W:CMainPlayMusic: ... M_T0168_marigoldjazzy_02extreme.xml
W:ErrorManager: HDD ERROR, ERROR CODE : 5-1501-0000
```

对比官方 `m_t0168_marigoldjazzy_02extreme.xml` 发现：

- 官方 `sub_note/track_index` 使用 `1..5`。
- Fengbei 规范化后仍保留源谱 `0/1`，但其 `track_info` 是 `index=1..3`，所以 `track_index=0` 无法匹配。

已生成修正版包：

```text
work/omni_fengbei_mj_clamp88
work/lf_fb_mj_clamp88
```

修正内容：

- `scale_piano` 和 `sub_note/scale_piano` clamp 到 `0..88`。
- `sub_note/track_index` 整体 `+1`，从 `0/1` 变为 `1/2`。
- 音频、`.xsb`、其他难度 XML 保持与 `mjfb` 一致。

验证结果：

- `validate_song.py work/omni_fengbei_mj_clamp88/contents/data_mods/mjfb88/data_op3/sound/music/m_t0168_marigoldjazzy`：`PASS`，`warnings: 0`。
- `validate_song.py work/omni_fengbei_mj_clamp88/contents/data_mods/mjfb88/data_Op3/sound/music/M_T0168_marigoldjazzy`：`PASS`，`warnings: 0`。

## Fengbei 新增曲测试

在 Fengbei 替换 Marigold Jazzy 已成功后，生成一个不占用现有曲目的“正常更新式新增曲”测试包：

```text
work/omni_fengbei_add
work/lf_fengbei_add
```

新增曲条目：

```text
basename: M_L0104_fengbei
folder:   m_l0104_fengbei
title:    グラウンドスライダー協奏曲第一番「風唄」
artist:   Fanmade
levels:   5/9/13/15
index:    595
offline:  1
```

包结构采用 Omni 追加方式：

```text
contents/data_mods/fbadd/data_op3/sound/music_list.merged.xml
contents/data_mods/fbadd/data_op3/sound/music/m_l0104_fengbei/
```

为适配路径大小写差异，资源目录还额外包含：

```text
contents/data_mods/fbadd/data_Op3/sound/music/M_L0104_fengbei/
```

处理内容：

- 从已验证可运行的 Fengbei clamp88 谱面生成四个难度 XML。
- `.xsb/.xwb` 文件名和内部 bank name 均改为 `M_L0104_fengbei` / `M_L0104_fengbei_pre`。
- `music_list.merged.xml` 只包含一个完整 `music_spec`，根节点为 `<music_list>`，Shift_JIS 编码。

验证结果：

- `validate_song.py work/fengbei_added_song_m_l0104`：`PASS`，`warnings: 0`。
- `validate_song.py work/omni_fengbei_add/contents/data_mods/fbadd/data_op3/sound/music/m_l0104_fengbei`：`PASS`。
- `validate_song.py work/omni_fengbei_add/contents/data_mods/fbadd/data_Op3/sound/music/M_L0104_fengbei`：`PASS`。

测试判断：

- 如果游戏能进选曲但看不到新歌，优先检查 `music_list.merged.xml` 是否被 Omni/LayeredFS merge。
- 如果游戏早期启动失败，说明新增 `music_spec` 条目数量仍可能触发与此前 full/raw 测试相同的问题。
- 如果能看到新歌但进入失败，再看 log 中实际请求的 `M_L0104_fengbei` 资源路径。

后续测试反馈：游戏可以进入，疑似可以找到新曲，但新曲查找困难；标题显示为 `loading`，没有预览音乐，进入歌曲后游戏无响应。由此可判断 `music_list.merged.xml` 至少部分生效，但显示字段、排序字段或资源路径仍存在变量。

已生成下一轮隔离测试包：

```text
work/omni_fengbei_add_2025
work/lf_fengbei_add_2025
```

新增曲条目保持：

```text
basename: M_L0104_fengbei
index:    595
levels:   5/9/13/15
offline:  1
```

本轮改动：

- `title` 改为 ASCII：`Fengbei Test`，排除 Shift_JIS 标题或特殊字符显示问题。
- `title_kana` 同步为 `Fengbei Test`。
- `description` 改为 ASCII：`Fengbei custom chart test`。
- `start_date` 和 `real_start_date` 改为 `2025-01-01 10:00`，让歌曲更容易按新曲/时间排序找到。
- `real_release_code` 改为 `2025010100`。
- 除原有 `data_op3` / `data_Op3` 路径外，额外加入 `sound/music` 根路径下的大小写两套资源目录，用于确认无预览是否来自资源 root 不匹配。

包内资源路径：

```text
contents/data_mods/fb25/data_op3/sound/music/m_l0104_fengbei/
contents/data_mods/fb25/data_Op3/sound/music/M_L0104_fengbei/
contents/data_mods/fb25/sound/music/m_l0104_fengbei/
contents/data_mods/fb25/sound/music/M_L0104_fengbei/
```

验证结果：

- `music_list.merged.xml` 中 `M_L0104_fengbei` 条目可解析，标题为 `Fengbei Test`，`start_date` / `real_start_date` 均为 `2025-01-01 10:00`。
- 四个资源目录均通过 `validate_song.py`，`errors: 0`，`warnings: 0`。

下一步测试时只启用 `fb25`，清理 `contents/data_mods/_cache`，在游戏里查找 `Fengbei Test`。如果仍然没有预览或进歌无响应，优先查看 log 中 `M_L0104_fengbei` 附近的 `Load wave` / `Load sound` 行，确认游戏实际请求的是 `data_op3`、`data_Op3`、`sound/music`，还是另一个未覆盖路径。

后续测试反馈：`fb25` 歌曲已排到最前面，说明 `start_date` 调整和曲表追加生效；但仍没有预览音乐，进入歌曲后卡死。检查包内 `.xsb` 字符串确认：

```text
M_L0104_fengbei.xsb:     M_L0104_fengbei / _backtrack
M_L0104_fengbei_pre.xsb: M_L0104_fengbei_pre / _preview
```

因此当前更可疑的是资源 root 或多路径大小写混合在 Windows/LayeredFS 下的命中行为。已生成两个更窄的 A/B 包，每次只启用一个：

```text
work/omni_fengbei_add_2025_op3only
work/lf_fengbei_add_2025_op3only
```

该包标题为 `Fengbei OP3 Test`，只包含：

```text
contents/data_mods/fb25op3/data_op3/sound/music/m_l0104_fengbei/
```

另一个包：

```text
work/omni_fengbei_add_2025_soundonly
work/lf_fengbei_add_2025_soundonly
```

该包标题为 `Fengbei Sound Test`，只包含：

```text
contents/data_mods/fb25snd/sound/music/m_l0104_fengbei/
```

两个包的歌曲目录均通过 `validate_song.py`，`errors: 0`，`warnings: 0`。如果两者都能显示曲名但都没有预览，下一步必须依赖 log 中 `M_L0104_fengbei` 的实际 `Load wave` / `Load sound` 路径；否则无法判断游戏请求的是哪个资源 root。

后续测试反馈：`fb25op3` 和 `fb25snd` 都表现相同。更新 log 中出现关键路径：

```text
property: cannot open 'data_Op3/sound//music/M_L0104_fengbei/M_L0104_fengbei_02extreme.xml'
SoundCtrl: Load wave=data_Op3/sound/music/M_L0104_fengbei/M_L0104_fengbei.xwb
SoundCtrl: Load sound = data_Op3/sound/music/M_L0104_fengbei/M_L0104_fengbei.xsb
Class_Wavebank::Load: ... data_Op3/sound/music/M_L0104_fengbei/M_L0104_fengbei.xwb
Class_Soundbank::Load: ... data_Op3/sound/music/M_L0104_fengbei/M_L0104_fengbei.xsb
```

`PropertyDesc` 返回 `-2147024894`，对应 Windows `ERROR_FILE_NOT_FOUND`。这说明当前失败不是谱面内容不合规，而是游戏按 `data_Op3/sound/music/M_L0104_fengbei/` 的大小写精确路径找文件时没有命中 mod 资源。

已生成精确大写路径包：

```text
work/omni_fengbei_add_2025_upperexact
work/lf_fengbei_add_2025_upperexact
```

mod 名：

```text
fb25u
```

可见标题：

```text
Fengbei Upper Test
```

包内只使用 log 请求的路径：

```text
contents/data_mods/fb25u/data_Op3/sound/music_list.merged.xml
contents/data_mods/fb25u/data_Op3/sound/music/M_L0104_fengbei/
```

验证结果：

- `validate_song.py work/omni_fengbei_add_2025_upperexact/contents/data_mods/fb25u/data_Op3/sound/music/M_L0104_fengbei`：`PASS`，`errors: 0`，`warnings: 0`。
- `music_list.merged.xml` 中标题为 `Fengbei Upper Test`，`start_date` / `real_start_date` 仍为 `2025-01-01 10:00`。

测试判断：

- 如果 `Fengbei Upper Test` 不显示，说明 `.merged.xml` hook 可能只识别小写 `data_op3`，需要做“lowercase list + uppercase resource”的复制策略。
- 如果标题显示且 log 不再出现 `cannot open M_L0104_fengbei`，则路径问题解决；若仍卡死，再回到谱面/音频内容层面排查。

后续测试反馈：`fb25u` 标题不显示，与之前现象一致。log 中没有再出现 `cannot open M_L0104_fengbei`，但出现：

```text
Class_Soundbank::Load: ... data_Op3/sound/music/M_L0104_fengbei/M_L0104_fengbei_pre.xsb
Class_Soundbank::Load: ... data_Op3/sound/music/M_L0104_fengbei/M_L0104_fengbei.xsb
imagefs: cannot open '/data/jacket/jkms_l/afp_jkms0595_l.ifs'
afpu-render: get_bitmap_info[ms0595_s] can not find.
```

当前结论：

- 大写资源路径已命中；失败已从“找不到文件”推进到“XSB interface 创建失败”。
- `music_list.merged.xml` 放在 `data_Op3` 下时标题不稳定，仍应优先使用小写 `data_op3`。
- `index=595` 没有对应 jacket，因此会出现 `ms0595_s` / `afp_jkms0595_l.ifs` 缺失。这个会影响封面显示，但不应单独导致主音频 XSB interface 失败。
- `M_L0104_fengbei` 比模板 `M_T0168_marigoldjazzy` 短。当前 `patch_bank_names.py` 只替换可见 64 字节 bank name 槽，没有重建 XSB 内部未知表；改短 bank name 可能导致 XSB 创建失败。

已生成两个新测试包。

第一，混合路径包：

```text
work/omni_fengbei_add_2025_mix
work/lf_fengbei_add_2025_mix
```

mod 名：

```text
fb25mix
```

可见标题：

```text
Fengbei Mix Test
```

结构：

```text
contents/data_mods/fb25mix/data_op3/sound/music_list.merged.xml
contents/data_mods/fb25mix/data_op3/sound/music/M_L0104_fengbei/
```

该包用于验证“小写 list root + 大写 basename 资源”是否可以同时保留标题和命中资源。

第二，等长 basename 包：

```text
work/omni_fengbei_add_lenpreserve
work/lf_fengbei_add_lenpreserve
```

mod 名：

```text
fblen
```

可见标题：

```text
Fengbei Length Test
```

新增 basename：

```text
M_T0169_fengbeimusicx
```

它与已验证模板等长：

```text
M_T0168_marigoldjazzy
```

结构：

```text
contents/data_mods/fblen/data_op3/sound/music_list.merged.xml
contents/data_mods/fblen/data_op3/sound/music/M_T0169_fengbeimusicx/
```

该包使用已实测可运行的 clamp88/track-index-shifted Fengbei XML，`validate_song.py`：`PASS`，`errors: 0`，`warnings: 0`。它用于验证 XSB interface 失败是否由改短 bank name 导致。

后续测试反馈：`fb25mix` 仍然无预览，进歌仍卡死。log 关键行：

```text
Class_Soundbank::Load: ... data_Op3/sound/music/M_L0104_fengbei/M_L0104_fengbei_pre.xsb
SoundCtrl: Load wave=data_Op3/sound/music/M_L0104_fengbei/M_L0104_fengbei.xwb
SoundCtrl: Load sound = data_Op3/sound/music/M_L0104_fengbei/M_L0104_fengbei.xsb
Class_Soundbank::Load: ... data_Op3/sound/music/M_L0104_fengbei/M_L0104_fengbei.xsb
```

未再出现 `cannot open`，因此路径已经命中。`fb25mix` 排除了“小写 list root + 大写资源目录”组合问题；当前最强假设仍是 `M_L0104_fengbei` 的 XSB 内容不被游戏接受。下一步应测试 `fblen`，即 `M_T0169_fengbeimusicx` 等长 basename 包。

后续测试反馈：`fblen` 失败。log 显示：

```text
Class_Soundbank::Load: ... data_Op3/sound/music/M_T0169_fengbeimusicx/M_T0169_fengbeimusicx_pre.xsb
SoundCtrl: Load wave=data_Op3/sound/music/M_T0169_fengbeimusicx/M_T0169_fengbeimusicx.xwb
SoundCtrl: Load sound = data_Op3/sound/music/M_T0169_fengbeimusicx/M_T0169_fengbeimusicx.xsb
Class_Soundbank::Load: ... data_Op3/sound/music/M_T0169_fengbeimusicx/M_T0169_fengbeimusicx.xsb
```

等长 basename 未解决 XSB interface 失败。因此问题不只是 bank name 长度，而是当前 `patch_bank_names.py` 只修改可见字符串，未重建 XSB 内部未知表，生成的新 bank name XSB 仍不被游戏接受。

随后测试 `fbalias`：

```text
work/lf_fengbei_add_alias_marigold
```

该包在 `music_list.merged.xml` 里追加重复 basename：

```text
basename: M_T0168_marigoldjazzy
title:    Fengbei Alias Test
index:    595
```

资源使用已验证能加载的原名 `M_T0168_marigoldjazzy` Soundbank。测试反馈：

- `Fengbei Alias Test` 不显示。
- 原 Marigold 入口的预览、进歌、音乐和谱面正常。

结论：

- 重复 basename 的追加条目不会作为新曲显示，不能用它绕过新增曲标题问题。
- 未改名的 `M_T0168_marigoldjazzy` XSB 仍可正常加载，再次确认失败点是新 basename 的 XSB 生成。

已生成下一轮反向测试包：

```text
work/lf_fengbei_add_filenameonly
```

mod 名：

```text
fbfn
```

可见标题：

```text
Fengbei Filename Test
```

该包使用新曲表 basename 和新文件路径：

```text
M_T0169_filenameonly
```

但 `.xsb/.xwb` 内部 bank name 故意不改，仍保持：

```text
M_T0168_marigoldjazzy
M_T0168_marigoldjazzy_pre
```

测试目的：确认游戏是否真正要求 XSB 内部 bank name 与文件路径 basename 一致。如果 `fbfn` 可以预览/游玩，说明内部 bank name 可以不匹配，下一步可使用“新文件名 + 原内部 bank name”的方案继续新增曲；如果仍失败，说明游戏需要 XSB 内部表与新路径全链路一致，必须找到正式生成 XSB 的方法，而不能靠字符串 patch。

后续测试反馈：`fbfn` 有预览，进入游玩音乐和谱面正常，但 title 区域仍显示 `nowloading`。log 中没有 Soundbank 失败，音频加载为：

```text
SoundCtrl: Load wave=data_Op3/sound/music/M_T0169_filenameonly/M_T0169_filenameonly.xwb
SoundCtrl: Load sound = data_Op3/sound/music/M_T0169_filenameonly/M_T0169_filenameonly.xsb
```

同时反复出现：

```text
afpu-render: get_bitmap_info[ms0595_s] can not find.
imagefs: cannot open '/data/jacket/jkms_l/afp_jkms0595_l.ifs'
```

因此当前结论：

- 新文件名 + 原内部 bank name 可以正常加载预览和主音频。
- `nowloading` 很可能来自 `index=595` 缺少 jacket/select 资源，而不是 music title 文本本身。

已给 `fbfn` 补充 0595 jacket 测试资源：

```text
data_mods/fbfn/jacket/jkms_l/afp_jkms0595_l.ifs
data_mods/fbfn/jacket/jkms_s/afp_jkms059_s_ifs/jk0595_s.png
data_mods/fbfn/jacket/jkms_s/afp_jkms059_s_ifs/ms0595_s.png
```

这些文件暂时复制自 Omni 的 `0477` jacket 资源，仅用于确认缺 jacket 是否导致 `nowloading`。
