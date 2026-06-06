from backend.script_generator import generate_script_yaml


TEXT_WITH_ACTION_SUFFIXES = """
第一章 初入县衙
王林苦笑说道：“案子没有那么简单。”
台上朗声说道：“肃静！”
王林看着卷宗，发现证词里有矛盾。

第二章 堂前争执
李秋沉声问道：“你昨夜到底去了哪里？”
一眼沉声说道：“这不是人名。”
王林说道：“我只相信证据。”

第三章 真相浮现
李秋说道：“原来银袋藏在车底。”
王林说道：“真相已经清楚。”
"""


def test_local_name_extraction_strips_action_suffixes():
    result = generate_script_yaml(
        TEXT_WITH_ACTION_SUFFIXES,
        provider="local",
        model="local-rule",
        adaptation_style="faithful",
    )
    assert result["success"] is True
    names = [item["name"] for item in result["data"]["characters"]]

    assert "王林" in names
    assert "李秋" in names
    assert "王林苦笑" not in names
    assert "台上朗声" not in names
    assert "一眼沉声" not in names
    assert "台上" not in names
    assert "一眼" not in names
