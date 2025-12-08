# SENS Hand Controller / SENS HAND 手部控制器

完整的双手协同机械手控制系统，支持Feetech总线舵机控制、动作录制回放、手势识别镜像控制。

A complete dual-hand robotic hand control system with Feetech bus servo control, motion recording/playback, and gesture recognition mirror control.

## Features / 功能特性

### 1. Servo Control / 舵机控制
- **17-servo management** / **17舵机管理**
  - Individual position, speed, acceleration, torque control / 独立的位置、速度、加速度、扭矩控制
  - Real-time feedback display / 实时反馈显示
  - Batch operations (all on/off) / 批量操作（全部上电/下电）

- **Calibration** / **校准功能**
  - Automatic limit detection / 自动极限检测
  - Real-time range calibration / 实时范围校准
  - Configuration saving / 配置保存

### 2. Recording & Playback / 录制与播放
- **Two recording modes** / **双录制模式**
  - Frame-based: Manual keyframe recording / 帧式：手动关键帧录制
  - Real-time: 1:1 continuous recording (1-100Hz) / 实时：1:1连续录制(1-100Hz)

- **Flexible playback** / **灵活播放**
  - Variable speed (0.1x - 5.0x) / 可变速度(0.1x - 5.0x)
  - Precise timing reproduction / 精确时间重现
  - JSON format storage / JSON格式存储

### 3. Gesture Recognition / 手势识别
- **MediaPipe-based tracking** / **基于MediaPipe的追踪**
  - Real-time hand landmark detection / 实时手部关键点检测
  - 21-point joint tracking / 21点关节追踪
  - Mirror control mode / 镜像控制模式

- **Intelligent mapping** / **智能映射**
  - Joint-to-servo position mapping / 关节到舵机位置映射
  - Adjustable sensitivity / 可调灵敏度
  - Smooth motion filtering / 平滑运动滤波

### 4. Bilingual UI / 双语界面
- **Chinese/English switching** / **中英文切换**
- **PyQt5 modern interface** / **PyQt5现代界面**
- **Intuitive controls** / **直观控制**

## System Requirements / 系统要求

### Hardware / 硬件
- PC with available USB port / 带有可用USB端口的PC
- Feetech SCS/SMS bus servos (17 units) / 飞特SCS/SMS总线舵机（17个）
- USB-to-TTL adapter (UART) / USB转TTL适配器（UART）
- (Optional) USB camera for gesture recognition / （可选）用于手势识别的USB摄像头

### Software / 软件
- Python 3.8 or higher / Python 3.8或更高版本
- Windows / Linux / macOS

## Installation / 安装

