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
    get_mode,
    get_schedule,
    get_interval_minutes,
    get_image_url,
    get_display_model,
    get_output_dir,
    get_display_script_path,
    get_log_level,
    is_debug_mode,
)
from wifi_manager import wifi_on, wifi_off
from fetcher import download_with_retry
from scheduler import (
    get_next_wake_time,
    format_next_wake_time,
    calculate_sleep_duration,
    calculate_next_interval_wake,
)
from power_manager import create_power_manager

# 日志配置将在 main() 中根据 config 设置
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
    try:
        config = load_config()
    except Exception as e:
        print(f"Failed to load config: {e}")
        sys.exit(1)

    # 根据配置设置日志级别
    log_level = getattr(logging, get_log_level(config), logging.INFO)
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(levelname)s - %(message)s"
    )

    logger.info("Photo Painter Show - Main Program Started")

    # 初始化电源管理器
    power_manager = create_power_manager()
    if power_manager:
        logger.info("INA219 power manager initialized")
    else:
        logger.warning("INA219 not available, skipping power detection")

    logger.info(
        f"Config loaded: mode={get_mode(config)}, schedule={get_schedule(config)}, "
        f"interval={get_interval_minutes(config)}min, display={get_display_model(config)}"
    )

    MAINTENANCE_CHECK_INTERVAL = 30  # 充电状态下检测间隔（秒）
    last_charging_state = None  # 记录上一次充电状态，用于状态变化检测

    while True:
        try:
            # 检查充电状态
            is_charging = False
            if power_manager:
                try:
                    status = power_manager.get_status()
                    is_charging = status["charging"]

                    # 只在状态变化时输出日志
                    if is_charging != last_charging_state:
                        state_text = "charging" if is_charging else "discharging"
                        logger.info(
                            f"Power state changed to {state_text}: "
                            f"voltage={status['voltage']:.3f}V, "
                            f"current={status['current']*1000:.0f}mA"
                        )
                        last_charging_state = is_charging

                except Exception as e:
                    logger.warning(f"Failed to read power status: {e}")

            if is_charging:
                # 充电状态：执行任务后不休眠，继续检测
                logger.info("Charging mode - executing task without suspend")
                if execute_task(config):
                    logger.info(f"Task completed, checking again in {MAINTENANCE_CHECK_INTERVAL} seconds")
                    time.sleep(MAINTENANCE_CHECK_INTERVAL)
                else:
                    logger.error("Task failed, retrying in 30 seconds")
                    time.sleep(30)
            else:
                # 未充电：根据模式选择调度策略
                mode = get_mode(config)
                if mode == "interval":
                    # 间隔模式
                    interval_minutes = get_interval_minutes(config)
                    wake_timestamp = calculate_next_interval_wake(interval_minutes)
                    logger.info(f"Interval mode: waking every {interval_minutes} minutes")
                else:
                    # 默认 schedule 模式（固定时间点）
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
                    mode = get_mode(config)
                    if mode == "interval":
                        interval_minutes = get_interval_minutes(config)
                        wake_timestamp = calculate_next_interval_wake(interval_minutes)
                    else:
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
            mode = get_mode(config)
            if mode == "interval":
                interval_minutes = get_interval_minutes(config)
                wake_timestamp = calculate_next_interval_wake(interval_minutes)
            else:
                schedule_list = get_schedule(config)
                wake_timestamp = get_next_wake_time(schedule_list)
            run_rtcwake(wake_timestamp)
            os.system("sync")
            os.system("systemctl suspend")

    logger.info("Program exiting")
    sys.exit(0)


if __name__ == "__main__":
    main()
