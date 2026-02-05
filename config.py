#!/usr/bin/env python3
# -*- coding:utf-8 -*-
import json
import os
from typing import Dict, List, Any

CONFIG_FILE = "config.json"


def load_config(config_path: str | None = None) -> Dict[str, Any]:
    if config_path is None:
        config_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), CONFIG_FILE
        )

    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)

    required_keys = ["schedule", "image_url", "display_model", "work_dir", "output_dir"]
    for key in required_keys:
        if key not in config:
            raise ValueError(f"Missing required config key: {key}")

    return config


def get_schedule(config: Dict[str, Any]) -> List[str]:
    return config.get("schedule", [])


def get_image_url(config: Dict[str, Any]) -> str:
    return config.get("image_url", "")


def get_display_model(config: Dict[str, Any]) -> str:
    return config.get("display_model", "")


def get_work_dir(config: Dict[str, Any]) -> str:
    return config.get("work_dir", "")


def get_output_dir(config: Dict[str, Any]) -> str:
    return config.get("output_dir", "")


def get_display_script_path(config: Dict[str, Any]) -> str:
    return config.get("display_script_path", "")


def get_log_level(config: Dict[str, Any]) -> str:
    """获取日志级别"""
    return config.get("log_level", "INFO").upper()


def is_debug_mode(config: Dict[str, Any]) -> bool:
    """是否开启调试模式"""
    return config.get("debug_mode", False)


def get_mode(config: Dict[str, Any]) -> str:
    """获取运行模式: schedule(固定时间点) | interval(固定间隔)"""
    return config.get("mode", "schedule")


def get_interval_minutes(config: Dict[str, Any]) -> int:
    """获取间隔模式的分钟数"""
    return config.get("interval_minutes", 60)


def get_log_file(config: Dict[str, Any]) -> str:
    """获取日志文件路径，空字符串表示不输出到文件"""
    return config.get("log_file", "")


def get_allow_wifi_off(config: Dict[str, Any]) -> bool:
    """是否允许关闭WiFi（用于节能模式），默认为False不关闭"""
    return config.get("allow_wifi_off", False)


def get_rotate_display(config: Dict[str, Any]) -> bool:
    """是否旋转180度显示"""
    return config.get("rotate_display", False)


def get_enable_time_sync(config: Dict[str, Any]) -> bool:
    """是否启用时间同步"""
    return config.get("enable_time_sync", True)


def get_sync_timeout(config: Dict[str, Any]) -> int:
    """时间同步超时时间（秒）"""
    return config.get("sync_timeout", 30)


def get_sync_on_boot(config: Dict[str, Any]) -> bool:
    """是否在开机时同步时间"""
    return config.get("sync_on_boot", True)


def get_sync_before_suspend(config: Dict[str, Any]) -> bool:
    """是否在休眠前同步到RTC"""
    return config.get("sync_before_suspend", True)
