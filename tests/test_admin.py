from pathlib import Path

from grokx.admin import set_clearance_in_toml


def test_set_clearance_replaces_existing_value_and_keeps_user_agent(tmp_path):
    config_path = tmp_path / "config.toml"
    config_path.write_text(
        "[proxy.clearance]\n"
        'cf_clearance = "old-value"\n'
        'user_agent = "old-agent"\n'
    )

    set_clearance_in_toml(config_path, cf_clearance="new-value", user_agent=None)

    content = config_path.read_text()
    assert 'cf_clearance = "new-value"' in content
    assert 'user_agent = "old-agent"' in content


def test_set_clearance_can_replace_user_agent(tmp_path):
    config_path = tmp_path / "config.toml"
    config_path.write_text(
        "[proxy.clearance]\n"
        'cf_clearance = "old-value"\n'
        'user_agent = "old-agent"\n'
    )

    set_clearance_in_toml(config_path, cf_clearance="new-value", user_agent="new-agent")

    content = config_path.read_text()
    assert 'cf_clearance = "new-value"' in content
    assert 'user_agent = "new-agent"' in content
