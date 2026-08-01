import json
import pytest
from pathlib import Path
from unittest.mock import patch
import config as cfg


def test_load_config_returns_defaults_when_no_file_exists(tmp_path):
    config_path = tmp_path / "config.json"
    with patch("config.CONFIG_PATH", config_path):
        result = cfg.load_config()
    assert result["default_quality"] == "320"
    assert result["download_dir"] == str(Path("~/Music/Downloads").expanduser())


def test_load_config_reads_existing_file(tmp_path):
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps({"download_dir": "/custom/path", "default_quality": "192"}))
    with patch("config.CONFIG_PATH", config_path):
        result = cfg.load_config()
    assert result["download_dir"] == "/custom/path"
    assert result["default_quality"] == "192"


def test_load_config_merges_defaults_with_partial_config(tmp_path):
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps({"download_dir": "/custom/path"}))
    with patch("config.CONFIG_PATH", config_path):
        result = cfg.load_config()
    assert result["download_dir"] == "/custom/path"
    assert result["default_quality"] == "320"


def test_load_config_handles_corrupted_json(tmp_path):
    config_path = tmp_path / "config.json"
    config_path.write_text("invalid json content {{{")
    with patch("config.CONFIG_PATH", config_path):
        result = cfg.load_config()
    assert result["default_quality"] == "320"
    assert result["download_dir"] == str(Path("~/Music/Downloads").expanduser())


@pytest.mark.parametrize("non_dict_val", ["null", "[]", '"string"', "123", "true"])
def test_load_config_handles_non_dict_json(tmp_path, non_dict_val):
    config_path = tmp_path / "config.json"
    config_path.write_text(non_dict_val)
    with patch("config.CONFIG_PATH", config_path):
        result = cfg.load_config()
    assert result["default_quality"] == "320"
    assert result["download_dir"] == str(Path("~/Music/Downloads").expanduser())


def test_save_config_writes_json(tmp_path):
    config_path = tmp_path / "config.json"
    with patch("config.CONFIG_PATH", config_path):
        cfg.save_config({"download_dir": "/new/path", "default_quality": "128"})
    data = json.loads(config_path.read_text())
    assert data["download_dir"] == "/new/path"
    assert data["default_quality"] == "128"


def test_save_config_creates_parent_dirs(tmp_path):
    config_path = tmp_path / "nested" / "deep" / "config.json"
    with patch("config.CONFIG_PATH", config_path):
        cfg.save_config({"download_dir": "/x", "default_quality": "320"})
    assert config_path.exists()
