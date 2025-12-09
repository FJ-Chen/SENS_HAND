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
        """打开舵机扭矩"""
        try:
            # 使用WritePosEx的torque参数来控制扭矩
            # 先读取当前位置，然后设置一个小的扭矩值来启用
            position, _, comm_result, _ = self.packet_handler.ReadPosSpeed(self.id)
            if comm_result == COMM_SUCCESS:
                # 设置当前位置，启用扭矩
                comm_result, error = self.packet_handler.WritePosEx(
                    self.id, position, 0, 0, 500  # position, speed, accel, torque
                )
                if comm_result == COMM_SUCCESS:
                    self.torque_enabled = True
                    return True
            return False
        except Exception:
            return False
    
    def torque_off(self) -> bool:
        """关闭舵机扭矩"""
        try:
            # 设置扭矩为0来关闭
            position, _, comm_result, _ = self.packet_handler.ReadPosSpeed(self.id)
            if comm_result == COMM_SUCCESS:
                comm_result, error = self.packet_handler.WritePosEx(
                    self.id, position, 0, 0, 0  # torque设为0
                )
                if comm_result == COMM_SUCCESS:
                    self.torque_enabled = False
                    return True
            return False
        except Exception:
            return False
    
    def set_goal_position(self, position: int, speed: int = 100, accel: int = 50) -> bool:
        """设置目标位置"""
        try:
            # 应用配置变换
            if self.invert:
                position = -position
            
            # 限制范围
            position = max(self.min_reg, min(self.max_reg, position))
            
            # 使用WritePosEx写入位置
            comm_result, error = self.packet_handler.WritePosEx(
                self.id, position, speed, accel, 500  # 默认扭矩500
            )
            return comm_result == COMM_SUCCESS
        except Exception:
            return False
    
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
        """读取当前位置"""
        try:
            position, speed, comm_result, error = self.packet_handler.ReadPosSpeed(self.id)
            if comm_result == COMM_SUCCESS:
                self.last_position = position
                # 应用配置变换
                if self.invert:
                    position = -position
                return position
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
            'torque_enabled': self.torque_enabled
        }
    
    def update_limits(self, min_pos: int, max_pos: int):
        """更新位置限制"""
        self.min_reg = min_pos
        self.max_reg = max_pos
        self.config['min_reg'] = min_pos
        self.config['max_reg'] = max_pos
        