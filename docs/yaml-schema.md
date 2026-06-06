# 剧本 YAML Schema 定义文档

## 一、设计目标

本 Schema 用于将小说文本转换为结构化剧本。v0.3 在原有角色、场景、动作、对白结构基础上，进一步增强两个方向：

1. 按章节组织剧本，方便作者回溯小说章节与剧本场景的对应关系；
2. 将台词单独拉出索引，方便作者快速检查人物对白、演员台词和语气提示。

v0.3 推荐使用：

```yaml
schema_version: "1.1"
```

## 二、基础结构

```yaml
schema_version: "1.1"
title: "剧本标题"
source:
  type: "novel"
  chapters:
    - id: "chapter_001"
      title: "第一章 初入县衙"
logline: "一句话故事梗概"
theme: "故事主题"
adaptation_style: "忠于原文"

characters:
  - id: "char_001"
    name: "林安"
    role: "主角"
    description: "初入县衙的年轻县令"
    goal: "查清案件真相"

chapter_scripts:
  - chapter_id: "chapter_001"
    chapter_title: "第一章 初入县衙"
    summary: "林安初入县衙，准备审案。"
    scene_ids:
      - "scene_001"

scenes:
  - id: "scene_001"
    source_chapter: "chapter_001"
    title: "初入县衙"
    location: "青石县县衙"
    time: "清晨"
    characters:
      - "char_001"
    summary: "林安进入县衙，接手案件。"
    action:
      - "林安走进县衙，堂前站着两排衙役。"
    dialogue:
      - id: "dialogue_001"
        speaker: "char_001"
        speaker_name: "林安"
        line: "那就从第一桩开始。"
        emotion: "平静"
    transition: "切至下一场"

dialogue_index:
  - id: "dialogue_001"
    chapter_id: "chapter_001"
    chapter_title: "第一章 初入县衙"
    scene_id: "scene_001"
    speaker: "char_001"
    speaker_name: "林安"
    line: "那就从第一桩开始。"
    emotion: "平静"
```

## 三、字段说明

| 字段 | 类型 | 是否必填 | 说明 |
|---|---|---|---|
| schema_version | string | 是 | Schema 版本，v0.3 推荐 1.1 |
| title | string | 是 | 剧本标题 |
| source | object | 是 | 原小说来源信息 |
| source.type | string | 是 | 来源类型，当前为 novel |
| source.chapters | list | 是 | 原小说章节列表 |
| logline | string | 否 | 一句话故事梗概 |
| theme | string | 否 | 主题说明 |
| adaptation_style | string | 否 | 改编风格，如忠于原文、增强戏剧冲突化、口语化 |
| characters | list | 是 | 角色列表 |
| characters[].id | string | 是 | 角色 ID，如 char_001 |
| characters[].name | string | 是 | 角色名称 |
| characters[].role | string | 是 | 角色定位 |
| characters[].description | string | 是 | 角色简介 |
| characters[].goal | string | 否 | 角色目标 |
| chapter_scripts | list | 否 | 按章节组织后的剧本索引 |
| chapter_scripts[].chapter_id | string | 是 | 章节 ID |
| chapter_scripts[].chapter_title | string | 是 | 章节标题 |
| chapter_scripts[].summary | string | 否 | 章节摘要 |
| chapter_scripts[].scene_ids | list | 是 | 本章对应的场景 ID 列表 |
| scenes | list | 是 | 场景列表 |
| scenes[].id | string | 是 | 场景 ID |
| scenes[].source_chapter | string | 是 | 来源章节 ID |
| scenes[].title | string | 是 | 场景标题 |
| scenes[].location | string | 是 | 场景地点 |
| scenes[].time | string | 是 | 场景时间 |
| scenes[].characters | list | 是 | 本场出场角色 ID |
| scenes[].summary | string | 是 | 本场剧情摘要 |
| scenes[].action | list | 是 | 动作、环境、旁白说明 |
| scenes[].dialogue | list | 是 | 本场对白 |
| scenes[].dialogue[].id | string | 否 | 对白 ID |
| scenes[].dialogue[].speaker | string | 是 | 说话角色 ID |
| scenes[].dialogue[].speaker_name | string | 否 | 说话角色名称 |
| scenes[].dialogue[].line | string | 是 | 台词内容 |
| scenes[].dialogue[].emotion | string | 否 | 情绪或语气 |
| scenes[].transition | string | 是 | 转场说明 |
| dialogue_index | list | 否 | 全局台词索引 |
| dialogue_index[].id | string | 是 | 对白 ID |
| dialogue_index[].chapter_id | string | 是 | 所属章节 ID |
| dialogue_index[].chapter_title | string | 否 | 所属章节标题 |
| dialogue_index[].scene_id | string | 是 | 所属场景 ID |
| dialogue_index[].speaker | string | 是 | 说话角色 ID |
| dialogue_index[].speaker_name | string | 是 | 说话角色名称 |
| dialogue_index[].line | string | 是 | 台词内容 |
| dialogue_index[].emotion | string | 否 | 情绪或语气 |

## 四、v0.3 新增设计原因

### 1. 为什么增加 chapter_scripts？

v0.1/v0.2 主要以 scenes 为剧本主体，但用户在编辑剧本时仍然需要知道每个场景来自哪个小说章节。`chapter_scripts` 用于建立“章节 → 场景”的索引关系，让作者可以按章节查看改编结果。

### 2. 为什么增加 dialogue_index？

台词是剧本编辑中的重点内容。虽然每个场景中已有 dialogue 字段，但作者如果想集中检查所有人物台词，需要一个独立列表。`dialogue_index` 将所有台词单独拉出，并标明章节、场景、人物和情绪，便于后续排练、配音、修改和统计。

### 3. 为什么增加 adaptation_style？

不同作者对改编结果的期待不同。有些作者希望忠于原文，有些作者希望增强戏剧冲突，还有些作者希望台词更口语化。`adaptation_style` 用于记录本次生成所采用的改编风格，便于用户理解和复现生成结果。

### 4. 为什么保留 scenes.dialogue？

`dialogue_index` 是全局索引，而 `scenes.dialogue` 是场景内部内容。二者作用不同：前者方便集中查看，后者方便在场景语境中编辑。两者同时存在，可以兼顾剧本结构完整性和台词管理效率。

## 五、兼容性说明

为了兼容 v0.2，系统仍支持没有 `chapter_scripts` 和 `dialogue_index` 的 YAML，但会在校验结果中给出建议提示。v0.3 推荐生成完整的 `schema_version: "1.1"` 结构。
