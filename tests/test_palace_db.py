import os
import json
import tempfile
import pytest
from mempalace.config import MempalaceConfig


def test_remote_config_defaults():
    """chroma_host defaults to None; port to 8000; ssl to False."""
    cfg = MempalaceConfig(config_dir=tempfile.mkdtemp())
    assert cfg.chroma_host is None
    assert cfg.chroma_port == 8000
    assert cfg.chroma_ssl is False


def test_remote_config_from_file():
    """Config file values are read correctly."""
    tmpdir = tempfile.mkdtemp()
    with open(os.path.join(tmpdir, "config.json"), "w") as f:
        json.dump({"chroma_host": "m1mini.local", "chroma_port": 9000, "chroma_ssl": True}, f)
    cfg = MempalaceConfig(config_dir=tmpdir)
    assert cfg.chroma_host == "m1mini.local"
    assert cfg.chroma_port == 9000
    assert cfg.chroma_ssl is True


def test_remote_config_env_vars_override_file():
    """Env vars take priority over config file values."""
    tmpdir = tempfile.mkdtemp()
    with open(os.path.join(tmpdir, "config.json"), "w") as f:
        json.dump({"chroma_host": "file-host", "chroma_port": 1234}, f)
    os.environ["MEMPALACE_CHROMA_HOST"] = "env-host"
    os.environ["MEMPALACE_CHROMA_PORT"] = "5678"
    os.environ["MEMPALACE_CHROMA_SSL"] = "true"
    try:
        cfg = MempalaceConfig(config_dir=tmpdir)
        assert cfg.chroma_host == "env-host"
        assert cfg.chroma_port == 5678
        assert cfg.chroma_ssl is True
    finally:
        del os.environ["MEMPALACE_CHROMA_HOST"]
        del os.environ["MEMPALACE_CHROMA_PORT"]
        del os.environ["MEMPALACE_CHROMA_SSL"]


def test_remote_config_env_host_none_when_empty_string():
    """Empty string env var is treated as not set (returns None)."""
    os.environ["MEMPALACE_CHROMA_HOST"] = ""
    try:
        cfg = MempalaceConfig(config_dir=tempfile.mkdtemp())
        assert cfg.chroma_host is None
    finally:
        del os.environ["MEMPALACE_CHROMA_HOST"]


def test_remote_config_invalid_port_raises():
    """Non-integer MEMPALACE_CHROMA_PORT raises ValueError."""
    os.environ["MEMPALACE_CHROMA_PORT"] = "not-a-port"
    try:
        cfg = MempalaceConfig(config_dir=tempfile.mkdtemp())
        with pytest.raises(ValueError, match="MEMPALACE_CHROMA_PORT"):
            _ = cfg.chroma_port
    finally:
        del os.environ["MEMPALACE_CHROMA_PORT"]
