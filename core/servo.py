#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
servo.py - 单个舵机控制
使用 hls.py 提供的 WritePosEx 方法
"""

import sys
import os
current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sdk_path = os.path.join(current_dir, 'scservo_sdk')
if sdk_path not in sys.path:
    sys.path.append(sdk_path)

from scservo_sdk import *
from typing import Optional, Dict, Any


class Servo:
    """单个舵机控制器"""
    
    def __init__(self, servo_id: int, packet_handler, config: Dict[str, Any]):
        self.id = servo_id
        self.packet_handler = packet_handler
        self.config = config
        
        # 状态跟踪
        self.connected = False
        self.torque_enabled = False
        self.last_position = None
        self.torque_value = 500
        self.last_speed = 100
        self.last_acceleration = 50
        
        # 限制值
        self.min_reg = config.get('min_reg', -32767)
        self.max_reg = config.get('max_reg', 32767)
        self.offset = config.get('offset', 0)
        self.scale = config.get('scale', 1.0)
        self.invert = config.get('invert', False)
    
    def ping(self) -> bool:
        """检查舵机连接"""
        try:
            _, _, comm_result, error = self.packet_handler.ReadPosSpeed(self.id)
            self.connected = (comm_result == COMM_SUCCESS)
            return self.connected
        except Exception as e:
            print(f"Servo {self.id} ping error: {e}")
            self.connected = False
            return False
    
    def torque_on(self) -> bool:
        """打开舵机扭矩"""
        try:
            comm_result, error = self.packet_handler.write1ByteTxRx(self.id, 40, 1)
            if comm_result == COMM_SUCCESS and error == 0:
                self.torque_enabled = True
                self.torque_value = 500
                return True
            else:
                print(f"Servo {self.id}: Torque on failed - result:{comm_result}, error:{error}")
                return False
        except Exception as e:
            print(f"Servo {self.id}: Torque on error: {e}")
            return False
    
    def torque_off(self) -> bool:
        """关闭舵机扭矩"""
        try:
            comm_result, error = self.packet_handler.write1ByteTxRx(self.id, 40, 0)
            if comm_result == COMM_SUCCESS and error == 0:
                self.torque_enabled = False
                self.torque_value = 0
                return True
            return False
        except Exception as e:
            print(f"Servo {self.id}: Torque off error: {e}")
            return False
    
    def set_goal_position_with_torque(self, position: int, torque: int, 
                                      speed: int = 100, accel: int = 50) -> bool:
        """设置目标位置（完整参数版本）"""
        try:
            position = max(self.min_reg, min(self.max_reg, position))
            actual_position = -position if self.invert else position
            
            # 更新状态
            self.torque_value = torque
            self.last_speed = speed
            self.last_acceleration = accel
            
            comm_result, error = self.packet_handler.WritePosEx(
                self.id, actual_position, speed, accel, torque
            )
            
            if comm_result == COMM_SUCCESS:
                return True
            else:
                print(f"Servo {self.id}: WritePosEx failed - result:{comm_result}, error:{error}")
                return False
                
        except Exception as e:
            print(f"Servo {self.id}: set_goal_position_with_torque error: {e}")
            return False
    
    def set_goal_position(self, position: int) -> bool:
        """设置目标位置（使用当前保存的速度、加速度、扭矩值）"""
        return self.set_goal_position_with_torque(
            position, self.torque_value, self.last_speed, self.last_acceleration
        )
    
    def set_goal_speed(self, speed: int) -> bool:
        """设置速度并立即应用（使用当前位置重发命令）"""
        self.last_speed = max(0, min(1000, speed))
        if self.last_position is not None and self.torque_enabled:
            return self.set_goal_position_with_torque(
                self.last_position, self.torque_value, 
                self.last_speed, self.last_acceleration
            )
        return True
    
    def set_goal_acceleration(self, accel: int) -> bool:
        """设置加速度并立即应用（使用当前位置重发命令）"""
        self.last_acceleration = max(0, min(255, accel))
        if self.last_position is not None and self.torque_enabled:
            return self.set_goal_position_with_torque(
                self.last_position, self.torque_value,
                self.last_speed, self.last_acceleration
            )
        return True
    
    def read_present_position(self) -> Optional[int]:
        """读取当前位置"""
        try:
            position, comm_result, error = self.packet_handler.ReadPos(self.id)
            if comm_result == COMM_SUCCESS:
                self.last_position = position
                if self.invert:
                    position = -position
                return position
            return None
        except Exception:
            return None
    
    def read_present_speed(self) -> Optional[int]:
        """读取当前速度"""
        try:
            speed, comm_result, error = self.packet_handler.ReadSpeed(self.id)
            if comm_result == COMM_SUCCESS:
                return speed
            return None
        except Exception:
            return None
    
    def read_pos_speed(self) -> tuple:
        """读取位置和速度"""
        try:
            position, speed, comm_result, error = self.packet_handler.ReadPosSpeed(self.id)
            if comm_result == COMM_SUCCESS:
                self.last_position = position
                if self.invert:
                    position = -position
                return position, speed
            return None, None
        except Exception:
            return None, None
    
    def read_all_feedback(self) -> Dict[str, Any]:
        """读取所有反馈数据"""
        position, speed = self.read_pos_speed()
        return {
            'position': position,
            'speed': speed,
            'connected': self.connected,
            'torque_enabled': self.torque_enabled,
            'torque_value': self.torque_value
        }
    
    def set_torque_value(self, torque: int):
        """设置扭矩值"""
        self.torque_value = max(0, min(1000, torque))
    
    def get_torque_value(self) -> int:
        """获取当前扭矩值"""
        return self.torque_value
    
    def update_limits(self, min_pos: int, max_pos: int):
        """更新位置限制"""
        self.min_reg = min_pos
        self.max_reg = max_pos
        self.config['min_reg'] = min_pos
        self.config['max_reg'] = max_pos
    
    def get_position_limits(self) -> tuple:
        """获取位置限制"""
        return (self.min_reg, self.max_reg)
    