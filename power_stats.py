#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
电量统计工具 - 查看电量追踪记录和统计信息

用法:
    python3 power_stats.py                 # 查看最近10条记录
    python3 power_stats.py --all           # 查看所有记录
    python3 power_stats.py --stats         # 查看统计信息
    python3 power_stats.py --last          # 查看最后一条记录
    python3 power_stats.py --days 7        # 查看最近7天的统计
"""

import sys
import os
import argparse
from datetime import datetime
from typing import List

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from power_manager import PowerRecord, create_power_tracker


def format_duration(seconds: float) -> str:
    """格式化时长"""
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.1f}min"
    else:
        hours = seconds / 3600
        return f"{hours:.1f}h"


def print_recent_records(tracker, count: int = 10):
    """打印最近记录"""
    records = tracker.get_recent_records(count)

    if not records:
        print("暂无电量记录")
        return

    print("=" * 80)
    print(
        f"{'任务ID':^8} | {'时间':^20} | {'电量变化':^10} | {'平均功率':^10} | {'耗时':^8} | {'充电'}"
    )
    print("-" * 80)

    for record in records:
        timestamp = datetime.fromisoformat(record.timestamp).strftime("%Y-%m-%d %H:%M")
        consumption = (
            f"-{record.net_consumption:.1f}%"
            if record.net_consumption > 0
            else f"+{abs(record.net_consumption):.1f}%"
        )
        charging_mark = "是" if record.charging else "否"
        print(
            f"{record.task_id:^8} | {timestamp:^20} | {consumption:^10} | "
            f"{record.avg_power:>6.2f}W | {format_duration(record.task_duration):^8} | {charging_mark}"
        )

    print("=" * 80)


def print_all_records(tracker):
    """打印所有记录"""
    records = tracker.get_all_records()

    if not records:
        print("暂无电量记录")
        return

    print("=" * 100)
    print(
        f"{'任务ID':^6} | {'时间':^20} | {'开始%':^8} | {'结束%':^8} | "
        f"{'消耗%':^8} | {'平均W':^8} | {'最大W':^8} | {'耗时':^10} | {'充电'}"
    )
    print("-" * 100)

    for record in records:
        timestamp = datetime.fromisoformat(record.timestamp).strftime(
            "%Y-%m-%d %H:%M:%S"
        )
        consumption = (
            f"-{record.net_consumption:.1f}%"
            if record.net_consumption > 0
            else f"+{abs(record.net_consumption):.1f}%"
        )
        charging_mark = "是" if record.charging else "否"
        print(
            f"{record.task_id:^6} | {timestamp:^20} | "
            f"{record.start_percentage:>6.1f}% | {record.end_percentage:>6.1f}% | "
            f"{consumption:^8} | {record.avg_power:>6.2f} | {record.max_power:>6.2f} | "
            f"{format_duration(record.task_duration):^10} | {charging_mark}"
        )

    print("=" * 100)
    print(f"共 {len(records)} 条记录")


def print_statistics(tracker, days: int = 7):
    """打印统计信息"""
    stats = tracker.get_statistics(days)

    if not stats:
        print("暂无统计数据")
        return

    print("=" * 60)
    print("电量消耗统计")
    print("=" * 60)
    print(f"统计周期: 最近 {days} 天 (或全部记录)")
    print("-" * 60)
    print(f"总任务次数:     {stats['total_tasks']}")
    print(f"平均消耗电量:   {stats['avg_consumption']:.2f}%")
    print(f"最大单次消耗:   {stats['max_consumption']:.2f}%")
    print(f"最小单次消耗:   {stats['min_consumption']:.2f}%")
    print(f"总消耗电量:     {stats['total_consumption']:.2f}%")
    print("-" * 60)
    print(f"平均功率:       {stats['avg_power']:.3f}W")
    print(f"最大功率:       {stats['max_power']:.3f}W")
    print(f"平均任务耗时:   {format_duration(stats['avg_duration'])}")
    print("-" * 60)
    if stats["estimated_battery_life"]:
        print(f"估算电池续航:   {stats['estimated_battery_life']}")
    print("=" * 60)


def print_last_record(tracker):
    """打印最后一条记录"""
    record = tracker.get_last_record()

    if not record:
        print("暂无电量记录")
        return

    print("=" * 60)
    print("最后一条电量记录")
    print("=" * 60)
    print(f"任务ID:         #{record.task_id}")
    print(
        f"时间:           {datetime.fromisoformat(record.timestamp).strftime('%Y-%m-%d %H:%M:%S')}"
    )
    print(f"充电状态:       {'是' if record.charging else '否'}")
    print(f"开始电量:       {record.start_percentage:.1f}%")
    print(f"结束电量:       {record.end_percentage:.1f}%")
    print(f"净消耗电量:     {record.net_consumption:.1f}%")
    print(f"开始电压:       {record.start_voltage:.3f}V")
    print(f"结束电压:       {record.end_voltage:.3f}V")
    print(f"平均功率:       {record.avg_power:.3f}W")
    print(f"最大功率:       {record.max_power:.3f}W")
    print(f"最小功率:       {record.min_power:.3f}W")
    print(f"任务耗时:       {format_duration(record.task_duration)}")
    print(f"结束时电流:     {record.current_ma:.1f}mA")
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(
        description="电量统计工具 - 查看电量追踪记录和统计信息",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
    python3 power_stats.py                 # 查看最近10条记录
    python3 power_stats.py --all           # 查看所有记录
    python3 power_stats.py --stats         # 查看统计信息
    python3 power_stats.py --last          # 查看最后一条记录
    python3 power_stats.py --days 7        # 查看最近7天的统计
        """,
    )

    parser.add_argument("--all", action="store_true", help="显示所有记录")
    parser.add_argument("--stats", action="store_true", help="显示统计信息")
    parser.add_argument("--last", action="store_true", help="显示最后一条记录")
    parser.add_argument("--days", type=int, default=7, help="统计天数 (默认: 7)")
    parser.add_argument("--count", type=int, default=10, help="显示记录数量 (默认: 10)")
    parser.add_argument(
        "--file", type=str, default="power_log.csv", help="日志文件路径"
    )

    args = parser.parse_args()

    script_dir = os.path.dirname(os.path.abspath(__file__))
    if args.file:
        log_file = os.path.join(script_dir, args.file)
    else:
        log_file = os.path.join(script_dir, "power_log.csv")

    if not os.path.exists(log_file):
        print(f"电量日志文件不存在: {log_file}")
        print("请先运行主程序以生成电量记录")
        sys.exit(1)

    try:
        tracker = create_power_tracker(log_file)
    except Exception as e:
        print(f"创建电量追踪器失败: {e}")
        sys.exit(1)

    if args.last:
        print_last_record(tracker)
    elif args.stats:
        print_statistics(tracker, args.days)
    elif args.all:
        print_all_records(tracker)
    else:
        print_recent_records(tracker, args.count)


if __name__ == "__main__":
    main()
