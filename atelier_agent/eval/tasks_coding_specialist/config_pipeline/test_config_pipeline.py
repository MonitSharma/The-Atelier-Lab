from config import DEFAULTS, load_config
from render import render_items


def test_load_config_returns_copy_and_applies_overrides():
    assert load_config({"limit": 2}) == {"limit": 2, "enabled": True}
    assert DEFAULTS == {"limit": 3, "enabled": True}


def test_render_items_filters_and_limits_across_modules():
    items = [
        {"name": "a", "enabled": True},
        {"name": "b", "enabled": False},
        {"name": "c", "enabled": True},
        {"name": "d", "enabled": True},
    ]
    assert render_items(items, {"limit": 2}) == ["a", "c"]
