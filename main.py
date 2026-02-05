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
    get_log_file,
    is_debug_mode,
    get_allow_wifi_off,
    get_rotate_display,
    get_enable_time_sync,
    get_sync_timeout,
    get_sync_on_boot,
    get_sync_before_suspend,
    get_enable_power_tracking,
    get_power_log_file,
)
from wifi_manager import wifi_on, wifi_off
from fetcher import download_with_retry
from scheduler import (
    get_next_wake_time,
    format_next_wake_time,
    calculate_sleep_duration,
    calculate_next_interval_wake,
)
from power_manager import create_power_manager, create_power_tracker
from time_sync import sync_time_with_chrony, sync_system_to_rtc

# 日志配置将在 main() 中根据 config 设置
logger = logging.getLogger(__name__)

IMAGE_PATH = "/tmp/latest_image.jpg"


def call_display_script(
    display_model: str, image_path: str, output_dir: str, config: dict
) -> bool:
    script_dir = os.path.dirname(os.path.abspath(__file__))
    simplified_script = os.path.join(script_dir, "display", "display.py")

    # 从 display_script_path 推断驱动路径
    external_script = get_display_script_path(config)
    if external_script:
        driver_path = os.path.join(os.path.dirname(external_script), "..", "lib")
    else:
        driver_path = None

    cmd_simplified = [
        sys.executable,
        simplified_script,
        "-m",
        display_model,
        image_path,
        "-o",
        output_dir,
    ]
    if driver_path:
        cmd_simplified.extend(["-d", driver_path])

    # 检查是否需要旋转
    rotate_display = get_rotate_display(config)
    if rotate_display:
        cmd_simplified.append("-r")

    try:
        logger.info("Trying simplified display script")
        result_simplified = subprocess.run(
            cmd_simplified, capture_output=True, text=True, timeout=300
        )

        # 输出子进程日志
        if result_simplified.stdout:
            for line in result_simplified.stdout.strip().split("\n"):
                logger.info(f"[display] {line}")
        if result_simplified.stderr:
            for line in result_simplified.stderr.strip().split("\n"):
                logger.warning(f"[display] {line}")

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

        # 输出子进程日志
        if result_external.stdout:
            for line in result_external.stdout.strip().split("\n"):
                logger.info(f"[display] {line}")
        if result_external.stderr:
            for line in result_external.stderr.strip().split("\n"):
                logger.warning(f"[display] {line}")

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


def execute_task(config: dict, power_manager=None, power_tracker=None) -> bool:
    logger.info("=" * 50)
    logger.info("Starting task execution")
    logger.info("=" * 50)

    display_model = get_display_model(config)
    output_dir = get_output_dir(config)
    image_url = get_image_url(config)
    allow_wifi_off = get_allow_wifi_off(config)

    os.makedirs(output_dir, exist_ok=True)

    charging_state = False
    if power_manager:
        try:
            charging_state = power_manager.is_charging()
        except:
            pass

    # 开始电量追踪
    if power_tracker:
        power_tracker.start_task(power_manager)
        logger.info(f"Power tracking started (charging: {charging_state})")

    if not wifi_on():
        logger.error("Failed to enable WiFi")
        if power_tracker:
            power_tracker.end_task(power_manager, charging=charging_state)
        return False

    # WiFi 开启后采样
    if power_tracker:
        power_tracker.sample_power(power_manager, "wifi_on")

    if not download_with_retry(image_url, IMAGE_PATH, max_retries=3):
        logger.error("Failed to download image")
        if allow_wifi_off:
            wifi_off()
        else:
            logger.info("WiFi keep-alive: skipping WiFi off")
        if power_tracker:
            power_tracker.end_task(power_manager, charging=charging_state)
        return False

    # 下载完成后采样
    if power_tracker:
        power_tracker.sample_power(power_manager, "download_complete")

    if allow_wifi_off:
        if not wifi_off():
            logger.warning("Failed to disable WiFi")
    else:
        logger.info("WiFi keep-alive mode enabled")

    # WiFi 关闭后采样
    if power_tracker:
        power_tracker.sample_power(power_manager, "wifi_off")

    if not call_display_script(display_model, IMAGE_PATH, output_dir, config):
        logger.error("Failed to display image")
        if power_tracker:
            power_tracker.end_task(power_manager, charging=charging_state)
        return False

    # 显示完成后采样并结束追踪
    if power_tracker:
        power_tracker.sample_power(power_manager, "display_complete")
        record = power_tracker.end_task(power_manager, charging=charging_state)
        if record:
            logger.info(
                f"Task #{record.task_id} power summary: "
                f"{record.net_consumption:.1f}% consumed, "
                f"avg {record.avg_power:.2f}W, "
                f"duration {record.task_duration:.1f}s"
            )

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
    log_file = get_log_file(config)

    handlers = [logging.StreamHandler()]
    if log_file:
        from pathlib import Path

        Path(log_file).parent.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(log_file, encoding="utf-8"))

    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=handlers,
    )

    logger.info("Photo Painter Show - Main Program Started")

    if get_enable_time_sync(config) and get_sync_on_boot(config):
        logger.info("正在同步网络时间...")
        success, msg = sync_time_with_chrony(get_sync_timeout(config))
        if success:
            logger.info(f"开机时间同步成功: {msg}")
        else:
            logger.warning(f"开机时间同步失败: {msg}, 继续运行")

    # 初始化电源管理器
    power_manager = create_power_manager()
    if power_manager:
        logger.info("INA219 power manager initialized")
    else:
        logger.warning("INA219 not available, skipping power detection")

    # 初始化电量追踪器
    power_tracker = None
    if get_enable_power_tracking(config):
        power_log_file = get_power_log_file(config)
        if not os.path.isabs(power_log_file):
            power_log_file = os.path.join(
                os.path.dirname(os.path.abspath(__file__)), power_log_file
            )
        try:
            power_tracker = create_power_tracker(power_log_file)
            logger.info(f"Power tracker initialized: {power_log_file}")
        except Exception as e:
            logger.warning(f"Failed to initialize power tracker: {e}")
    else:
        logger.info("Power tracking disabled")

    logger.info(
        f"Config loaded: mode={get_mode(config)}, schedule={get_schedule(config)}, "
        f"interval={get_interval_minutes(config)}min, display={get_display_model(config)}"
    )

    MAINTENANCE_CHECK_INTERVAL = 30  # 充电状态下检测间隔（秒）
    last_charging_state = None  # 记录上一次充电状态，用于状态变化检测

    while True:
        try:
            # 检查充电状态
            is_charging = True  # 默认维护模式，防止无电源硬件时休眠无法唤醒
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
                            f"current={status['current'] * 1000:.0f}mA"
                        )
                        last_charging_state = is_charging

                except Exception as e:
                    logger.warning(f"Failed to read power status: {e}")
            else:
                # 无 INA219 硬件，默认进入维护模式
                if last_charging_state is not None:
                    logger.info(
                        "No power manager - maintenance mode enabled by default"
                    )
                last_charging_state = False  # 标记已输出过日志

            if is_charging:
                # 充电状态：执行任务后不休眠，继续检测
                logger.info("Charging mode - executing task without suspend")
                if execute_task(config, power_manager, power_tracker):
                    logger.info(
                        f"Task completed, checking again in {MAINTENANCE_CHECK_INTERVAL} seconds"
                    )
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
                    logger.info(
                        f"Interval mode: waking every {interval_minutes} minutes"
                    )
                else:
                    # 默认 schedule 模式（固定时间点）
                    schedule_list = get_schedule(config)
                    wake_timestamp = get_next_wake_time(schedule_list)

                if execute_task(config, power_manager, power_tracker):
                    run_rtcwake(wake_timestamp)

                    logger.info("System suspending...")
                    sys.stdout.flush()
                    sys.stderr.flush()

                    if get_sync_before_suspend(config):
                        logger.info("正在同步系统时间到 RTC...")
                        sync_success, sync_msg = sync_system_to_rtc()
                        if sync_success:
                            logger.info(f"RTC 同步成功: {sync_msg}")
                        else:
                            logger.warning(f"RTC 同步失败: {sync_msg}, 继续休眠")

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

                    if get_sync_before_suspend(config):
                        logger.info("正在同步系统时间到 RTC...")
                        sync_success, sync_msg = sync_system_to_rtc()
                        if sync_success:
                            logger.info(f"RTC 同步成功: {sync_msg}")
                        else:
                            logger.warning(f"RTC 同步失败: {sync_msg}, 继续休眠")

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

            if get_sync_before_suspend(config):
                logger.info("正在同步系统时间到 RTC...")
                sync_success, sync_msg = sync_system_to_rtc()
                if sync_success:
                    logger.info(f"RTC 同步成功: {sync_msg}")
                else:
                    logger.warning(f"RTC 同步失败: {sync_msg}, 继续休眠")

            os.system("sync")
            os.system("systemctl suspend")

    logger.info("Program exiting")
    sys.exit(0)


if __name__ == "__main__":
    main()
