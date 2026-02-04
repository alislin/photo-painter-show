#!/usr/bin/env python3
# -*- coding:utf-8 -*-
import argparse
import cv2
import os
import sys
import time
import importlib
from PIL import Image

DRIVER_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "Waveshare_E-Paper", "lib"
)
sys.path.append(DRIVER_DIR)


def load_image(image_path):
    return cv2.imread(image_path)


def dynamic_load_driver(display_model):
    try:
        module_name = f"waveshare_epd.epd{display_model}"
        driver_module = importlib.import_module(module_name)
        print(f"Loaded {display_model} driver: {module_name}")
        return driver_module
    except ModuleNotFoundError:
        try:
            module_name = f"waveshare_epd.{display_model}"
            driver_module = importlib.import_module(module_name)
            print(f"Loaded {display_model} driver: {module_name}")
            return driver_module
        except Exception as e:
            print(f"Error: Failed to load {display_model} driver: {e}")
            sys.exit(1)
    except Exception as e:
        print(f"Error: Exception loading driver: {e}")
        sys.exit(1)


def display_image(epd, image):
    image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    pil_img = Image.fromarray(image_rgb)
    try:
        epd.display(epd.getbuffer(pil_img))
        time.sleep(1)
        epd.sleep()
        print("Display completed, screen in sleep mode")
    except Exception as e:
        print(f"Error during display: {e}")
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
    args = parser.parse_args()

    display_model = args.model
    image_path = args.image

    if not os.path.exists(image_path):
        print(f"Error: Image not found: {image_path}")
        sys.exit(1)

    try:
        driver_module = dynamic_load_driver(display_model)
        epd = driver_module.EPD()
        epd.init()
        disp_w, disp_h = epd.width, epd.height
        print(f"Display resolution: {disp_w}x{disp_h}")
    except Exception as e:
        print(f"Failed to initialize display: {e}")
        sys.exit(1)

    image = load_image(image_path)
    if image is None:
        print(f"Error: Failed to load image: {image_path}")
        sys.exit(1)

    img_h, img_w = image.shape[:2]
    print(f"Image size: {img_w}x{img_h}")

    if img_w != disp_w or img_h != disp_h:
        print(f"Size mismatch: image={img_w}x{img_h}, display={disp_w}x{disp_h}")
        print("Use external display script for processing")
        epd.epdconfig.module_exit()
        sys.exit(2)

    display_image(epd, image)


if __name__ == "__main__":
    main()
