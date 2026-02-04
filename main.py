#!/usr/bin/env python3
# -*- coding:utf-8 -*-
import sys
import os
import subprocess
import time
import logging
import signal

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config import (
    load_config,
    get_schedule,
    get_image_url,
    get_display_model,
    get_output_dir,
    get_display_script_path,
)
from wifi_manager import wifi_on, wifi_off
from fetcher import download_with_retry
from scheduler import (
    get_next_wake_time,
    format_next_wake_time,
    calculate_sleep_duration,
)

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

IMAGE_PATH = "/tmp/latest_image.jpg"


def call_display_script(
    display_model: str, image_path: str, output_dir: str, config: dict
) -> bool:
    script_dir = os.path.dirname(os.path.abspath(__file__))
    simplified_script = os.path.join(script_dir, "display", "display.py")

    logger.info("Trying simplified display script")
    cmd_simplified = [
        sys.executable,
        simplified_script,
        "-m",
        display_model,
        image_path,
        "-o",
        output_dir,
    ]

    try:
        result_simplified = subprocess.run(
            cmd_simplified, capture_output=True, text=True, timeout=300
        )

        if result_simplified.returncode == 0:
            logger.info("Simplified display script executed successfully")
            return True

        if result_simplified.returncode == 2:
            logger.info("Image size mismatch, falling back to external display script")

        external_script = get_display_script_path(config)
        if not external_script:
            logger.error("External display script path not configured")
            return False

        if not os.path.exists(external_script):
            logger.error(f"External display script not found: {external_script}")
            return False

        cmd_external = [
            sys.executable,
            external_script,
            "-m",
            display_model,
            image_path,
            "-o",
            output_dir,
        ]

        logger.info(f"Falling back to external display script: {external_script}")
        result_external = subprocess.run(
            cmd_external, capture_output=True, text=True, timeout=300
        )

        if result_external.returncode == 0:
            logger.info("External display script executed successfully")
            return True
        else:
            logger.error(f"External display script failed: {result_external.stderr}")
            return False

    except subprocess.TimeoutExpired:
        logger.error("Display script timed out")
        return False
    except Exception as e:
        logger.error(f"Error calling display script: {e}")
        return False


def run_rtcwake(wake_timestamp: int) -> bool:
    try:
        sleep_duration = calculate_sleep_duration(wake_timestamp)
        if sleep_duration <= 0:
            logger.warning("Wake time is in the past, scheduling for next cycle")
            schedule_list = get_schedule(load_config())
            wake_timestamp = get_next_wake_time(schedule_list)
            sleep_duration = calculate_sleep_duration(wake_timestamp)

        formatted_time = format_next_wake_time(wake_timestamp)
        logger.info(
            f"Scheduling RTC wake-up at {formatted_time} (in {sleep_duration:.0f} seconds)"
        )

        cmd = ["rtcwake", "-m", "off", "-t", str(wake_timestamp)]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)

        if result.returncode == 0:
            logger.info("RTC wake scheduled successfully, system will suspend")
            return True
        else:
            logger.error(f"RTC wake failed: {result.stderr}")
            return False

    except FileNotFoundError:
        logger.error("rtcwake command not found")
        return False
    except Exception as e:
        logger.error(f"Error scheduling RTC wake: {e}")
        return False


def execute_task(config: dict) -> bool:
    logger.info("=" * 50)
    logger.info("Starting task execution")
    logger.info("=" * 50)

    display_model = get_display_model(config)
    output_dir = get_output_dir(config)
    image_url = get_image_url(config)

    os.makedirs(output_dir, exist_ok=True)

    if not wifi_on():
        logger.error("Failed to enable WiFi")
        return False

    if not download_with_retry(image_url, IMAGE_PATH, max_retries=3):
        logger.error("Failed to download image")
        wifi_off()
        return False

    if not wifi_off():
        logger.warning("Failed to disable WiFi")

    if not call_display_script(display_model, IMAGE_PATH, output_dir, config):
        logger.error("Failed to display image")
        return False

    logger.info("Task execution completed successfully")
    return True


def main():
    logger.info("Photo Painter Show - Main Program Started")

    try:
        config = load_config()
        logger.info(
            f"Config loaded: schedule={get_schedule(config)}, display={get_display_model(config)}"
        )
    except Exception as e:
        logger.error(f"Failed to load config: {e}")
        sys.exit(1)

    while True:
        try:
            schedule_list = get_schedule(config)
            wake_timestamp = get_next_wake_time(schedule_list)

            if execute_task(config):
                run_rtcwake(wake_timestamp)

                logger.info("System suspending...")
                sys.stdout.flush()
                sys.stderr.flush()

                os.system("sync")
                os.system("systemctl suspend")

                logger.info("System resumed from suspend")
                time.sleep(5)

            else:
                logger.error("Task execution failed")
                schedule_list = get_schedule(config)
                wake_timestamp = get_next_wake_time(schedule_list)
                run_rtcwake(wake_timestamp)
                os.system("sync")
                os.system("systemctl suspend")

        except KeyboardInterrupt:
            logger.info("Interrupted by user")
            break
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            schedule_list = get_schedule(config)
            wake_timestamp = get_next_wake_time(schedule_list)
            run_rtcwake(wake_timestamp)
            os.system("sync")
            os.system("systemctl suspend")

    logger.info("Program exiting")
    sys.exit(0)


if __name__ == "__main__":
    main()
