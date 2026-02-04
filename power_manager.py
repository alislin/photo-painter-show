#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
电源检测模块 - INA219 电源监控芯片驱动

用于检测树莓派的充电状态和电源信息。
只支持 INA219 芯片，不支持系统文件检测。
"""

import logging
import time
from typing import Dict, Any, Optional

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
            raise ImportError("smbus not installed. Install with: pip install smbus-cffi")

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
            BusVoltageRange.RANGE_16V << 13 |
            Gain.DIV_2_80MV << 11 |
            ADCResolution.ADCRES_12BIT_32S << 7 |
            ADCResolution.ADCRES_12BIT_32S << 3 |
            Mode.SANDBVOLT_CONTINUOUS
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


if __name__ == "__main__":
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s"
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
        print(f"电流:       {status['current']*1000:6.1f} mA ({status_text})")
        print(f"功率:       {status['power']:6.3f} W")
        print(f"电量:       {status['percentage']:3.1f}%")

        time.sleep(2)
