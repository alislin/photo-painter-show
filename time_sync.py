#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
时间同步模块 - 使用 chrony 进行 NTP 同步

功能:
- 开机时同步网络时间
- 休眠前同步系统时间到 RTC
- 自动校准系统时钟
"""

import subprocess
import logging
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


def check_chrony_available() -> bool:
    result = subprocess.run(
        ["which", "chronyc"], capture_output=True, text=True, timeout=10
    )
    return result.returncode == 0


def sync_time_with_chrony(timeout: int = 30) -> Tuple[bool, str]:
    if not check_chrony_available():
        return False, "chrony 未安装"

    try:
        result = subprocess.run(
            ["chronyc", "makestep"],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        if result.returncode == 0:
            tracking = subprocess.run(
                ["chronyc", "tracking"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if tracking.returncode == 0:
                for line in tracking.stdout.splitlines():
                    if "System time" in line:
                        offset = line.split(":")[1].strip()
                        logger.info(f"时间同步完成, 系统偏移: {offset}")
                        return True, f"同步成功, 偏移: {offset}"
            return True, "makestep 执行成功"
        else:
            return False, f"同步失败: {result.stderr}"
    except subprocess.TimeoutExpired:
        return False, "同步超时"
    except Exception as e:
        return False, f"同步异常: {e}"


def sync_system_to_rtc() -> Tuple[bool, str]:
    try:
        result = subprocess.run(
            ["sudo", "hwclock", "--systohc"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            logger.info("系统时间已同步到 RTC")
            return True, "RTC 同步成功"
        else:
            return False, f"RTC 同步失败: {result.stderr}"
    except Exception as e:
        return False, f"RTC 同步异常: {e}"


def sync_rtc_to_system() -> Tuple[bool, str]:
    try:
        result = subprocess.run(
            ["sudo", "hwclock", "--hctosys"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            logger.info("RTC 时间已同步到系统")
            return True, "系统同步成功"
        else:
            return False, f"系统同步失败: {result.stderr}"
    except Exception as e:
        return False, f"系统同步异常: {e}"


def get_time_status() -> dict:
    status = {
        "chrony_available": check_chrony_available(),
        "system_time": None,
        "rtc_time": None,
        "chrony_tracking": None,
    }

    try:
        result = subprocess.run(
            ["date", "+%Y-%m-%d %H:%M:%S"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            status["system_time"] = result.stdout.strip()
    except Exception:
        pass

    try:
        result = subprocess.run(
            ["sudo", "hwclock", "-r"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            status["rtc_time"] = result.stdout.strip()
    except Exception:
        pass

    if check_chrony_available():
        try:
            result = subprocess.run(
                ["chronyc", "tracking"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                status["chrony_tracking"] = result.stdout
        except Exception:
            pass

    return status
