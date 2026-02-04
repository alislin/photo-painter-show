#!/usr/bin/env python3
# -*- coding:utf-8 -*-
import pytest
import tempfile
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import (
    load_config,
    get_schedule,
    get_image_url,
    get_display_model,
    get_output_dir,
    get_display_script_path,
)


class TestGetDisplayScriptPath:
    """Tests for get_display_script_path function"""

    def test_get_display_script_path_exists(self):
        """Test when display_script_path is configured"""
        config = {
            "schedule": ["05:00", "13:00"],
            "image_url": "https://example.com/pic.jpg",
            "display_model": "epd7in3e",
            "work_dir": "/home/pi/project",
            "output_dir": "/home/pi/project/output",
            "display_script_path": "/external/path/display_picture.py",
        }
        assert get_display_script_path(config) == "/external/path/display_picture.py"

    def test_get_display_script_path_empty(self):
        """Test when display_script_path is not configured (empty string)"""
        config = {
            "schedule": ["05:00"],
            "image_url": "https://example.com/pic.jpg",
            "display_model": "epd7in3e",
            "work_dir": "/home/pi/project",
            "output_dir": "/home/pi/project/output",
            "display_script_path": "",
        }
        assert get_display_script_path(config) == ""

    def test_get_display_script_path_missing(self):
        """Test when display_script_path key is missing"""
        config = {
            "schedule": ["05:00"],
            "image_url": "https://example.com/pic.jpg",
            "display_model": "epd7in3e",
            "work_dir": "/home/pi/project",
            "output_dir": "/home/pi/project/output",
        }
        assert get_display_script_path(config) == ""


class TestLoadConfig:
    """Tests for load_config function"""

    def test_load_config_valid(self):
        """Test loading a valid config file"""
        config_content = """{
            "schedule": ["05:00", "13:00"],
            "image_url": "https://example.com/pic.jpg",
            "display_model": "epd7in3e",
            "work_dir": "/home/pi/project",
            "output_dir": "/home/pi/project/output",
            "display_script_path": "/external/path/display_picture.py"
        }"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write(config_content)
        try:
            config = load_config(f.name)
            assert config["schedule"] == ["05:00", "13:00"]
            assert config["display_model"] == "epd7in3e"
            assert config["display_script_path"] == "/external/path/display_picture.py"
        finally:
            os.unlink(f.name)

    def test_load_config_missing_required_key(self):
        """Test loading config with missing required key"""
        config_content = """{
            "schedule": ["05:00"],
            "image_url": "https://example.com/pic.jpg",
            "display_model": "epd7in3e"
        }"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write(config_content)
        try:
            with pytest.raises(ValueError):
                load_config(f.name)
        finally:
            os.unlink(f.name)


class TestOtherGetters:
    """Tests for other getter functions"""

    def test_get_schedule(self):
        """Test get_schedule returns list"""
        config = {"schedule": ["05:00", "13:00", "18:00"]}
        assert get_schedule(config) == ["05:00", "13:00", "18:00"]

    def test_get_image_url(self):
        """Test get_image_url returns string"""
        config = {"image_url": "https://example.com/image.jpg"}
        assert get_image_url(config) == "https://example.com/image.jpg"

    def test_get_display_model(self):
        """Test get_display_model returns string"""
        config = {"display_model": "epd7in3e"}
        assert get_display_model(config) == "epd7in3e"

    def test_get_output_dir(self):
        """Test get_output_dir returns string"""
        config = {"output_dir": "/home/pi/output"}
        assert get_output_dir(config) == "/home/pi/output"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
