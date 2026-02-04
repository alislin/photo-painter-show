#!/usr/bin/env python3
# -*- coding:utf-8 -*-
from datetime import datetime, timedelta
import time
import logging
from typing import List, Optional

logger = logging.getLogger(__name__)


def parse_time_string(time_str: str) -> datetime:
    now = datetime.now()
    parts = time_str.split(":")
    if len(parts) != 2:
        raise ValueError(f"Invalid time format: {time_str}, expected HH:MM")

    hour = int(parts[0])
    minute = int(parts[1])

    return now.replace(hour=hour, minute=minute, second=0, microsecond=0)


def get_next_wake_time(schedule_list: List[str]) -> int:
    now = datetime.now()
    today_times = []

    for time_str in schedule_list:
        try:
            target_time = parse_time_string(time_str)
            today_times.append(target_time)
        except ValueError as e:
            logger.warning(f"Invalid time format: {time_str}, skipping")
            continue

    today_times.sort()

    for target_time in today_times:
        if target_time > now:
            timestamp = int(target_time.timestamp())
            logger.info(f"Next wake time: {target_time.strftime('%Y-%m-%d %H:%M:%S')}")
            return timestamp

    next_day = schedule_list[0]
    tomorrow_target = parse_time_string(next_day) + timedelta(days=1)
    timestamp = int(tomorrow_target.timestamp())
    logger.info(
        f"Next wake time (tomorrow): {tomorrow_target.strftime('%Y-%m-%d %H:%M:%S')}"
    )
    return timestamp


def format_next_wake_time(timestamp: int) -> str:
    dt = datetime.fromtimestamp(timestamp)
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def get_current_timestamp() -> int:
    return int(time.time())


def calculate_sleep_duration(wake_timestamp: int) -> float:
    now = get_current_timestamp()
    duration = wake_timestamp - now
    return max(0, duration)


def calculate_next_interval_wake(interval_minutes: int) -> int:
    """计算间隔模式下的下次唤醒时间戳

    Args:
        interval_minutes: 间隔分钟数

    Returns:
        下次唤醒时间的Unix时间戳
    """
    now = get_current_timestamp()
    next_wake = now + interval_minutes * 60
    logger.info(f"Interval mode: next wake in {interval_minutes} minutes at {datetime.fromtimestamp(next_wake).strftime('%Y-%m-%d %H:%M:%S')}")
    return next_wake
