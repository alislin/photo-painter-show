#!/usr/bin/env python3
# -*- coding:utf-8 -*-
import pytest
import tempfile
import os
import sys
from unittest.mock import Mock, patch, MagicMock
import subprocess

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestCallDisplayScript:
    @patch("subprocess.run")
    @patch("os.path.exists")
    def test_simplified_script_success(self, mock_exists, mock_run):
        mock_exists.return_value = True
        mock_result = Mock()
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        from main import call_display_script

        config = {"display_script_path": "/external/script.py"}
        result = call_display_script(
            "epd7in3e", "/tmp/image.png", "/tmp/output", config
        )

        assert result is True
        mock_run.assert_called_once()

    @patch("subprocess.run")
    @patch("os.path.exists")
    def test_simplified_script_size_mismatch_fallback_success(
        self, mock_exists, mock_run
    ):
        mock_exists.return_value = True
        mock_result1 = Mock()
        mock_result1.returncode = 2
        mock_result2 = Mock()
        mock_result2.returncode = 0
        mock_run.side_effect = [mock_result1, mock_result2]

        from main import call_display_script

        config = {"display_script_path": "/external/script.py"}
        result = call_display_script(
            "epd7in3e", "/tmp/image.png", "/tmp/output", config
        )

        assert result is True
        assert mock_run.call_count == 2

    @patch("subprocess.run")
    @patch("os.path.exists")
    def test_simplified_script_size_mismatch_fallback_fails(
        self, mock_exists, mock_run
    ):
        mock_exists.return_value = True
        mock_result1 = Mock()
        mock_result1.returncode = 2
        mock_result2 = Mock()
        mock_result2.returncode = 1
        mock_result2.stderr = "Error"
        mock_run.side_effect = [mock_result1, mock_result2]

        from main import call_display_script

        config = {"display_script_path": "/external/script.py"}
        result = call_display_script(
            "epd7in3e", "/tmp/image.png", "/tmp/output", config
        )

        assert result is False

    @patch("subprocess.run")
    def test_external_script_path_not_configured(self, mock_run):
        mock_result = Mock()
        mock_result.returncode = 2
        mock_run.return_value = mock_result

        from main import call_display_script

        config = {"display_script_path": ""}
        result = call_display_script(
            "epd7in3e", "/tmp/image.png", "/tmp/output", config
        )

        assert result is False
        assert mock_run.call_count == 1

    @patch("subprocess.run")
    def test_external_script_not_exists(self, mock_run):
        mock_result = Mock()
        mock_result.returncode = 2
        mock_run.return_value = mock_result

        from main import call_display_script

        config = {"display_script_path": "/nonexistent/script.py"}
        result = call_display_script(
            "epd7in3e", "/tmp/image.png", "/tmp/output", config
        )

        assert result is False

    @patch("subprocess.run")
    def test_simplified_script_timeout(self, mock_run):
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="test", timeout=300)

        from main import call_display_script

        config = {"display_script_path": "/external/script.py"}
        result = call_display_script(
            "epd7in3e", "/tmp/image.png", "/tmp/output", config
        )

        assert result is False


class TestExecuteTask:
    @patch("main.wifi_on")
    @patch("main.download_with_retry")
    @patch("main.wifi_off")
    @patch("main.call_display_script")
    def test_execute_task_success(
        self, mock_display, mock_wifi_off, mock_download, mock_wifi_on
    ):
        mock_wifi_on.return_value = True
        mock_download.return_value = True
        mock_wifi_off.return_value = True
        mock_display.return_value = True

        from main import execute_task
        from config import load_config as real_load_config

        tmp_path = tempfile.mktemp(suffix=".json")
        with open(tmp_path, "w") as f:
            f.write("""{
                "schedule": ["05:00"],
                "image_url": "https://example.com/pic.jpg",
                "display_model": "epd7in3e",
                "work_dir": "/tmp",
                "output_dir": "/tmp/output",
                "display_script_path": ""
            }""")
        try:
            config = real_load_config(tmp_path)
            result = execute_task(config)
            assert result is True
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    @patch("main.wifi_on")
    def test_execute_task_wifi_on_failed(self, mock_wifi_on):
        mock_wifi_on.return_value = False

        from main import execute_task
        from config import load_config as real_load_config

        tmp_path = tempfile.mktemp(suffix=".json")
        with open(tmp_path, "w") as f:
            f.write("""{
                "schedule": ["05:00"],
                "image_url": "https://example.com/pic.jpg",
                "display_model": "epd7in3e",
                "work_dir": "/tmp",
                "output_dir": "/tmp/output",
                "display_script_path": ""
            }""")
        try:
            config = real_load_config(tmp_path)
            result = execute_task(config)
            assert result is False
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    @patch("main.wifi_on")
    @patch("main.download_with_retry")
    @patch("main.wifi_off")
    def test_execute_task_download_failed(
        self, mock_wifi_off, mock_download, mock_wifi_on
    ):
        mock_wifi_on.return_value = True
        mock_download.return_value = False
        mock_wifi_off.return_value = True

        from main import execute_task
        from config import load_config as real_load_config

        tmp_path = tempfile.mktemp(suffix=".json")
        with open(tmp_path, "w") as f:
            f.write("""{
                "schedule": ["05:00"],
                "image_url": "https://example.com/pic.jpg",
                "display_model": "epd7in3e",
                "work_dir": "/tmp",
                "output_dir": "/tmp/output",
                "display_script_path": ""
            }""")
        try:
            config = real_load_config(tmp_path)
            result = execute_task(config)
            assert result is False
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    @patch("main.wifi_on")
    @patch("main.download_with_retry")
    @patch("main.wifi_off")
    @patch("main.call_display_script")
    def test_execute_task_display_failed(
        self, mock_display, mock_wifi_off, mock_download, mock_wifi_on
    ):
        mock_wifi_on.return_value = True
        mock_download.return_value = True
        mock_wifi_off.return_value = True
        mock_display.return_value = False

        from main import execute_task
        from config import load_config as real_load_config

        tmp_path = tempfile.mktemp(suffix=".json")
        with open(tmp_path, "w") as f:
            f.write("""{
                "schedule": ["05:00"],
                "image_url": "https://example.com/pic.jpg",
                "display_model": "epd7in3e",
                "work_dir": "/tmp",
                "output_dir": "/tmp/output",
                "display_script_path": ""
            }""")
        try:
            config = real_load_config(tmp_path)
            result = execute_task(config)
            assert result is False
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)


class TestScriptPathHandling:
    @patch("subprocess.run")
    def test_script_path_with_spaces(self, mock_run):
        mock_result = Mock()
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        from main import call_display_script

        config = {"display_script_path": "/path with spaces/script.py"}
        result = call_display_script(
            "epd7in3e", "/tmp/image.png", "/tmp/output", config
        )

        assert result is True

    @patch("subprocess.run")
    @patch("os.path.exists")
    def test_fallback_called_with_correct_args(self, mock_exists, mock_run):
        mock_exists.return_value = True
        mock_result1 = Mock()
        mock_result1.returncode = 2
        mock_result2 = Mock()
        mock_result2.returncode = 0
        mock_run.side_effect = [mock_result1, mock_result2]

        from main import call_display_script

        config = {"display_script_path": "/external/script.py"}
        call_display_script("epd7in3e", "/tmp/test.png", "/tmp/out", config)

        fallback_call = mock_run.call_args_list[1]
        args = fallback_call[0][0]

        assert "-m" in args
        assert "epd7in3e" in args
        assert "/tmp/test.png" in args
        assert "-o" in args
        assert "/tmp/out" in args


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
