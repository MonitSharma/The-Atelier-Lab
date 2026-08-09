from config import load_config


def render_items(items, overrides=None):
    config = load_config(overrides)
    selected = items[: config["limit"]]
    return [item["name"] for item in selected if item.get("enabled", True)]
