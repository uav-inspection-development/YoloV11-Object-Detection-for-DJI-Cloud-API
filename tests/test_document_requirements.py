import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
THERMAL_ANALYSIS_LABELS = [
    "同类设备温差对比",
    "最高温度点故障类型分析",
    "异常温升",
    "局部过热",
    "点状温度异常",
    "线状温度异常",
    "带状温度异常",
    "片状温度异常",
    "环状温度异常",
    "二极管短路_异常低温",
]


def load_locale(language):
    with (ROOT / "src" / "locales" / f"{language}.json").open(
        encoding="utf-8"
    ) as locale_file:
        return json.load(locale_file)


def test_chinese_thermal_requirements_are_configured():
    locale = load_locale("zh")

    assert list(locale["CLASS_NAMES"]["Thermal"].values()) == THERMAL_ANALYSIS_LABELS
    assert locale["ABOUT_SECTION"]["author"] == "四川富尔曼科技有限公司"
    assert "contact" not in locale["ABOUT_SECTION"]
    assert "DL/T 664-2025" in locale["ABOUT_SECTION"]["description"]
    assert [
        locale["FAULT_CATEGORIES"]["level_1_fault"],
        locale["FAULT_CATEGORIES"]["level_2_fault"],
        locale["FAULT_CATEGORIES"]["level_3_fault"],
    ] == ["一般缺陷", "严重缺陷", "紧急缺陷"]
    assert locale["SYSTEM_INFO"]["title"] == "光伏云组件检测系统"
    assert locale["SYSTEM_INFO"]["description"] == (
        "本系统可以检测光伏面板可见光故障、红外热故障、"
        "EL隐裂故障以及其他异物入侵等问题。"
    )


def test_streamlit_ui_only_offers_thermal_images():
    web_source = (ROOT / "src" / "web.py").read_text(encoding="utf-8")

    assert (
        web_source.count(
            'available_options = [get_system_default("image_type_thermal")]'
        )
        == 2
    )
    assert "get_about_content('contact')" not in web_source


def test_default_image_is_the_requested_infrared_equipment_image():
    default_image = ROOT / "icon" / "ini.jpg"

    assert default_image.stat().st_size == 68929


def test_radio_labels_do_not_collapse_cjk_text():
    style_source = (ROOT / "src" / "ui_style.py").read_text(encoding="utf-8")

    assert '.stRadio [role="radiogroup"] > label' in style_source
    assert "width: max-content;" in style_source
    assert "word-break: keep-all;" in style_source
    assert ".stRadio > label {" not in style_source
