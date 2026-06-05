# YAML Schema 设计文档

## 设计目标

该 Schema 用于把小说内容拆解为可编辑、可校验、可继续扩展的剧本初稿。结构重点围绕“来源章节、角色、场景、动作、对白”展开，便于作者追溯原文、调整人物关系和继续打磨场次。

## 顶层结构

```yaml
schema_version: "1.0"
title: "剧本标题"
source:
  type: "novel"
  chapters: []
logline: "一句话故事梗概"
theme: "故事主题"
metadata: {}
characters: []
scenes: []
```

## 字段说明

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `schema_version` | string | 是 | 标记结构版本，方便后续升级兼容。 |
| `title` | string | 是 | 剧本标题，用于页面展示与下载文件命名。 |
| `source` | object | 是 | 记录改编来源。当前 `type` 固定为 `novel`。 |
| `source.chapters` | list | 是 | 输入小说章节清单，包含章节 ID、标题和字数。 |
| `logline` | string | 是 | 一句话概括故事核心。 |
| `theme` | string | 是 | 记录主题与改编策略，避免偏离原作核心。 |
| `metadata` | object | 否 | 记录生成参数、时间和生成器类型。 |
| `characters` | list | 是 | 独立角色表，供场景与对白稳定引用。 |
| `scenes` | list | 是 | 剧本主体，按可拍摄场景组织。 |

## 角色结构

```yaml
characters:
  - id: "char_001"
    name: "林舟"
    role: "主角"
    description: "沉默冷静的调查记者"
    goal: "查清旧案真相"
```

角色使用稳定 ID，而不是只使用姓名。原因是姓名可能重复、改名或有别称，ID 更适合程序校验和后续编辑。

## 场景结构

```yaml
scenes:
  - id: "scene_001"
    source_chapter: "chapter_001"
    title: "雨夜咖啡馆"
    location: "街边咖啡馆"
    time: "夜晚"
    characters:
      - "char_001"
      - "char_002"
    summary: "林舟在雨夜见到多年未见的苏晚。"
    action:
      - "林舟推门走进咖啡馆，雨水顺着伞尖滴落。"
    dialogue:
      - speaker: "char_001"
        line: "我回来了。"
        emotion: "克制"
    transition: "切至旧照片特写。"
```

场景按影视剧本习惯组织，包含时间、地点、出场人物、动作、对白和转场。`source_chapter` 保留章节来源，方便作者回到原文核对。

## 校验规则

- YAML 必须能被解析为对象。
- 顶层必须包含 `schema_version`、`title`、`source`、`logline`、`theme`、`characters`、`scenes`。
- `source.chapters`、`characters`、`scenes` 必须是非空列表。
- 章节 ID、角色 ID、场景 ID 不允许重复。
- 场景引用的 `source_chapter` 必须存在。
- 场景 `characters` 必须引用已有角色 ID。
- 对白必须包含 `speaker`、`line`、`emotion`。
- 对白 `speaker` 建议使用角色 ID，避免姓名歧义。

## 设计原因

`source` 保留小说章节来源，使改编结果可追溯；`characters` 独立存放人物，避免每个场景重复写角色描述；`scenes` 作为主体更贴近影视剧本创作流程；`action` 和 `dialogue` 分离，方便后续单独修改动作或台词；`emotion` 给演员和作者提供语气提示；`transition` 让输出结果更接近可拍摄分镜。

