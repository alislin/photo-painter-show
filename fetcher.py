#!/usr/bin/env python3
# -*- coding:utf-8 -*-
import requests
import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def download_image(url: str, save_path: str, timeout: int = 60) -> bool:
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }

        logger.info(f"Downloading image from: {url}")

        response = requests.get(url, headers=headers, timeout=timeout, stream=True)
        response.raise_for_status()

        os.makedirs(os.path.dirname(save_path), exist_ok=True)

        with open(save_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        file_size = os.path.getsize(save_path)
        logger.info(f"Image saved to {save_path} ({file_size} bytes)")

        return True

    except requests.exceptions.Timeout:
        logger.error(f"Download timeout: {url}")
        return False
    except requests.exceptions.HTTPError as e:
        logger.error(f"HTTP error: {e}")
        return False
    except requests.exceptions.RequestException as e:
        logger.error(f"Request error: {e}")
        return False
    except IOError as e:
        logger.error(f"IO error saving file: {e}")
        return False


def download_with_retry(
    url: str, save_path: str, max_retries: int = 3, timeout: int = 60
) -> bool:
    for attempt in range(1, max_retries + 1):
        logger.info(f"Download attempt {attempt}/{max_retries}")
        if download_image(url, save_path, timeout):
            return True
        if attempt < max_retries:
            wait_time = attempt * 10
            logger.info(f"Retrying in {wait_time} seconds...")
            import time

            time.sleep(wait_time)

    logger.error(f"Failed to download after {max_retries} attempts")
    return False
