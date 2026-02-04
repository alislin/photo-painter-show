# Photo Painter Show

定时图片显示系统，用于树莓派Zero 2W + DS3231 RTC + 墨水屏。

## 硬件环境

- 树莓派 Zero 2W (aarch64)
- DS3231 RTC 模块
- Waveshare 7.3" e-Paper (epd7in3e, 800x480)
- Debian GNU/Linux

## 项目结构

```
photo-painter-show/
├── config.py              # 配置加载模块
├── wifi_manager.py        # WiFi控制模块
├── fetcher.py            # 图片下载模块
├── scheduler.py          # RTC调度模块
├── power_manager.py      # INA219电源监控模块
├── serial_manager.py     # 串口检测模块
├── main.py               # 主程序入口
├── display/              # 显示模块
│   └── display.py       # 简化版显示脚本
├── config.json           # 用户配置文件
├── requirements.txt      # Python依赖
├── photo-painter.service # systemd服务
├── checklist.py          # 功能检查清单
└── docs/
    └── PLAN.md          # 开发计划文档
```

## 安装

### 1. 准备环境

```bash
# 克隆或上传源码到树莓派
cd ~

# 进入项目目录
cd photo-painter-show

# 安装 Python 依赖
pip install -r requirements.txt
```

### 2. 墨水屏驱动依赖

确保已安装 Waveshare 官方驱动：

```bash
# 进入墨水屏驱动目录
cd /home/pi/Waveshare_E-Paper/RaspberryPi_JetsonNano/python

# 安装驱动依赖
pip install -r requirements.txt
```

### 3. 文件权限

```bash
# 确保主程序可执行
chmod +x main.py checklist.py display/display.py

# 创建输出目录
mkdir -p output_dir
```

## 配置

编辑 `config.json`:

```json
{
  "schedule": ["05:00", "13:00", "18:00"],
  "image_url": "https://your-server/picture.jpg",
  "display_model": "epd7in3e",
  "work_dir": "/home/pi/photo-painter-show",
  "output_dir": "/home/pi/photo-painter-show/output_dir",
  "display_script_path": "/home/pi/Waveshare_E-Paper/RaspberryPi_JetsonNano/python/main.py",
  "log_level": "INFO",
  "debug_mode": false
}
```

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| schedule | 执行时间列表 (HH:MM格式) | - |
| image_url | 图片下载URL | - |
| display_model | 墨水屏型号 (epd7in3e等) | - |
| work_dir | 工作目录 | - |
| output_dir | 图片输出目录 | - |
| display_script_path | 墨水屏官方驱动脚本路径 | "" |
| log_level | 日志级别: DEBUG, INFO, WARNING, ERROR | "INFO" |
| debug_mode | 调试模式（预留） | false |

## 使用

### 手动运行测试

```bash
# 模拟模式测试（无需硬件）
python3 checklist.py --simulate

# 真实硬件测试（在树莓派上执行）
python3 checklist.py --hardware

# 手动运行一次任务
python3 main.py
```

### 安装系统服务

```bash
# 复制服务文件
sudo cp photo-painter.service /etc/systemd/system/

# 启用开机自启
sudo systemctl enable photo-painter.service

# 启动服务
sudo systemctl start photo-painter.service
```

### 服务管理命令

| 命令 | 说明 |
|------|------|
| `sudo systemctl start photo-painter` | 启动服务 |
| `sudo systemctl stop photo-painter` | 停止服务 |
| `sudo systemctl restart photo-painter` | 重启服务 |
| `sudo systemctl status photo-painter` | 查看服务状态 |
| `sudo systemctl enable photo-painter` | 启用开机自启 |
| `sudo systemctl disable photo-painter` | 禁用开机自启 |
| `journalctl -u photo-painter -f` | 实时查看日志 |

## 工作流程

```
RTC闹钟触发 → 系统启动
    ↓
读取配置
    ↓
WiFi开 → 下载图片 → WiFi关
    ↓
调用显示脚本
    ↓
rtcwake -m off  # 系统深度休眠
```

## 省电说明

- 系统使用 `rtcwake -m off` 实现深度休眠
- 仅RTC模块供电，功耗极低
- 定时时间到达后自动开机执行任务

## 电源监控

### INA219 电源监控芯片

支持通过 INA219 芯片检测充电状态，实现智能省电：

- **充电中**：执行任务后**不休眠**，保持运行状态
- **未充电**：正常执行任务后进入深度休眠

### 硬件连接

INA219 默认 I2C 地址：`0x43`

```
树莓派          INA219
-----          ------
GPIO 2 (SDA) -> SDA
GPIO 3 (SCL) -> SCL
3.3V/5V     -> VCC
GND         -> GND
```

### 安装依赖

```bash
sudo apt install python3-smbus
pip install smbus-cffi
```

### 测试电源监控

```bash
python3 power_manager.py
```

输出示例：

```
============================================================
INA219 电源监控测试
============================================================

PSU 电压:   5.123 V
总线电压:   4.987 V
分流电压:   0.136 V
电流:       523.0 mA (充电中)
功率:       2.607 W
电量:       78.5%
```

### 充电状态判断

| 电流方向 | 状态 |
|----------|------|
| 正电流 (> 0 mA) | 充电中 |
| 负电流 (< 0 mA) | 放电中（树莓派负载） |

## 文件说明

| 文件 | 功能 |
|------|------|
| config.py | 加载config.json配置 |
| wifi_manager.py | nmcli控制WiFi开关 |
| fetcher.py | 下载图片到本地 |
| scheduler.py | 计算下次执行时间的Unix时间戳 |
| power_manager.py | INA219电源监控芯片驱动 |
| serial_manager.py | 串口连接检测模块 |
| main.py | 主程序，协调各模块 |
| display/display.py | 简化版墨水屏显示脚本 |
| checklist.py | 功能检查清单（测试工具） |

## 功能测试

提供 `checklist.py` 脚本用于逐项验证各模块功能。

### 模拟模式

无需硬件环境，验证代码逻辑是否正常：

```bash
python3 checklist.py --simulate
```

输出示例：

```
========================================
     Photo Painter Show - 功能检查清单
========================================

[CONFIG] 配置模块
  ✓ config.json 文件存在
  ✓ JSON 格式正确
  ✓ 必要字段完整

[WIFI] WiFi 控制 [需要硬件]
  - nmcli 可用 [跳过-模拟模式]
  - wifi_on() 返回 True [跳过-模拟模式]

[FETCHER] 图片下载
  ✓ requests 库可用
  ✓ download_image() 函数存在
  ✓ 模拟下载测试

[SCHEDULER] RTC 调度
  ✓ get_next_wake_time() 有效
  ✓ 时间戳 > 当前时间

[DISPLAY] 墨水屏显示
  ✓ display.py 脚本存在
  - external 脚本检查 [跳过-模拟模式]

[MAIN] 主程序
  ✓ main.py 可导入
  ✓ execute_task() 函数存在

[SYSTEM] 系统工具 [需要硬件]
  - Python3 可用 [跳过-模拟模式]
  - rtcwake 可用 [跳过-模拟模式]
  - systemctl 可用 [跳过-模拟模式]

========================================
总计: 11 项通过, 0 项失败, 8 项跳过
========================================
```

### 真实硬件模式

在树莓派上运行，测试实际硬件交互：

```bash
python3 checklist.py --hardware
```

### 检查项目说明

| 模块 | 检查内容 | 模式 |
|------|----------|------|
| CONFIG | 配置文件存在性、JSON格式、字段完整性 | 模拟 |
| WIFI | nmcli可用性、WiFi开关函数 | 硬件 |
| FETCHER | requests库、下载函数、模拟下载测试 | 模拟 |
| SCHEDULER | 时间计算函数有效性 | 模拟 |
| DISPLAY | 显示脚本存在性、可执行性 | 混合 |
| MAIN | 主程序导入、函数存在性 | 模拟 |
| SYSTEM | Python3、rtcwake、systemctl可用性 | 硬件 |
