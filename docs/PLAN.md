# Photo Painter Show - 定时图片显示方案

## 项目概述

在树莓派Zero 2W上实现定时图片显示功能，通过RTC唤醒实现极致省电。

## 硬件环境

| 组件 | 型号/说明 |
|------|----------|
| 开发板 | 树莓派 Zero 2W |
| 操作系统 | Debian GNU/Linux (aarch64) |
| RTC模块 | DS3231 |
| 显示屏 | Waveshare 7.3 inch e-Paper (epd7in3e, 800x480) |
| WiFi管理 | NetworkManager (nmcli) |

## 系统架构

```
photo-painter-show/
├── config.py              # 配置加载模块
├── wifi_manager.py        # WiFi控制模块
├── fetcher.py             # 图片下载模块
├── scheduler.py           # RTC调度模块
├── main.py                # 主程序入口
├── display_picture.py     # 显示脚本（已存在）
├── config.json            # 用户配置文件
├── requirements.txt       # Python依赖
└── photo-painter.service # systemd服务
```

## 工作流程

```
RTC闹钟触发 → 系统启动
    ↓
main.py: 读取配置
    ↓
执行任务:
  1. nmcli radio wifi on     # 打开WiFi
  2. 下载图片 → /tmp/latest_image.jpg
  3. nmcli radio wifi off    # 关闭WiFi
  4. python3 display_picture.py -m epd7in3e /tmp/latest_image.jpg -o ./output_dir
    ↓
计算下次执行时间
    ↓
rtcwake -m off -t <timestamp>  # 系统深度休眠
```

## 模块设计

### 1. config.py

```python
# 功能: 加载config.json配置
load_config() -> Dict[str, Any]  # 返回配置字典
get_schedule() -> List[str]     # 获取时间列表
get_image_url() -> str          # 获取图片URL
get_display_model() -> str      # 获取显示屏型号
get_work_dir() -> str           # 获取工作目录
get_output_dir() -> str         # 获取输出目录
```

### 2. wifi_manager.py

```python
# 功能: 控制WiFi开关
wifi_on()  -> bool  # nmcli radio wifi on
wifi_off() -> bool  # nmcli radio wifi off
is_wifi_on() -> bool  # 检查WiFi状态
```

### 3. fetcher.py

```python
# 功能: 下载图片
download_image(url: str, save_path: str, timeout: int = 60) -> bool
download_with_retry(url: str, save_path: str, max_retries: int = 3) -> bool
```

### 4. scheduler.py

```python
# 功能: 计算下一次执行时间的Unix时间戳
get_next_wake_time(schedule_list: List[str]) -> int  # 返回Unix时间戳
format_next_wake_time(timestamp: int) -> str        # 格式化时间字符串
calculate_sleep_duration(wake_timestamp: int) -> float
```

### 5. main.py

```python
# 主循环:
# 1. 读取配置
# 2. 执行WiFi开→下载→WiFi关
# 3. 调用显示脚本
# 4. 设置RTC闹钟
# 5. 执行rtcwake休眠
```

## 配置文件 config.json

```json
{
  "schedule": ["05:00", "13:00", "18:00"],
  "image_url": "https://example.com/picture.jpg",
  "display_model": "epd7in3e",
  "work_dir": "/home/pi/photo-painter-show",
  "output_dir": "/home/pi/photo-painter-show/output_dir"
}
```

| 配置项 | 说明 | 默认值 |
|-------|------|--------|
| schedule | 执行时间列表 (HH:MM格式) | ["05:00", "13:00", "18:00"] |
| image_url | 图片下载URL | - |
| display_model | 墨水屏型号 |3e |
| epd7in work_dir | 工作目录 | /home/pi/photo-painter-show |
| output_dir | 图片输出目录 | ./output_dir |

## 显示脚本调用

```bash
python3 display_picture.py -m epd7in3e /tmp/latest_image.jpg -o ./output_dir
```

## 依赖

### Python包 (requirements.txt)

```
requests
```

### 系统依赖

- NetworkManager (`nmcli`)
- util-linux (`rtcwake`)
- OpenCV, PIL, numpy (显示脚本已依赖)

## 安装步骤

```bash
# 1. 克隆项目
git clone <repo_url>
cd photo-painter-show

# 2. 安装Python依赖
pip install -r requirements.txt

# 3. 配置config.json
nano config.json

# 4. 设置开机自启
sudo cp photo-painter.service /etc/systemd/system/
sudo systemctl enable photo-painter.service

# 5. 启动服务
sudo systemctl start photo-painter.service

# 6. 查看日志
journalctl -u photo-painter -f
```

## 手动测试

```bash
# 直接运行主程序测试
python3 main.py

# 查看执行日志
tail -f /var/log/syslog | grep photo
```

## 开机自启

创建 `/etc/systemd/system/photo-painter.service`:

```ini
[Unit]
Description=Photo Painter Show - 定时图片显示系统
After=network.target

[Service]
Type=simple
ExecStart=/usr/bin/python3 /home/pi/photo-painter-show/main.py
WorkingDirectory=/home/pi/photo-painter-show
User=pi
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

## 省电策略

| 阶段 | 状态 | 功耗 |
|------|------|-----|
| 执行任务 | 系统运行 | 较高 |
| 休眠时 | `rtcwake -m off` | RTC供电，仅RTC芯片工作 |

- `rtcwake -m off` 使系统完全断电
- 仅RTC模块供电，RTC芯片本身功耗极低 (约1μW)
- 定时时间到达后，RTC触发上电，系统启动

## 使用步骤

1. 克隆项目到树莓派
2. 安装依赖: `pip install -r requirements.txt`
3. 配置 `config.json`
4. 设置开机自启
5. 重启或手动启动服务

## 故障排查

| 问题 | 可能原因 | 解决方案 |
|------|---------|---------|
| WiFi无法关闭 | NetworkManager未管理 | 检查nmcli配置 |
| RTC不生效 | I2C未启用 | 启用I2C (`raspi-config`) |
| 显示失败 | 驱动模块缺失 | 检查lib/目录 |
| 下载超时 | 网络问题 | 检查WiFi连接 |
| rtcwake失败 | 权限不足 | 使用sudo运行或配置systemd |
