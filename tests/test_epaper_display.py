#!/usr/bin/env python3
# -*- coding:utf-8 -*-
import pytest
import tempfile
import os
import sys
from unittest.mock import Mock, patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


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


class MockDriverModule:
    EPD = MockEPD


class TestLoadImage:
    def test_load_image_exists(self):
        import cv2
        import numpy as np

        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            temp_path = f.name
        try:
            image = np.zeros((100, 100, 3), dtype=np.uint8)
            cv2.imwrite(temp_path, image)
            from display import display as display_module

            result = display_module.load_image(temp_path)
            assert result is not None
        finally:
            os.unlink(temp_path)

    def test_load_image_not_exists(self):
        from display import display as display_module

        result = display_module.load_image("/nonexistent/path/image.png")
        assert result is None


class TestDynamicLoadDriver:
    @patch("importlib.import_module")
    def test_load_driver_success(self, mock_import):
        mock_import.return_value = MockDriverModule
        from display import display as display_module

        result = display_module.dynamic_load_driver("epd7in3e")
        assert result == MockDriverModule
        mock_import.assert_called()

    @patch("importlib.import_module")
    def test_load_driver_alternative_name(self, mock_import):
        mock_import.side_effect = [ModuleNotFoundError, MockDriverModule]
        from display import display as display_module

        result = display_module.dynamic_load_driver("epd7in3e")
        assert result == MockDriverModule
        assert mock_import.call_count == 2

    @patch("importlib.import_module")
    def test_load_driver_failure(self, mock_import):
        mock_import.side_effect = Exception("Module not found")
        from display import display as display_module

        with pytest.raises(SystemExit):
            display_module.dynamic_load_driver("nonexistent")


class TestDisplayImage:
    def test_display_image_success(self):
        import numpy as np
        from display import display as display_module

        mock_epd = MockEPD()
        mock_epd.init()
        mock_image = np.zeros((480, 800, 3), dtype=np.uint8)
        mock_image[:, :, 0] = 255
        display_module.display_image(mock_epd, mock_image)
        assert not mock_epd._initialized

    def test_display_image_error(self):
        import numpy as np
        from display import display as display_module

        mock_epd = MockEPD()
        mock_epd.init()
        mock_epd.display = Mock(side_effect=Exception("Display error"))
        mock_image = np.zeros((480, 800, 3), dtype=np.uint8)
        with pytest.raises(SystemExit):
            display_module.display_image(mock_epd, mock_image)


class TestMain:
    def test_main_size_mismatch(self):
        import numpy as np
        from display import display as display_module

        with patch.object(
            display_module, "dynamic_load_driver", return_value=MockDriverModule
        ):
            mock_image = np.zeros((400, 600, 3), dtype=np.uint8)
            with patch.object(display_module, "load_image", return_value=mock_image):
                with patch.object(os.path, "exists", return_value=True):
                    with pytest.raises(SystemExit) as exc_info:
                        with patch.object(
                            sys, "argv", ["display.py", "test.png", "-m", "epd7in3e"]
                        ):
                            display_module.main()
                    assert exc_info.value.code == 2

    def test_main_image_not_found(self):
        from display import display as display_module

        with patch.object(
            display_module, "dynamic_load_driver", return_value=MockDriverModule
        ):
            with patch.object(display_module, "load_image", return_value=None):
                with patch.object(os.path, "exists", return_value=False):
                    with pytest.raises(SystemExit) as exc_info:
                        with patch.object(
                            sys,
                            "argv",
                            ["display.py", "/nonexistent.png", "-m", "epd7in3e"],
                        ):
                            display_module.main()
                    assert exc_info.value.code == 1

    def test_main_display_init_failed(self):
        from display import display as display_module

        with patch.object(
            display_module, "dynamic_load_driver", side_effect=Exception("Init failed")
        ):
            with patch.object(os.path, "exists", return_value=True):
                with pytest.raises(SystemExit) as exc_info:
                    with patch.object(
                        sys, "argv", ["display.py", "test.png", "-m", "epd7in3e"]
                    ):
                        display_module.main()
                assert exc_info.value.code == 1


class TestSizeMatching:
    def test_exact_match(self):
        import numpy as np
        from display import display as display_module

        mock_epd = MockEPD(800, 480)
        mock_image = np.zeros((480, 800, 3), dtype=np.uint8)

        with patch.object(
            display_module, "dynamic_load_driver", return_value=MockDriverModule
        ):
            with patch.object(display_module, "load_image", return_value=mock_image):
                with patch.object(os.path, "exists", return_value=True):
                    with patch.object(
                        sys, "argv", ["display.py", "test.png", "-m", "epd7in3e"]
                    ):
                        with patch.object(mock_epd, "display"):
                            display_module.main()

    def test_width_mismatch(self):
        import numpy as np
        from display import display as display_module

        mock_image = np.zeros((480, 600, 3), dtype=np.uint8)

        with patch.object(
            display_module, "dynamic_load_driver", return_value=MockDriverModule
        ):
            with patch.object(display_module, "load_image", return_value=mock_image):
                with patch.object(os.path, "exists", return_value=True):
                    with pytest.raises(SystemExit) as exc_info:
                        with patch.object(
                            sys, "argv", ["display.py", "test.png", "-m", "epd7in3e"]
                        ):
                            display_module.main()
                    assert exc_info.value.code == 2

    def test_height_mismatch(self):
        import numpy as np
        from display import display as display_module

        mock_image = np.zeros((400, 800, 3), dtype=np.uint8)

        with patch.object(
            display_module, "dynamic_load_driver", return_value=MockDriverModule
        ):
            with patch.object(display_module, "load_image", return_value=mock_image):
                with patch.object(os.path, "exists", return_value=True):
                    with pytest.raises(SystemExit) as exc_info:
                        with patch.object(
                            sys, "argv", ["display.py", "test.png", "-m", "epd7in3e"]
                        ):
                            display_module.main()
                    assert exc_info.value.code == 2

    def test_height_mismatch(self):
        import numpy as np
        from display import display as display_module

        mock_image = np.zeros((400, 800, 3), dtype=np.uint8)

        with patch.object(
            display_module, "dynamic_load_driver", return_value=MockDriverModule
        ):
            with patch.object(display_module, "load_image", return_value=mock_image):
                with patch.object(os.path, "exists", return_value=True):
                    with pytest.raises(SystemExit) as exc_info:
                        with patch.object(
                            sys, "argv", ["display.py", "test.png", "-m", "epd7in3e"]
                        ):
                            display_module.main()
                    assert exc_info.value.code == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
