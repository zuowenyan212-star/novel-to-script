from backend.script_generator import generate_script_yaml
from backend.yaml_validator import validate_yaml_text


SAMPLE_TEXT = """
第一章 初入县衙
林安第一次走进青石县县衙时，天色刚亮。
周伯低声说道：“大人，今日有三桩案子要审。”
林安说道：“那就从第一桩开始。”

第二章 堂前争执
商人跪在堂下，说道：“大人，就是他偷了我的银子。”
年轻人反驳道：“我没有。”

第三章 真相浮现
周伯说道：“大人明察秋毫。”
林安说道：“诬告他人，罪加一等。”
"""


def test_v03_local_generation_contains_chapter_scripts_and_dialogue_index():
    result = generate_script_yaml(
        SAMPLE_TEXT,
        provider="local",
        model="local-rule",
        adaptation_style="faithful",
    )
    assert result["success"] is True
    data = result["data"]
    assert data["schema_version"] == "1.1"
    assert "chapter_scripts" in data
    assert "dialogue_index" in data
    assert len(data["chapter_scripts"]) == 3
    assert len(data["dialogue_index"]) >= 1


def test_v03_dramatic_style_is_recorded():
    result = generate_script_yaml(
        SAMPLE_TEXT,
        provider="local",
        model="local-rule",
        adaptation_style="dramatic",
    )
    assert result["success"] is True
    assert result["data"]["adaptation_style"] == "增强戏剧冲突化"


def test_v03_validator_accepts_dialogue_index():
    result = generate_script_yaml(SAMPLE_TEXT, provider="local", model="local-rule")
    validation = validate_yaml_text(result["yaml"])
    assert validation["valid"] is True
