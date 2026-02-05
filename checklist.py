#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
Photo Painter Show - 功能检查清单
用法:
    python3 checklist.py --simulate    # 模拟模式 (默认)
    python3 checklist.py --hardware    # 真实硬件模式
"""

import os
import sys
import json
import subprocess
import argparse
from datetime import datetime

if sys.platform == "win32":
    import io

    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")


class Colors:
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    END = "\033[0m"
    BOLD = "\033[1m"


CHECKLIST = {
    "CONFIG": {
        "name": "配置模块",
        "checks": [
            ("config.json 文件存在", "file_exists", False),
            ("JSON 格式正确", "json_valid", False),
            ("必要字段完整", "config_complete", False),
        ],
    },
    "WIFI": {
        "name": "WiFi 控制",
        "checks": [
            ("nmcli 可用", "command_exists nmcli", True),
            ("wifi_on() 返回 True", "wifi_on", True),
            # ("wifi_off() 返回 True", "wifi_off", True),
        ],
    },
    "FETCHER": {
        "name": "图片下载",
        "checks": [
            ("requests 库可用", "import requests", False),
            ("download_image() 函数存在", "import fetcher", False),
            ("模拟下载测试", "mock_download", False),
        ],
    },
    "SCHEDULER": {
        "name": "RTC 调度",
        "checks": [
            ("get_next_wake_time() 有效", "scheduler_check", False),
            ("时间戳 > 当前时间", "timestamp_check", False),
        ],
    },
    "POWER": {
        "name": "电源监控 (INA219)",
        "checks": [
            ("smbus 库可用", "import smbus", False),
            ("power_manager.py 可导入", "import power_manager", False),
            ("INA219 芯片检测", "ina219_detect", True),
            ("电源状态读取", "ina219_read_status", True),
        ],
    },
    "DISPLAY": {
        "name": "墨水屏显示",
        "checks": [
            ("display.py 脚本存在", "file_exists display/display.py", False),
            ("external 脚本检查", "external_script_exists", True),
            ("display_picture.py 可执行", "display_script_runnable", True),
        ],
    },
    "MAIN": {
        "name": "主程序",
        "checks": [
            ("main.py 可导入", "import main", False),
            ("execute_task() 函数存在", "execute_task_exists", False),
        ],
    },
    "SYSTEM": {
        "name": "系统工具",
        "checks": [
            ("Python3 可用", "command_exists python3", True),
            ("rtcwake 可用", "command_exists rtcwake", True),
            ("systemctl 可用", "command_exists systemctl", True),
        ],
    },
}


def get_project_dir():
    return os.path.dirname(os.path.abspath(__file__))


def file_exists(path):
    full_path = os.path.join(get_project_dir(), path)
    return os.path.exists(full_path)


def json_valid():
    config_path = os.path.join(get_project_dir(), "config.json")
    if not os.path.exists(config_path):
        return False, "config.json 不存在"
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            json.load(f)
        return True, None
    except json.JSONDecodeError as e:
        return False, f"JSON 格式错误: {e}"


def config_complete():
    try:
        from config import load_config

        config = load_config()
        required_keys = [
            "schedule",
            "image_url",
            "display_model",
            "work_dir",
            "output_dir",
        ]
        missing = [k for k in required_keys if k not in config]
        if missing:
            return False, f"缺少字段: {missing}"
        return True, None
    except Exception as e:
        return False, str(e)


def command_exists(cmd):
    try:
        result = subprocess.run(
            ["which", cmd], capture_output=True, text=True, timeout=10
        )
        return (
            result.returncode == 0,
            None if result.returncode == 0 else f"{cmd} 未找到",
        )
    except Exception as e:
        return False, str(e)


def wifi_on():
    try:
        from wifi_manager import wifi_on as wifi_on_func

        result = wifi_on_func()
        return result, None if result else "wifi_on() 返回 False"
    except Exception as e:
        return False, str(e)


def wifi_off():
    try:
        from wifi_manager import wifi_off as wifi_off_func

        result = wifi_off_func()
        return result, None if result else "wifi_off() 返回 False"
    except Exception as e:
        return False, str(e)


def import_requests():
    try:
        import requests

        return True, None
    except ImportError:
        return False, "requests 库未安装"


def import_fetcher():
    try:
        import fetcher

        return hasattr(fetcher, "download_image"), "download_image 函数不存在"
    except Exception as e:
        return False, str(e)


def mock_download():
    try:
        import fetcher

        if hasattr(fetcher, "download_image"):
            return True, None
        return False, "download_image 函数不存在"
    except Exception as e:
        return False, str(e)


def scheduler_check():
    try:
        from scheduler import get_next_wake_time

        config = {"schedule": ["05:00", "13:00", "18:00"]}
        schedule = [config["schedule"][0]] if config["schedule"] else []
        result = get_next_wake_time(schedule)
        return isinstance(result, int) and result > 0, f"返回无效值: {result}"
    except Exception as e:
        return False, str(e)


def timestamp_check():
    try:
        from scheduler import get_next_wake_time, get_current_timestamp

        config = {"schedule": ["05:00", "13:00", "18:00"]}
        schedule = config["schedule"][:1] if config["schedule"] else ["05:00"]
        next_ts = get_next_wake_time(schedule)
        now = get_current_timestamp()
        return next_ts > now, f"时间戳 {next_ts} <= 当前时间 {now}"
    except Exception as e:
        return False, str(e)


def import_smbus():
    try:
        import smbus

        return True, None
    except ImportError:
        return False, "smbus 库未安装 (pip install smbus-cffi)"


def import_power_manager():
    try:
        import power_manager

        return hasattr(power_manager, "create_power_manager"), "create_power_manager 函数不存在"
    except Exception as e:
        return False, str(e)


def ina219_detect():
    try:
        from power_manager import create_power_manager

        pm = create_power_manager()
        if pm is None:
            return False, "INA219 芯片未检测到或初始化失败"
        return True, None
    except Exception as e:
        return False, str(e)


def ina219_read_status():
    try:
        from power_manager import create_power_manager

        pm = create_power_manager()
        if pm is None:
            return None, "INA219 不可用，跳过"
        status = pm.get_status()
        required_keys = ["voltage", "current", "power", "percentage", "charging"]
        missing = [k for k in required_keys if k not in status]
        if missing:
            return False, f"返回数据缺少字段: {missing}"
        return True, f"电压={status['voltage']:.2f}V, 电量={status['percentage']:.0f}%"
    except Exception as e:
        return False, str(e)


def external_script_exists():
    try:
        from config import load_config

        config = load_config()
        script_path = config.get("display_script_path", "")
        if not script_path:
            return None, "未配置 external 脚本路径"
        if not os.path.exists(script_path):
            return False, f"脚本不存在: {script_path}"
        return True, None
    except Exception as e:
        return False, str(e)


def display_script_runnable():
    try:
        from config import load_config

        config = load_config()
        script_path = config.get("display_script_path", "")
        if not script_path:
            return None, "未配置 display 脚本路径"
        result = subprocess.run(
            [sys.executable, script_path, "--help"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return result.returncode in [0, 2], f"脚本执行失败"
    except Exception as e:
        return False, str(e)


def import_main():
    try:
        import main

        return True, None
    except Exception as e:
        return False, str(e)


def execute_task_exists():
    try:
        import main

        return hasattr(main, "execute_task"), "execute_task 函数不存在"
    except Exception as e:
        return False, str(e)


CHECK_FUNCTIONS = {
    "file_exists": lambda: file_exists("config.json"),
    "json_valid": json_valid,
    "config_complete": config_complete,
    "command_exists nmcli": lambda: command_exists("nmcli"),
    "wifi_on": wifi_on,
    # "wifi_off": wifi_off,
    "import requests": import_requests,
    "import fetcher": import_fetcher,
    "mock_download": mock_download,
    "scheduler_check": scheduler_check,
    "timestamp_check": timestamp_check,
    "import smbus": import_smbus,
    "import power_manager": import_power_manager,
    "ina219_detect": ina219_detect,
    "ina219_read_status": ina219_read_status,
    "file_exists display/display.py": lambda: file_exists("display/display.py"),
    "external_script_exists": external_script_exists,
    "display_script_runnable": display_script_runnable,
    "import main": import_main,
    "execute_task_exists": execute_task_exists,
    "command_exists python3": lambda: command_exists("python3"),
    "command_exists rtcwake": lambda: command_exists("rtcwake"),
    "command_exists systemctl": lambda: command_exists("systemctl"),
}


def run_check(check_name, check_func, is_hardware, is_hardware_mode):
    if is_hardware and not is_hardware_mode:
        return "-", check_name, "跳过-模拟模式", False

    try:
        result = check_func()
        if isinstance(result, tuple):
            success, msg = result
            if success is None:
                return "-", check_name, msg or "跳过", False
            elif success:
                return "✓", check_name, None, False
            else:
                return "✗", check_name, msg or "失败", False
        elif result:
            return "✓", check_name, None, False
        else:
            return "✗", check_name, "返回 False", False
    except Exception as e:
        return "✗", check_name, str(e), False


def print_header():
    print()
    print(f"{Colors.BOLD}{'=' * 50}{Colors.END}")
    print(f"{Colors.BOLD}     Photo Painter Show - 功能检查清单{Colors.END}")
    print(f"{Colors.BOLD}{'=' * 50}{Colors.END}")
    print()


def print_section(category, results, is_hardware_mode):
    category_info = CHECKLIST[category]
    section_name = category_info["name"]
    if any(len(r) > 3 and r[3] for r in results):
        section_name += f" {Colors.YELLOW}[需要硬件]{Colors.END}"
    print(f"{Colors.BLUE}[{category}]{Colors.END} {section_name}")

    for item in results:
        if len(item) == 4:
            symbol, check_name, msg, _ = item
        else:
            symbol, check_name, msg = item
        if symbol == "✓":
            symbol_str = f"{Colors.GREEN}✓{Colors.END}"
        elif symbol == "✗":
            symbol_str = f"{Colors.RED}✗{Colors.END}"
        else:
            symbol_str = f"{Colors.YELLOW}-{Colors.END}"

        print(f"  {symbol_str} {check_name}")
        if msg:
            print(f"      {Colors.YELLOW}{msg}{Colors.END}")
    print()


def print_summary(passed, failed, skipped):
    total = passed + failed + skipped
    print(f"{Colors.BOLD}{'=' * 50}{Colors.END}")
    print(
        f"{Colors.BOLD}总计: {passed} 项通过, {failed} 项失败, {skipped} 项跳过{Colors.END}"
    )
    print(f"{Colors.BOLD}{'=' * 50}{Colors.END}")
    print()
    print(
        f"使用: {Colors.BLUE}python3 checklist.py --simulate{Colors.END}   # 模拟模式 (默认)"
    )
    print(
        f"     {Colors.BLUE}python3 checklist.py --hardware{Colors.END}   # 真实硬件模式"
    )
    print()


def main():
    parser = argparse.ArgumentParser(description="Photo Painter Show 功能检查")
    parser.add_argument("--hardware", action="store_true", help="真实硬件模式")
    parser.add_argument("--simulate", action="store_true", help="模拟模式 (默认)")
    args = parser.parse_args()

    is_hardware_mode = args.hardware

    print_header()

    all_passed = 0
    all_failed = 0
    all_skipped = 0

    for category, category_info in CHECKLIST.items():
        results = []

        for check_name, check_key, is_hardware in category_info["checks"]:
            check_func = CHECK_FUNCTIONS.get(check_key)
            if check_func is None:
                results.append(("✗", check_name, f"检查函数不存在: {check_key}"))
                all_failed += 1
                continue

            symbol, name, msg, is_hw = run_check(
                check_name, check_func, is_hardware, is_hardware_mode
            )

            if symbol == "✓":
                all_passed += 1
            elif symbol == "✗":
                all_failed += 1
            else:
                all_skipped += 1

            results.append((symbol, name, msg, is_hw))

        print_section(category, results, is_hardware_mode)

    print_summary(all_passed, all_failed, all_skipped)

    return 0 if all_failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
