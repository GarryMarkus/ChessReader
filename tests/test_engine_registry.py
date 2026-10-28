"""
Unit tests for EngineRegistry, UCI engine probing, and engine registration.
"""

import os
import shutil
import tempfile
import pytest

from chess_reader.engine.engine_registry import EngineRegistry


def test_engine_registry_discovery():
    temp_dir = tempfile.mkdtemp()
    try:
        reg = EngineRegistry(config_dir=temp_dir)
        engines = reg.list_engines()
        assert len(engines) >= 1
        active = reg.get_active_engine()
        assert active is not None
        assert "stockfish" in active["path"].lower()
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_engine_registry_probe_invalid_file():
    temp_dir = tempfile.mkdtemp()
    invalid_script = os.path.join(temp_dir, "fake_engine.sh")
    with open(invalid_script, "w") as f:
        f.write("#!/bin/sh\necho not an engine\n")
    os.chmod(invalid_script, 0o755)

    try:
        reg = EngineRegistry(config_dir=temp_dir)
        with pytest.raises(ValueError):
            reg.add_engine(invalid_script)
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
