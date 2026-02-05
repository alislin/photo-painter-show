#!/usr/bin/env python3
# -*- coding:utf-8 -*-
import argparse
import cv2
import os
import sys
import time
import importlib
import logging
from PIL import Image

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def setup_driver_path(driver_path: str):
    """设置驱动路径"""
    if driver_path and os.path.exists(driver_path):
        sys.path.insert(0, driver_path)
        logger.info("Driver path set to: %s", driver_path)
    else:
        # 默认路径：./display/lib
        script_dir = os.path.dirname(os.path.abspath(__file__))
        default_driver = os.path.join(script_dir, "lib")
        if os.path.exists(default_driver):
            sys.path.insert(0, default_driver)
            logger.info("Using default driver path: %s", default_driver)
        else:
            logger.warning("No driver path available")


def load_image(image_path):
    return cv2.imread(image_path)


def dynamic_load_driver(display_model):
    try:
        module_name = f"waveshare_epd.epd{display_model}"
        driver_module = importlib.import_module(module_name)
        logger.info(f"Loaded %s driver: %s", display_model, module_name)
        return driver_module
    except ModuleNotFoundError:
        try:
            module_name = f"waveshare_epd.{display_model}"
            driver_module = importlib.import_module(module_name)
            logger.info(f"Loaded %s driver: %s", display_model, module_name)
            return driver_module
        except Exception as e:
            logger.error("Failed to load %s driver: %s", display_model, e)
            sys.exit(1)
    except Exception as e:
        logger.error("Exception loading driver: %s", e)
        sys.exit(1)


def display_image(epd, image):
    image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    pil_img = Image.fromarray(image_rgb)
    try:
        epd.display(epd.getbuffer(pil_img))
        time.sleep(1)
        epd.sleep()
        logger.info("Display completed, screen in sleep mode")
    except Exception as e:
        logger.error("Error during display: %s", e)
        if hasattr(epd, "epdconfig"):
            epd.epdconfig.module_exit()
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Simplified e-paper display")
    parser.add_argument("image", help="Input image path")
    parser.add_argument(
        "-m", "--model", required=True, help="Display model (e.g., epd7in3e)"
    )
    parser.add_argument("-o", "--output", default=None, help="Output directory")
    parser.add_argument(
        "-d", "--driver", default=None, help="Driver library path"
    )
    parser.add_argument(
        "-r", "--rotate", action="store_true", help="Rotate image 180 degrees"
    )
    args = parser.parse_args()

    display_model = args.model
    image_path = args.image
    rotate_180 = args.rotate

    if rotate_180:
        logger.info("Rotation: 180 degrees enabled")

    # 设置驱动路径
    setup_driver_path(args.driver)

    if not os.path.exists(image_path):
        logger.error("Image not found: %s", image_path)
        sys.exit(1)

    try:
        driver_module = dynamic_load_driver(display_model)
        epd = driver_module.EPD()
        epd.init()
        disp_w, disp_h = epd.width, epd.height
        logger.info("Display resolution: %sx%s", disp_w, disp_h)
    except Exception as e:
        logger.error("Failed to initialize display: %s", e)
        sys.exit(1)

    image = load_image(image_path)
    if image is None:
        logger.error("Failed to load image: %s", image_path)
        sys.exit(1)

    # 旋转180度
    if rotate_180:
        image = cv2.rotate(image, cv2.ROTATE_180)

    img_h, img_w = image.shape[:2]
    logger.info("Image size: %sx%s", img_w, img_h)

    if img_w != disp_w or img_h != disp_h:
        logger.warning("Size mismatch: image=%sx%s, display=%sx%s", img_w, img_h, disp_w, disp_h)
        logger.info("Use external display script for processing")
        epd.epdconfig.module_exit()
        sys.exit(2)

    display_image(epd, image)


if __name__ == "__main__":
    main()
