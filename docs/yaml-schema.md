# 剧本 YAML Schema 设计文档

## 一、设计目标

本 Schema 用于将 3 个章节以上的小说文本转换为结构化剧本。设计重点是让小说作者快速获得一份可读、可编辑、可继续打磨的剧本初稿。

小说以章节叙事为主，剧本以场次推进。因此本 Schema 采用：

```text
剧本信息 → 来源章节 → 角色表 → 场景列表 → 动作与对白
```

的层级结构。

## 二、Schema 示例

```yaml
schema_version: "1.0"
title: "剧本标题"
source:
  type: "novel"
  chapters:
    - id: "chapter_001"
      title: "第一章 雨夜重逢"
logline: "一句话故事梗概"
theme: "故事主题"
characters:
  - id: "char_001"
    name: "林舟"
    role: "男主角"
    description: "沉默冷静的调查记者"
    goal: "查清旧案真相"
scenes:
  - id: "scene_001"
    source_chapter: "chapter_001"
    title: "雨夜咖啡馆"
    location: "街边咖啡馆"
    time: "夜晚"
    characters:
      - "char_001"
    summary: "林舟在雨夜见到多年未见的旧友。"
    action:
      - "林舟推门走进咖啡馆，雨水顺着伞尖滴落。"
    dialogue:
      - speaker: "char_001"
        line: "我回来了。"
        emotion: "克制"
    transition: "切至旧照片特写"
```

## 三、字段说明

| 字段 | 类型 | 是否必填 | 说明 |
|---|---|---|---|
| schema_version | string | 是 | Schema 版本，方便后续升级 |
| title | string | 是 | 剧本标题 |
| source | object | 是 | 小说来源信息 |
| source.type | string | 是 | 来源类型，当前固定为 novel |
| source.chapters | list | 是 | 原小说章节列表 |
| logline | string | 否 | 一句话故事梗概 |
| theme | string | 否 | 故事主题 |
| characters | list | 是 | 角色表 |
| characters[].id | string | 是 | 角色唯一 ID |
| characters[].name | string | 是 | 角色姓名 |
| characters[].role | string | 是 | 角色定位 |
| characters[].description | string | 是 | 角色简介 |
| characters[].goal | string | 否 | 角色目标 |
| scenes | list | 是 | 剧本场次列表 |
| scenes[].id | string | 是 | 场景唯一 ID |
| scenes[].source_chapter | string | 是 | 来源章节 ID |
| scenes[].title | string | 是 | 场景标题 |
| scenes[].location | string | 是 | 场景地点 |
| scenes[].time | string | 是 | 场景时间 |
| scenes[].characters | list | 是 | 本场出场角色 ID 列表 |
| scenes[].summary | string | 是 | 本场摘要 |
| scenes[].action | list | 是 | 动作、环境和旁白说明 |
| scenes[].dialogue | list | 是 | 对白列表 |
| dialogue[].speaker | string | 是 | 说话角色 ID |
| dialogue[].line | string | 是 | 台词内容 |
| dialogue[].emotion | string | 否 | 情绪或语气 |
| scenes[].transition | string | 否 | 转场说明 |

## 四、设计原因

### 1. 为什么使用 schema_version？

剧本结构后续可能扩展，例如增加分镜头、道具、情绪曲线等字段。版本号可以让旧数据和新数据共存。

### 2. 为什么保留 source.chapters？

小说改编需要追溯来源。保留章节 ID 和标题后，作者可以知道某一场戏来自哪一章，便于二次修改。

### 3. 为什么 characters 独立存放？

角色信息统一维护，可以避免同一人物在不同场景里名称不一致，也方便后续扩展角色关系图谱。

### 4. 为什么以 scenes 为主体？

剧本创作的基本单位是“场”。小说按章节推进，但剧本需要按场景组织，所以 scenes 是本 Schema 的核心。

### 5. 为什么 action 和 dialogue 分离？

小说中的环境描写、心理描写、动作描写和人物对白经常混在一起。剧本需要把动作与对白分开，方便演员、编剧和后期继续编辑。

### 6. 为什么 dialogue.speaker 使用角色 ID？

角色 ID 可以保证引用稳定，避免同名、简称或别名造成混乱。

### 7. 为什么加入 emotion 和 transition？

emotion 可以帮助理解对白语气，transition 用于描述场景切换，增强剧本的可拍摄性。

### 8. 为什么 MVP 不做更复杂的专业剧本格式？

MVP 的目标是快速生成可编辑初稿，而不是替代专业编剧软件。字段越复杂，AI 越容易输出错误。因此当前 Schema 优先保证清晰、稳定、易校验。
