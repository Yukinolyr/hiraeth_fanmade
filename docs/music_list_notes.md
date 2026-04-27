# music_list.xml 分析笔记

本文记录 `reference/music_list.xml` 的只读分析结果。

## 基本信息

`music_list.xml` 文件头：

```xml
<?xml version='1.0' encoding='Shift_JIS'?>
<music_list __type='void' revision='22621M' release_code='2024123100'>
```

观察结果：

- 编码：`Shift_JIS`
- 根节点：`music_list`
- `revision`：`22621M`
- `release_code`：`2024123100`
- `music_spec` 数量：`544`

Python 标准库的 `ElementTree.parse()` 不能直接解析该文件声明的多字节编码，会报：

```text
ValueError: multi-byte encodings are not supported
```

当前脚本采用的方式是：

1. 读取 bytes。
2. 用 `shift_jis` 解码为字符串。
3. 将 XML declaration 替换为普通 Unicode XML declaration。
4. 用 `ElementTree.fromstring()` 解析。

复现命令：

```bash
python3 scripts/inspect_music_list.py reference/music_list.xml M_C0047_chopin_etude10_4 M_T0168_marigoldjazzy M_C0064_hungary06
```

## 样本条目

| index | basename | title | artist | levels N/H/E/R | bgm | key | start | real_start |
|---:|---|---|---|---|---:|---:|---|---|
| 319 | `M_C0064_hungary06` | ハンガリー舞曲第6番 | ブラームス | 4/7/11/13 | 0 | 0 | 2019-12-02 04:00 | 2019-12-02 04:00 |
| 324 | `M_C0047_chopin_etude10_4` | エチュード Op.10-4 | ショパン | 5/8/12/15 | 0 | 0 | 2019-12-02 04:00 | 2021-07-01 10:00 |
| 496 | `M_T0168_marigoldjazzy` | Marigold (Jazzy Hip-Hop Remix) | SHORTCUTS RMX by ROMANTIC PRODUCTION | 3/6/11/12 | -2 | -3 | 2022-08-18 10:00 | 2022-08-18 10:00 |

## music_spec 常见字段

已观察到的主要字段：

- `basename`：内部曲目 basename，格式使用大写前缀，例如 `M_C0047_chopin_etude10_4`。
- `title` / `title_kana`：曲名和假名。
- `artist` / `artist_kana`：艺术家和假名。
- `category_flag` / `primary_category`：分类相关字段。
- `bemani_flag` / `bemani_category`：BEMANI 分类相关字段。
- `add_ver`：追加版本。
- `level_normal` / `level_hard` / `level_extreme` / `level_real`：四个难度等级。
- `volume_bgm`：背景音量修正。
- `volume_key`：键音音量修正。
- `start_date` / `end_date` / `expiration_date`：普通开放时间。
- `real_start_date` / `real_end_date` / `real_release_code`：Real 难度相关开放信息。
- `force_unlock_date` / `real_force_unlock_date`：强制解锁日期。
- `tag_list_data`：标签 id 列表；当前三个样本条目为空。

## 与文件名和 bank name 的关系

三首样本中，`music_list.xml` 的 `basename` 使用大写前缀：

- `M_C0047_chopin_etude10_4`
- `M_C0064_hungary06`
- `M_T0168_marigoldjazzy`

对应文件夹和文件名使用小写前缀：

- `m_c0047_chopin_etude10_4`
- `m_c0064_hungary06`
- `m_t0168_marigoldjazzy`

对应 `.xwb/.xsb` 内部 bank name 使用 `music_list.xml` 的大写形式：

- `M_C0047_chopin_etude10_4`
- `M_C0064_hungary06`
- `M_T0168_marigoldjazzy`

因此，自制曲若要形成完整可识别条目，至少需要考虑三处 basename 的一致关系：

| 位置 | 形式 |
|---|---|
| 文件夹/文件名 | 小写 `m_...` |
| `music_list.xml` 的 `basename` | 大写 `M_...` |
| `.xsb/.xwb` 内部 bank name | 大写 `M_...` |

## 对自制曲的影响

当前已经能在 `work/` 内生成：

- 自制 `.xwb`
- bank name 同步后的 `.xsb`
- 可验证的 XML 谱面副本

但要让曲目像正式歌曲一样出现在列表中，还需要研究如何安全生成或修改 `music_list.xml` 的 `music_spec` 条目。

注意：

- 不应直接修改原始游戏目录中的 `music_list.xml`。
- 后续只应在 `work/` 中复制一份 `music_list.xml` 做条目生成实验。
- 需要保留 `Shift_JIS` 编码，否则游戏或工具链可能无法按原格式读取。

## 待确认项

- `index` 是否必须唯一且连续。
- 新增条目是否需要同步其他数据库或缓存文件。
- `category_flag`、`bemani_flag`、`unlock_type` 等字段的精确含义。
- `volume_bgm` / `volume_key` 是否直接影响实际播放混音。

## work 内新增条目实验

已新增脚本：

```bash
python3 scripts/create_music_list_entry.py reference/music_list.xml work/music_list_test/music_list.xml \
  --template M_T0168_marigoldjazzy \
  --basename M_F0002_closeup_test \
  --title CloseupTest \
  --artist Fanmade \
  --levels 3/6/9/12
```

脚本行为：

- 读取 `reference/music_list.xml`。
- 复制一个已有 `music_spec` 作为模板。
- 修改 `basename`、`title`、`title_kana`、`artist`、`artist_kana` 和等级。
- 生成新的 `work/music_list_test/music_list.xml`。
- 不修改 `reference/music_list.xml`。

本次结果：

- 输出文件：`work/music_list_test/music_list.xml`
- 原始 `music_spec_count`：`544`
- 新 `music_spec_count`：`545`
- 新条目 index：`595`
- 新 basename：`M_F0002_closeup_test`
- 标题：`CloseupTest`
- 艺术家：`Fanmade`
- 等级：`3/6/9/12`

查询验证：

```bash
python3 scripts/inspect_music_list.py work/music_list_test/music_list.xml M_F0002_closeup_test
```

输出摘要：

| index | basename | title | artist | levels N/H/E/R | bgm | key |
|---:|---|---|---|---|---:|---:|
| 595 | `M_F0002_closeup_test` | CloseupTest | Fanmade | 3/6/9/12 | -2 | -3 |

限制：

- 当前只是生成可解析的 `music_list.xml` 副本。
- 尚未确认游戏是否只依赖此文件显示曲目。
- 尚未同步封面、排序、解锁、缓存或其他数据库。
- 输出使用 Shift_JIS 编码，但格式化后的空白和原文件不完全一致；如后续需要最小 diff，应改为保留原 XML 片段风格的生成方式。

## m_l 前缀实验

根据后续观察，`m_c`、`m_t` 等前缀可能与游戏内歌曲分类/搜索标签有关。`m_f` 只是项目早期为避免撞名选择的 fanmade 测试前缀，不是已确认的官方分类。下一轮替换测试改用 `m_l`：

```bash
python3 scripts/create_music_list_entry.py reference/music_list.xml work/music_list_test_l/music_list.xml --template M_T0168_marigoldjazzy --basename M_L0002_closeup_test --title CloseupTest --artist Fanmade --levels 3/6/9/12
python3 scripts/inspect_music_list.py work/music_list_test_l/music_list.xml M_L0002_closeup_test
```

输出摘要：

| index | basename | title | artist | levels N/H/E/R | bgm | key |
|---:|---|---|---|---|---:|---:|
| 595 | `M_L0002_closeup_test` | CloseupTest | Fanmade | 3/6/9/12 | -2 | -3 |

结论：项目内 `music_list.xml` 副本已经能生成并查询 `M_L0002_closeup_test` 条目。是否会进入游戏内对应分类，需要在测试副本中验证。
