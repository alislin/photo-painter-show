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
