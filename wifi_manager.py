#!/usr/bin/env python3
# -*- coding:utf-8 -*-
import subprocess
import time
import logging

logger = logging.getLogger(__name__)


def wifi_on() -> bool:
    try:
        result = subprocess.run(
            ["nmcli", "radio", "wifi", "on"], capture_output=True, text=True, timeout=30
        )
        if result.returncode == 0:
            logger.info("WiFi enabled successfully")
            time.sleep(2)
            return True
        else:
            logger.error(f"Failed to enable WiFi: {result.stderr}")
            return False
    except Exception as e:
        logger.error(f"Error enabling WiFi: {e}")
        return False


def wifi_off() -> bool:
    try:
        result = subprocess.run(
            ["nmcli", "radio", "wifi", "off"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0:
            logger.info("WiFi disabled successfully")
            return True
        else:
            logger.error(f"Failed to disable WiFi: {result.stderr}")
            return False
    except Exception as e:
        logger.error(f"Error disabling WiFi: {e}")
        return False


def is_wifi_on() -> bool:
    try:
        result = subprocess.run(
            ["nmcli", "-t", "-f", "ACTIVE", "device", "show", "wlan0"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return "yes" in result.stdout.lower()
    except Exception as e:
        logger.error(f"Error checking WiFi status: {e}")
        return False
