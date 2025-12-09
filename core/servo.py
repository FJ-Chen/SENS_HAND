#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Servo Control using SCServo SDK
使用SCServo SDK的舵机控制
"""

import sys
import os
# 确保能导入scservo_sdk
current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sdk_path = os.path.join(current_dir, 'scservo_sdk')
if sdk_path not in sys.path:
    sys.path.append(sdk_path)

from scservo_sdk import *
from typing import Optional, Dict, Any


class Servo:
    """
    Individual servo motor controller using SCServo SDK
    使用SCServo SDK的单个舵机控制器
    """
    
    def __init__(self, servo_id: int, packet_handler, config: Dict[str, Any]):
        self.id = servo_id
        self.packet_handler = packet_handler
        self.config = config
        
        # 状态跟踪
        self.connected = False
        self.torque_enabled = False
        self.last_position = None
        self.torque_value = 500  # 默认扭矩值
        
        # 限制值
        self.min_reg = config.get('min_reg', -32767)
        self.max_reg = config.get('max_reg', 32767)
        self.offset = config.get('offset', 0)
        self.scale = config.get('scale', 1.0)
        self.invert = config.get('invert', False)
    
    def ping(self) -> bool:
        """检查舵机连接"""
        try:
            # 尝试读取当前位置
            _, _, comm_result, error = self.packet_handler.ReadPosSpeed(self.id)
            self.connected = (comm_result == COMM_SUCCESS)
            return self.connected
        except Exception:
            self.connected = False
            return False
    
    def torque_on(self) -> bool:
        """
        打开舵机扭矩 - 使用默认参数
        Enable servo torque - with default parameters
        """
        try:
            # 读取当前位置 / Read current position
            position, _, comm_result, _ = self.packet_handler.ReadPosSpeed(self.id)
            if comm_result == COMM_SUCCESS:
                # 上电时恢复默认扭矩值 / Restore default torque on power on
                self.torque_value = 500  # 默认扭矩 / Default torque
                
                # 设置当前位置，启用扭矩，使用默认参数
                # Set current position, enable torque with default parameters
                comm_result, error = self.packet_handler.WritePosEx(
                    self.id, position, 100, 50, self.torque_value  # 默认速度100，加速度50 / Default speed=100, accel=50
                )
                if comm_result == COMM_SUCCESS:
                    self.torque_enabled = True
                    return True
            return False
        except Exception:
            return False
    
    def torque_off(self) -> bool:
        """
        关闭舵机扭矩 - 确保真正断电
        Disable servo torque - ensure complete power off
        """
        try:
            # 读取当前位置 / Read current position
            position, _, comm_result, _ = self.packet_handler.ReadPosSpeed(self.id)
            if comm_result == COMM_SUCCESS:
                # 设置扭矩为0，速度为0，加速度为0，确保完全断电
                # Set torque=0, speed=0, accel=0 to ensure complete power off
                comm_result, error = self.packet_handler.WritePosEx(
                    self.id, position, 0, 0, 0  # 所有参数都设为0 / All parameters set to 0
                )
                if comm_result == COMM_SUCCESS:
                    self.torque_enabled = False
                    self.torque_value = 0  # 重置扭矩值 / Reset torque value
                    return True
            return False
        except Exception:
            return False
        
    def set_goal_position_with_torque(self, position: int, torque: int, 
                                    speed: int = 100, accel: int = 50) -> bool:
        """设置目标位置和扭矩"""
        try:
            # 检查位置限制
            if position < self.min_reg or position > self.max_reg:
                print(f"Servo {self.id}: Position {position} outside limits [{self.min_reg}, {self.max_reg}]")
                return False
            
            # 应用配置变换
            actual_position = position
            if self.invert:
                actual_position = -position
            
            # 设置扭矩值
            self.torque_value = torque
            
            # 使用WritePosEx写入位置和扭矩
            comm_result, error = self.packet_handler.WritePosEx(
                self.id, actual_position, speed, accel, torque
            )
            return comm_result == COMM_SUCCESS
        except Exception as e:
            print(f"Servo {self.id}: Error setting position with torque: {e}")
            return False
    
    def set_goal_position(self, position: int, speed: int = 100, accel: int = 50) -> bool:
        """设置目标位置（使用当前扭矩值）"""
        try:
            # 检查位置限制
            if position < self.min_reg or position > self.max_reg:
                print(f"Servo {self.id}: Position {position} outside limits [{self.min_reg}, {self.max_reg}]")
                # 限制到范围内
                position = max(self.min_reg, min(self.max_reg, position))
            
            # 应用配置变换
            actual_position = position
            if self.invert:
                actual_position = -position
            
            # 使用WritePosEx写入位置，使用当前扭矩值
            comm_result, error = self.packet_handler.WritePosEx(
                self.id, actual_position, speed, accel, self.torque_value
            )
            return comm_result == COMM_SUCCESS
        except Exception as e:
            print(f"Servo {self.id}: Error setting position: {e}")
            return False
    
    def set_torque_value(self, torque: int):
        """设置扭矩值（用于后续位置命令）"""
        self.torque_value = max(0, min(1000, torque))  # 限制扭矩范围 0-1000
    
    def get_torque_value(self) -> int:
        """获取当前扭矩值"""
        return self.torque_value
    
    def set_goal_speed(self, speed: int) -> bool:
        """设置目标速度（需要配合位置设置）"""
        # SCServo SDK通过WritePosEx统一设置，这里只记录速度
        self.last_speed = speed
        return True
    
    def set_goal_acceleration(self, accel: int) -> bool:
        """设置加速度（需要配合位置设置）"""
        # SCServo SDK通过WritePosEx统一设置，这里只记录加速度
        self.last_acceleration = accel
        return True
    
    def read_present_position(self) -> Optional[int]:
        """读取当前位置 - 改进错误处理"""
        try:
            position, speed, comm_result, error = self.packet_handler.ReadPosSpeed(self.id)
            if comm_result == COMM_SUCCESS:
                self.last_position = position
                # 应用配置变换
                if self.invert:
                    position = -position
                return position
            else:
                # 通信失败时返回None而不是异常
                return None
        except Exception:
            return None
    
    def read_present_speed(self) -> Optional[int]:
        """读取当前速度"""
        try:
            position, speed, comm_result, error = self.packet_handler.ReadPosSpeed(self.id)
            if comm_result == COMM_SUCCESS:
                return speed
            return None
        except Exception:
            return None
    
    def read_all_feedback(self) -> Dict[str, Any]:
        """读取所有反馈数据"""
        position = self.read_present_position()
        speed = self.read_present_speed()
        
        return {
            'position': position,
            'position_deg': position * 0.087 if position is not None else None,
            'speed': speed,
            'speed_rpm': speed * 0.732 if speed is not None else None,
            'connected': self.connected,
            'torque_enabled': self.torque_enabled,
            'torque_value': self.torque_value
        }
    
    def update_limits(self, min_pos: int, max_pos: int):
        """更新位置限制 - 不自动移动到极限位置"""
        self.min_reg = min_pos
        self.max_reg = max_pos
        self.config['min_reg'] = min_pos
        self.config['max_reg'] = max_pos
        print(f"Servo {self.id}: Updated limits to [{min_pos}, {max_pos}]")
        # 移除自动移动到极限位置的代码
    
    def is_position_valid(self, position: int) -> bool:
        """检查位置是否在有效范围内"""
        return self.min_reg <= position <= self.max_reg
    
    def get_position_limits(self) -> tuple:
        """获取位置限制"""
        return (self.min_reg, self.max_reg)
    