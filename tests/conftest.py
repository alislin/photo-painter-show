#!/usr/bin/env python3
# -*- coding:utf-8 -*-
import pytest
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture
def temp_config_file():
    """Create a temporary config file for testing"""
    config_content = """{
        "schedule": ["05:00", "13:00", "18:00"],
        "image_url": "https://example.com/picture.jpg",
        "display_model": "epd7in3e",
        "work_dir": "/tmp/project",
        "output_dir": "/tmp/project/output_dir",
        "display_script_path": "/external/Waveshare_E-Paper/display_picture.py"
    }"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        f.write(config_content)
        f.flush()
        yield f.name
    if os.path.exists(f.name):
        os.unlink(f.name)


@pytest.fixture
def temp_image_file():
    """Create a temporary image file for testing"""
    import numpy as np
    import cv2

    image = np.zeros((480, 800, 3), dtype=np.uint8)
    image[:, :, 0] = 255

    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
        cv2.imwrite(f.name, image)
        yield f.name
    if os.path.exists(f.name):
        os.unlink(f.name)


@pytest.fixture
def mock_epd():
    """Create a mock EPD object"""

    class MockEPD:
        def __init__(self, width=800, height=480):
            self.width = width
            self.height = height
            self._initialized = False

        def init(self):
            self._initialized = True

        def sleep(self):
            self._initialized = False

        def display(self, buffer):
            pass

        def getbuffer(self, image):
            return b"mock_buffer"

        class epdconfig:
            @staticmethod
            def module_exit():
                pass

    return MockEPD()


@pytest.fixture
def sample_config():
    """Sample config dictionary for testing"""
    return {
        "schedule": ["05:00", "13:00", "18:00"],
        "image_url": "https://example.com/picture.jpg",
        "display_model": "epd7in3e",
        "work_dir": "/tmp/project",
        "output_dir": "/tmp/project/output_dir",
        "display_script_path": "/external/Waveshare_E-Paper/display_picture.py",
    }
