#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Servo Control Class / 舵机控制类
High-level interface for individual servo motor control
单个舵机的高级控制接口
"""

from typing import Optional, Tuple, Dict, Any
from .feetech_protocol import FeetchProtocol, SRAMControl, SRAMFeedback


class Servo:
    """
    Individual servo motor controller / 单个舵机控制器
    Encapsulates all operations for a single Feetech servo
    封装单个Feetech舵机的所有操作
    """
    
    # Unit conversion constants / 单位转换常量
    POS_UNIT = 0.087  # degrees per register unit / 每寄存器单位的角度
    SPEED_UNIT = 0.732  # RPM per register unit / 每寄存器单位的转速
    ACCEL_UNIT = 8.7  # deg/s² per register unit / 每寄存器单位的加速度
    TORQUE_UNIT = 6.5  # mA per register unit / 每寄存器单位的扭矩电流
    VOLTAGE_UNIT = 0.1  # V per register unit / 每寄存器单位的电压
    
    def __init__(self, servo_id: int, protocol: FeetchProtocol, config: Dict[str, Any]):
        """
        Initialize servo instance / 初始化舵机实例
        
        Args:
            servo_id: Servo ID (1-17) / 舵机ID
            protocol: Protocol handler instance / 协议处理器实例
            config: Servo configuration dict / 舵机配置字典
                   {min_reg, max_reg, offset, scale, invert}
        """
        self.id = servo_id
        self.protocol = protocol
        self.config = config
        
        # Status tracking / 状态跟踪
        self.connected = False
        self.torque_enabled = False
        self.last_position: Optional[int] = None
        self.last_speed: Optional[int] = None
        
        # Limits / 极限值
        self.min_reg = config.get('min_reg', -32767)
        self.max_reg = config.get('max_reg', 32767)
        self.offset = config.get('offset', 0)
        self.scale = config.get('scale', 1.0)
        self.invert = config.get('invert', False)
    
    def ping(self) -> bool:
        """
        Check if servo is connected and responding / 检查舵机是否连接并响应
        
        Returns:
            Connection status / 连接状态
        """
        try:
            position = self.protocol.read_word(self.id, SRAMFeedback.PRESENT_POSITION_L)
            self.connected = position is not None
            return self.connected
        except Exception:
            self.connected = False
            return False
    
    def torque_on(self) -> bool:
        """
        Enable servo torque (power on) / 打开舵机扭矩（上电）
        
        Returns:
            Success status / 成功状态
        """
        success = self.protocol.write_byte(self.id, SRAMControl.TORQUE_SWITCH, 1)
        if success:
            self.torque_enabled = True
        return success
    
    def torque_off(self) -> bool:
        """
        Disable servo torque (power off) / 关闭舵机扭矩（下电）
        
        Returns:
            Success status / 成功状态
        """
        success = self.protocol.write_byte(self.id, SRAMControl.TORQUE_SWITCH, 0)
        if success:
            self.torque_enabled = False
        return success
    
    def set_damping_mode(self) -> bool:
        """
        Set servo to damping mode / 设置舵机为阻尼模式
        
        Returns:
            Success status / 成功状态
        """
        return self.protocol.write_byte(self.id, SRAMControl.TORQUE_SWITCH, 2)
    
    def set_goal_position(self, position: int, check_limits: bool = True) -> bool:
        """
        Set target position / 设置目标位置
        
        Args:
            position: Target position in register units / 目标位置（寄存器单位）
            check_limits: Whether to enforce limits / 是否强制限位检查
            
        Returns:
            Success status / 成功状态
        """
        if check_limits:
            position = max(self.min_reg, min(self.max_reg, position))
        
        if self.invert:
            position = -position
        
        return self.protocol.write_word(self.id, SRAMControl.GOAL_POSITION_L, position)
    
    def set_goal_speed(self, speed: int) -> bool:
        """
        Set target speed / 设置目标速度
        
        Args:
            speed: Speed in register units (±32767) / 速度（寄存器单位）
                   Positive = one direction, negative = reverse
                   正值=一个方向，负值=反向
            
        Returns:
            Success status / 成功状态
        """
        if self.invert:
            speed = -speed
        
        return self.protocol.write_word(self.id, SRAMControl.GOAL_SPEED_L, speed)
    
    def set_goal_acceleration(self, acceleration: int) -> bool:
        """
        Set acceleration / 设置加速度
        
        Args:
            acceleration: Acceleration (0-254) / 加速度值
                         0 = maximum acceleration / 0表示最大加速度
                         
        Returns:
            Success status / 成功状态
        """
        acceleration = max(0, min(254, acceleration))
        return self.protocol.write_byte(self.id, SRAMControl.ACCELERATION, acceleration)
    
    def set_goal_torque(self, torque: int) -> bool:
        """
        Set target torque/current / 设置目标扭矩/电流
        
        Args:
            torque: Torque in register units (±2047) / 扭矩（寄存器单位）
            
        Returns:
            Success status / 成功状态
        """
        torque = max(-2047, min(2047, torque))
        return self.protocol.write_word(self.id, SRAMControl.GOAL_TORQUE_L, torque)
    
    def set_torque_limit(self, limit: int) -> bool:
        """
        Set torque output limit / 设置扭矩输出限制
        
        Args:
            limit: Torque limit (0-1000) in 0.1% units / 扭矩限制
            
        Returns:
            Success status / 成功状态
        """
        limit = max(0, min(1000, limit))
        return self.protocol.write_word(self.id, SRAMControl.TORQUE_LIMIT_L, limit)
    
    def read_present_position(self) -> Optional[int]:
        """
        Read current position / 读取当前位置
        
        Returns:
            Position in register units or None / 位置（寄存器单位）或None
        """
        position = self.protocol.read_word(self.id, SRAMFeedback.PRESENT_POSITION_L)
        if position is not None:
            self.last_position = position
            if self.invert:
                position = -position
        return position
    
    def read_present_speed(self) -> Optional[int]:
        """
        Read current speed / 读取当前速度
        
        Returns:
            Speed in register units or None / 速度（寄存器单位）或None
        """
        speed = self.protocol.read_word(self.id, SRAMFeedback.PRESENT_SPEED_L)
        if speed is not None:
            self.last_speed = speed
            if self.invert:
                speed = -speed
        return speed
    
    def read_present_load(self) -> Optional[int]:
        """
        Read current load / 读取当前负载
        
        Returns:
            Load in register units or None / 负载（寄存器单位）或None
        """
        return self.protocol.read_word(self.id, SRAMFeedback.PRESENT_LOAD_L)
    
    def read_voltage_temperature(self) -> Tuple[Optional[float], Optional[float]]:
        """
        Read voltage and temperature / 读取电压和温度
        
        Returns:
            (voltage in V, temperature in °C) or (None, None) / (电压V, 温度°C)
        """
        voltage_raw = self.protocol.read_byte(self.id, SRAMFeedback.PRESENT_VOLTAGE)
        temp_raw = self.protocol.read_byte(self.id, SRAMFeedback.PRESENT_TEMPERATURE)
        
        voltage = voltage_raw * self.VOLTAGE_UNIT if voltage_raw is not None else None
        temperature = float(temp_raw) if temp_raw is not None else None
        
        return voltage, temperature
    
    def read_all_feedback(self) -> Dict[str, Any]:
        """
        Read all feedback data at once / 一次性读取所有反馈数据
        
        Returns:
            Dictionary with all feedback values / 包含所有反馈值的字典
        """
        position = self.read_present_position()
        speed = self.read_present_speed()
        load = self.read_present_load()
        voltage, temperature = self.read_voltage_temperature()
        
        return {
            'position': position,
            'position_deg': position * self.POS_UNIT if position is not None else None,
            'speed': speed,
            'speed_rpm': speed * self.SPEED_UNIT if speed is not None else None,
            'load': load,
            'load_percent': load * 0.1 if load is not None else None,
            'voltage': voltage,
            'temperature': temperature,
            'connected': self.connected,
            'torque_enabled': self.torque_enabled
        }
    
    def position_to_degrees(self, reg_value: int) -> float:
        """Convert register value to degrees / 将寄存器值转换为角度"""
        return reg_value * self.POS_UNIT
    
    def degrees_to_position(self, degrees: float) -> int:
        """Convert degrees to register value / 将角度转换为寄存器值"""
        return int(degrees / self.POS_UNIT)
    
    def update_limits(self, min_pos: int, max_pos: int):
        """
        Update position limits / 更新位置限制
        
        Args:
            min_pos: Minimum position / 最小位置
            max_pos: Maximum position / 最大位置
        """
        self.min_reg = min_pos
        self.max_reg = max_pos
        self.config['min_reg'] = min_pos
        self.config['max_reg'] = max_pos