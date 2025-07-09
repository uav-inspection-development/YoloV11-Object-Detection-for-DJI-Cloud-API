import importlib

from src import naming_config
import src.chinese_name_list as cnl


def test_language_switch():
    naming_config.set_language('en')
    importlib.reload(cnl)
    assert cnl.Visible_type['yyzd'] == 'obstruction'
    naming_config.set_language('zh')
    importlib.reload(cnl)
    assert cnl.Visible_type['yyzd'] == '遮挡'
