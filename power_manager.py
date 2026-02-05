#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
电源检测模块 - INA219 电源监控芯片驱动

用于检测树莓派的充电状态和电源信息。
只支持 INA219 芯片，不支持系统文件检测。
包含电量追踪功能，记录每次任务的电量消耗。
"""

import logging
import time
import csv
import os
from datetime import datetime
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)

# 尝试导入 smbus
try:
    import smbus

    INA219_AVAILABLE = True
except ImportError:
    INA219_AVAILABLE = False
    smbus = None


# INA219 寄存器地址
_REG_CONFIG = 0x00
_REG_SHUNTVOLTAGE = 0x01
_REG_BUSVOLTAGE = 0x02
_REG_POWER = 0x03
_REG_CURRENT = 0x04
_REG_CALIBRATION = 0x05


class BusVoltageRange:
    RANGE_16V = 0x00
    RANGE_32V = 0x01


class Gain:
    DIV_1_40MV = 0x00
    DIV_2_80MV = 0x01
    DIV_4_160MV = 0x02
    DIV_8_320MV = 0x03


class ADCResolution:
    ADCRES_12BIT_32S = 0x0D


class Mode:
    SANDBVOLT_CONTINUOUS = 0x07


class INA219:
    """INA219 电源监控芯片驱动"""

    def __init__(self, i2c_bus: int = 1, addr: int = 0x43):
        """
        初始化 INA219

        Args:
            i2c_bus: I2C 总线编号（默认 1）
            addr: I2C 地址（默认 0x43）
        """
        if not INA219_AVAILABLE:
            raise ImportError(
                "smbus not installed. Install with: pip install smbus-cffi"
            )

        self.bus = smbus.SMBus(i2c_bus)
        self.addr = addr

        self._cal_value = 0
        self._current_lsb = 0
        self._power_lsb = 0

        self.set_calibration_16V_5A()
        logger.info(f"INA219 initialized at address 0x{addr:02X}")

    def _read_word(self, address: int) -> int:
        """读取一个字（2字节）"""
        data = self.bus.read_i2c_block_data(self.addr, address, 2)
        return (data[0] << 8) | data[1]

    def _write_word(self, address: int, data: int):
        """写入一个字（2字节）"""
        temp = [(data >> 8) & 0xFF, data & 0xFF]
        self.bus.write_i2c_block_data(self.addr, address, temp)

    def set_calibration_16V_5A(self):
        """配置 INA219 测量 16V 和 5A 电流"""
        self._current_lsb = 0.1524  # 100uA per bit
        self._cal_value = 26868
        self._power_lsb = 0.003048  # 2mW per bit

        self._write_word(_REG_CALIBRATION, self._cal_value)

        config = (
            BusVoltageRange.RANGE_16V << 13
            | Gain.DIV_2_80MV << 11
            | ADCResolution.ADCRES_12BIT_32S << 7
            | ADCResolution.ADCRES_12BIT_32S << 3
            | Mode.SANDBVOLT_CONTINUOUS
        )
        self._write_word(_REG_CONFIG, config)

    def get_shunt_voltage_mV(self) -> float:
        """获取分流电压（mV）"""
        self._write_word(_REG_CALIBRATION, self._cal_value)
        value = self._read_word(_REG_SHUNTVOLTAGE)
        if value > 32767:
            value -= 65535
        return value * 0.01

    def get_bus_voltage_V(self) -> float:
        """获取总线电压（V）"""
        self._write_word(_REG_CALIBRATION, self._cal_value)
        self._read_word(_REG_BUSVOLTAGE)
        return (self._read_word(_REG_BUSVOLTAGE) >> 3) * 0.004

    def get_current_mA(self) -> float:
        """获取电流（mA），负数=放电，正数=充电"""
        value = self._read_word(_REG_CURRENT)
        if value > 32767:
            value -= 65535
        return value * self._current_lsb

    def get_power_W(self) -> float:
        """获取功率（W）"""
        self._write_word(_REG_CALIBRATION, self._cal_value)
        value = self._read_word(_REG_POWER)
        if value > 32767:
            value -= 65535
        return value * self._power_lsb

    def get_battery_percentage(self) -> float:
        """
        获取电池剩余电量百分比

        基于总线电压估算：
        - 充满电约 4.2V
        - 完全放电约 3.0V
        """
        voltage = self.get_bus_voltage_V()

        if voltage >= 4.2:
            return 100.0
        elif voltage <= 3.0:
            return 0.0
        else:
            percentage = (voltage - 3.0) / 1.2 * 100
            return max(0, min(100, percentage))

    def is_charging(self) -> bool:
        """检测是否在充电状态（正电流=充电）"""
        return self.get_current_mA() > 0

    def get_status(self) -> Dict[str, Any]:
        """
        获取完整电源状态

        Returns:
            dict: 包含 voltage, current, power, percentage, charging
        """
        voltage = self.get_bus_voltage_V()
        current = self.get_current_mA() / 1000  # 转换为 A
        power = self.get_power_W()
        percentage = self.get_battery_percentage()
        charging = current > 0

        return {
            "voltage": voltage,
            "current": current,
            "power": power,
            "percentage": percentage,
            "charging": charging,
        }


def create_power_manager(addr: int = 0x43) -> Optional[INA219]:
    """
    创建电源管理器

    Args:
        addr: INA219 I2C 地址

    Returns:
        INA219 实例，失败返回 None
    """
    if not INA219_AVAILABLE:
        logger.warning("smbus not installed")
        return None

    try:
        return INA219(addr=addr)
    except Exception as e:
        logger.warning(f"Failed to create PowerManager: {e}")
        return None


@dataclass
class PowerRecord:
    """单次电量记录"""

    timestamp: str
    task_id: int
    start_percentage: float
    end_percentage: float
    net_consumption: float
    start_voltage: float
    end_voltage: float
    avg_power: float
    max_power: float
    min_power: float
    task_duration: float
    charging: bool
    current_ma: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class PowerTracker:
    """电量追踪器 - 记录每次任务的电量消耗"""

    CSV_HEADERS = [
        "timestamp",
        "task_id",
        "start_percentage",
        "end_percentage",
        "net_consumption",
        "start_voltage",
        "end_voltage",
        "avg_power",
        "max_power",
        "min_power",
        "task_duration",
        "charging",
        "current_ma",
    ]

    def __init__(self, log_file: str = "power_log.csv"):
        """
        初始化电量追踪器

        Args:
            log_file: 日志文件路径
        """
        self.log_file = log_file
        self.current_task_id = self._load_last_task_id() + 1
        self.current_record: Optional[PowerRecord] = None
        self.power_samples: List[Dict[str, Any]] = []
        self.task_start_time: Optional[float] = None
        self._init_log_file()

    def _init_log_file(self):
        """初始化日志文件"""
        if not os.path.exists(self.log_file):
            try:
                with open(self.log_file, "w", newline="", encoding="utf-8") as f:
                    writer = csv.DictWriter(f, fieldnames=self.CSV_HEADERS)
                    writer.writeheader()
                logger.info(f"Created power log file: {self.log_file}")
            except Exception as e:
                logger.warning(f"Failed to create power log file: {e}")

    def _load_last_task_id(self) -> int:
        """加载最后一个任务ID"""
        if not os.path.exists(self.log_file):
            return 0
        try:
            with open(self.log_file, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                last_id = 0
                for row in reader:
                    try:
                        last_id = int(row.get("task_id", 0))
                    except ValueError:
                        pass
                return last_id
        except Exception:
            return 0

    def start_task(self, power_manager: Optional[INA219] = None):
        """
        开始记录任务电量

        Args:
            power_manager: INA219 实例
        """
        self.task_start_time = time.time()
        self.power_samples = []

        if power_manager:
            try:
                status = power_manager.get_status()
                self.power_samples.append(
                    {
                        "time": 0,
                        "power": status["power"],
                        "voltage": status["voltage"],
                        "current": status["current"] * 1000,
                        "percentage": status["percentage"],
                    }
                )
            except Exception as e:
                logger.warning(f"Failed to read initial power status: {e}")

        logger.info(f"Power tracking started for task #{self.current_task_id}")

    def sample_power(
        self, power_manager: Optional[INA219] = None, task_stage: str = ""
    ):
        """
        在任务执行过程中采样电源数据

        Args:
            power_manager: INA219 实例
            task_stage: 当前任务阶段标识
        """
        if not power_manager or not self.task_start_time:
            return

        try:
            elapsed = time.time() - self.task_start_time
            status = power_manager.get_status()
            self.power_samples.append(
                {
                    "time": elapsed,
                    "power": status["power"],
                    "voltage": status["voltage"],
                    "current": status["current"] * 1000,
                    "percentage": status["percentage"],
                    "stage": task_stage,
                }
            )
        except Exception as e:
            logger.warning(f"Failed to sample power: {e}")

    def end_task(
        self, power_manager: Optional[INA219] = None, charging: bool = False
    ) -> Optional[PowerRecord]:
        """
        结束任务电量记录

        Args:
            power_manager: INA219 实例
            charging: 任务执行期间是否在充电

        Returns:
            PowerRecord 实例，失败返回 None
        """
        if not self.task_start_time:
            logger.warning("No active task to end")
            return None

        task_end_time = time.time()
        task_duration = task_end_time - self.task_start_time

        if power_manager:
            try:
                status = power_manager.get_status()
                self.power_samples.append(
                    {
                        "time": task_duration,
                        "power": status["power"],
                        "voltage": status["voltage"],
                        "current": status["current"] * 1000,
                        "percentage": status["percentage"],
                    }
                )
            except Exception as e:
                logger.warning(f"Failed to read final power status: {e}")

        start_percentage = (
            self.power_samples[0]["percentage"] if self.power_samples else 0
        )
        end_percentage = (
            self.power_samples[-1]["percentage"]
            if self.power_samples
            else start_percentage
        )

        powers = [s["power"] for s in self.power_samples if "power" in s]
        avg_power = sum(powers) / len(powers) if powers else 0
        max_power = max(powers) if powers else 0
        min_power = min(powers) if powers else 0

        net_consumption = start_percentage - end_percentage
        if charging:
            net_consumption = -net_consumption

        start_voltage = self.power_samples[0]["voltage"] if self.power_samples else 0
        end_voltage = (
            self.power_samples[-1]["voltage"] if self.power_samples else start_voltage
        )
        current_ma = self.power_samples[-1]["current"] if self.power_samples else 0

        self.current_record = PowerRecord(
            timestamp=datetime.now().isoformat(),
            task_id=self.current_task_id,
            start_percentage=start_percentage,
            end_percentage=end_percentage,
            net_consumption=round(net_consumption, 2),
            start_voltage=round(start_voltage, 3),
            end_voltage=round(end_voltage, 3),
            avg_power=round(avg_power, 3),
            max_power=round(max_power, 3),
            min_power=round(min_power, 3),
            task_duration=round(task_duration, 2),
            charging=charging,
            current_ma=round(current_ma, 1),
        )

        self._save_record(self.current_record)
        logger.info(f"Power tracking ended for task #{self.current_task_id}")
        logger.info(
            f"Task #{self.current_task_id}: consumed {self.current_record.net_consumption:.1f}%, "
            f"avg power {self.current_record.avg_power:.2f}W, duration {self.current_record.task_duration:.1f}s"
        )

        self.current_task_id += 1
        self.task_start_time = None
        self.power_samples = []

        return self.current_record

    def _save_record(self, record: PowerRecord):
        """保存记录到 CSV 文件"""
        try:
            file_exists = os.path.exists(self.log_file)
            with open(self.log_file, "a", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=self.CSV_HEADERS)
                if not file_exists:
                    writer.writeheader()
                writer.writerow(record.to_dict())
        except Exception as e:
            logger.warning(f"Failed to save power record: {e}")

    def get_recent_records(self, count: int = 10) -> List[PowerRecord]:
        """获取最近的记录"""
        records = []
        if not os.path.exists(self.log_file):
            return records

        try:
            with open(self.log_file, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    records.append(PowerRecord(**row))
        except Exception as e:
            logger.warning(f"Failed to read power log: {e}")

        return records[-count:] if len(records) > count else records

    def get_statistics(self, days: int = 7) -> Dict[str, Any]:
        """获取统计信息"""
        records = self.get_all_records()
        if not records:
            return {}

        cutoff = datetime.now().timestamp() - (days * 24 * 60 * 60)
        recent_records = [
            r
            for r in records
            if datetime.fromisoformat(r.timestamp).timestamp() > cutoff
        ]

        if not recent_records:
            recent_records = records[-30:] if len(records) > 30 else records

        consumptions = [abs(r.net_consumption) for r in recent_records]
        powers = [r.avg_power for r in recent_records]
        durations = [r.task_duration for r in recent_records]

        return {
            "total_tasks": len(recent_records),
            "avg_consumption": round(sum(consumptions) / len(consumptions), 2)
            if consumptions
            else 0,
            "max_consumption": round(max(consumptions), 2) if consumptions else 0,
            "min_consumption": round(min(consumptions), 2) if consumptions else 0,
            "avg_power": round(sum(powers) / len(powers), 3) if powers else 0,
            "max_power": round(max(powers), 3) if powers else 0,
            "avg_duration": round(sum(durations) / len(durations), 1)
            if durations
            else 0,
            "total_consumption": round(sum(consumptions), 2),
            "estimated_battery_life": self._estimate_battery_life(recent_records),
        }

    def _estimate_battery_life(self, records: List[PowerRecord]) -> Optional[str]:
        """估算电池续航时间（基于最近的放电记录）"""
        discharge_records = [
            r for r in records if not r.charging and r.net_consumption > 0
        ]
        if not discharge_records:
            return None

        avg_consumption = sum(r.net_consumption for r in discharge_records) / len(
            discharge_records
        )
        if avg_consumption <= 0:
            return None

        avg_interval_hours = 8
        total_cycles = 100 / avg_consumption
        total_hours = total_cycles * avg_interval_hours
        total_days = total_hours / 24

        return f"{total_days:.1f} 天 (约 {total_cycles:.0f} 次循环)"

    def get_all_records(self) -> List[PowerRecord]:
        """获取所有记录"""
        records = []
        if not os.path.exists(self.log_file):
            return records

        try:
            with open(self.log_file, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    try:
                        row["task_id"] = int(row["task_id"])
                        row["start_percentage"] = float(row["start_percentage"])
                        row["end_percentage"] = float(row["end_percentage"])
                        row["net_consumption"] = float(row["net_consumption"])
                        row["start_voltage"] = float(row["start_voltage"])
                        row["end_voltage"] = float(row["end_voltage"])
                        row["avg_power"] = float(row["avg_power"])
                        row["max_power"] = float(row["max_power"])
                        row["min_power"] = float(row["min_power"])
                        row["task_duration"] = float(row["task_duration"])
                        row["charging"] = row["charging"] == "True"
                        row["current_ma"] = float(row["current_ma"])
                        records.append(PowerRecord(**row))
                    except (ValueError, KeyError) as e:
                        logger.warning(f"Skipping invalid record: {e}")
        except Exception as e:
            logger.warning(f"Failed to read power log: {e}")

        return records

    def get_last_record(self) -> Optional[PowerRecord]:
        """获取最后一条记录"""
        records = self.get_recent_records(1)
        return records[0] if records else None


def create_power_tracker(log_file: str = "power_log.csv") -> PowerTracker:
    """创建电量追踪器"""
    return PowerTracker(log_file=log_file)


if __name__ == "__main__":
    import sys

    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
    )

    print("=" * 60)
    print("INA219 电源监控测试")
    print("=" * 60)

    ina219 = create_power_manager(addr=0x43)
    if not ina219:
        print("\n错误: 无法初始化 INA219，请检查:")
        print("  1. INA219 芯片是否正确连接")
        print("  2. I2C 地址是否正确（默认 0x43）")
        print("  3. 是否安装了 smbus: pip install smbus-cffi")
        sys.exit(1)

    while True:
        status = ina219.get_status()
        shunt_v = ina219.get_shunt_voltage_mV() / 1000

        psu_voltage = status["voltage"] + shunt_v
        status_text = "充电中" if status["charging"] else "放电中"

        print(f"\nPSU 电压:   {psu_voltage:6.3f} V")
        print(f"总线电压:   {status['voltage']:6.3f} V")
        print(f"分流电压:   {shunt_v:9.6f} V")
        print(f"电流:       {status['current'] * 1000:6.1f} mA ({status_text})")
        print(f"功率:       {status['power']:6.3f} W")
        print(f"电量:       {status['percentage']:3.1f}%")

        time.sleep(2)
