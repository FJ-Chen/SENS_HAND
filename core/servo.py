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

# SCServo 寄存器地址定义
# SCServo register address definitions
ADDR_TORQUE_ENABLE = 40  # 扭矩使能寄存器地址 / Torque enable register address


class Servo:
    """
    Individual servo motor controller using SCServo SDK
    使用SCServo SDK的单个舵机控制器
    """
    
    def __init__(self, servo_id: int, packet_handler, config: Dict[str, Any], 
                 protocol_handler=None):
        """
        初始化舵机 / Initialize servo
        
        Args:
            servo_id: 舵机ID / Servo ID
            packet_handler: 数据包处理器 / Packet handler
            config: 配置字典 / Configuration dict
            protocol_handler: 协议处理器（用于底层寄存器访问）/ Protocol handler for low-level register access
        """
        self.id = servo_id
        self.packet_handler = packet_handler
        self.protocol_handler = protocol_handler  # 新增 / New
        self.config = config
        
        # 状态跟踪 / State tracking
        self.connected = False
        self.torque_enabled = False
        self.last_position = None
        self.torque_value = 500  # 默认扭矩值 / Default torque value
        self.last_speed = 100        
        self.last_acceleration = 50  
        
        # 限制值 / Limit values
        self.min_reg = config.get('min_reg', -32767)
        self.max_reg = config.get('max_reg', 32767)
        self.offset = config.get('offset', 0)
        self.scale = config.get('scale', 1.0)
        self.invert = config.get('invert', False)
    
    def ping(self) -> bool:
        """检查舵机连接 / Check servo connection"""
        try:
            # 尝试读取当前位置 / Try to read current position
            _, _, comm_result, error = self.packet_handler.ReadPosSpeed(self.id)
            self.connected = (comm_result == COMM_SUCCESS)
            return self.connected
        except Exception:
            self.connected = False
            return False
    
    def torque_on(self) -> bool:
        """
        打开舵机扭矩 - 使用寄存器直接写入
        Enable servo torque - using direct register write
        """
        try:
            if self.protocol_handler:
                # 使用协议处理器直接写入扭矩使能寄存器
                # Use protocol handler to directly write torque enable register
                comm_result, error = self.protocol_handler.write1ByteTxRx(
                    self.id, ADDR_TORQUE_ENABLE, 1
                )
                if comm_result == COMM_SUCCESS and error == 0:
                    self.torque_enabled = True
                    self.torque_value = 500  # 恢复默认扭矩 / Restore default torque
                    print(f"Servo {self.id}: Torque enabled (direct register)")
                    return True
                else:
                    print(f"Servo {self.id}: Failed to enable torque - comm:{comm_result}, error:{error}")
            else:
                # 降级方案：使用 WritePosEx，但保持当前位置不动
                # Fallback: use WritePosEx but keep current position
                position, _, comm_result, _ = self.packet_handler.ReadPosSpeed(self.id)
                if comm_result == COMM_SUCCESS:
                    # 设置当前位置，速度0，加速度0，启用扭矩
                    # Set current position, speed=0, accel=0, enable torque
                    comm_result, error = self.packet_handler.WritePosEx(
                        self.id, position, 0, 0, 500
                    )
                    if comm_result == COMM_SUCCESS:
                        self.torque_enabled = True
                        self.torque_value = 500
                        print(f"Servo {self.id}: Torque enabled (fallback)")
                        return True
            return False
        except Exception as e:
            print(f"Servo {self.id}: Torque on error: {e}")
            return False
    
    def torque_off(self) -> bool:
        """
        关闭舵机扭矩 - 使用寄存器直接写入
        Disable servo torque - using direct register write
        """
        try:
            if self.protocol_handler:
                # 使用协议处理器直接写入扭矩使能寄存器
                # Use protocol handler to directly write torque enable register
                comm_result, error = self.protocol_handler.write1ByteTxRx(
                    self.id, ADDR_TORQUE_ENABLE, 0
                )
                if comm_result == COMM_SUCCESS and error == 0:
                    self.torque_enabled = False
                    self.torque_value = 0  # 重置扭矩 / Reset torque
                    print(f"Servo {self.id}: Torque disabled (direct register)")
                    return True
                else:
                    print(f"Servo {self.id}: Failed to disable torque - comm:{comm_result}, error:{error}")
            else:
                # 降级方案：使用 WritePosEx，设置所有参数为0
                # Fallback: use WritePosEx, set all parameters to 0
                position, _, comm_result, _ = self.packet_handler.ReadPosSpeed(self.id)
                if comm_result == COMM_SUCCESS:
                    comm_result, error = self.packet_handler.WritePosEx(
                        self.id, position, 0, 0, 0
                    )
                    if comm_result == COMM_SUCCESS:
                        self.torque_enabled = False
                        self.torque_value = 0
                        print(f"Servo {self.id}: Torque disabled (fallback)")
                        return True
            return False
        except Exception as e:
            print(f"Servo {self.id}: Torque off error: {e}")
            return False
        
    def set_goal_position_with_torque(self, position: int, torque: int, 
                                    speed: int = 100, accel: int = 50) -> bool:
        """设置目标位置和扭矩 / Set goal position and torque"""
        try:
            # 检查位置限制 / Check position limits
            if position < self.min_reg or position > self.max_reg:
                print(f"Servo {self.id}: Position {position} outside limits [{self.min_reg}, {self.max_reg}]")
                return False
            
            # 应用配置变换 / Apply configuration transform
            actual_position = position
            if self.invert:
                actual_position = -position
            
            # 设置扭矩值 / Set torque value
            self.torque_value = torque
            
            # 使用WritePosEx写入位置和扭矩 / Use WritePosEx to write position and torque
            comm_result, error = self.packet_handler.WritePosEx(
                self.id, actual_position, speed, accel, torque
            )
            return comm_result == COMM_SUCCESS
        except Exception as e:
            print(f"Servo {self.id}: Error setting position with torque: {e}")
            return False
    
    def set_goal_position(self, position: int, speed: int = 100, accel: int = 50) -> bool:
        """设置目标位置（使用当前扭矩值）/ Set goal position (using current torque value)"""
        try:
            # 检查位置限制 / Check position limits
            if position < self.min_reg or position > self.max_reg:
                print(f"Servo {self.id}: Position {position} outside limits [{self.min_reg}, {self.max_reg}]")
                # 限制到范围内 / Clamp to range
                position = max(self.min_reg, min(self.max_reg, position))
            
            # 应用配置变换 / Apply configuration transform
            actual_position = position
            if self.invert:
                actual_position = -position
            
            # 使用WritePosEx写入位置，使用当前扭矩值
            # Use WritePosEx to write position, using current torque value
            comm_result, error = self.packet_handler.WritePosEx(
                self.id, actual_position, speed, accel, self.torque_value
            )
            return comm_result == COMM_SUCCESS
        except Exception as e:
            print(f"Servo {self.id}: Error setting position: {e}")
            return False
    
    def set_torque_value(self, torque: int):
        """设置扭矩值（用于后续位置命令）/ Set torque value (for subsequent position commands)"""
        self.torque_value = max(0, min(1000, torque))  # 限制扭矩范围 0-1000 / Limit torque range 0-1000
    
    def get_torque_value(self) -> int:
        """获取当前扭矩值 / Get current torque value"""
        return self.torque_value
    
    def set_goal_speed(self, speed: int) -> bool:
        """设置目标速度（需要配合位置设置）/ Set goal speed (needs to be used with position setting)"""
        # SCServo SDK通过WritePosEx统一设置，这里只记录速度
        # SCServo SDK sets through WritePosEx, only record speed here
        self.last_speed = speed
        return True
    
    def set_goal_acceleration(self, accel: int) -> bool:
        """设置加速度（需要配合位置设置）/ Set acceleration (needs to be used with position setting)"""
        # SCServo SDK通过WritePosEx统一设置，这里只记录加速度
        # SCServo SDK sets through WritePosEx, only record acceleration here
        self.last_acceleration = accel
        return True
    
    def read_present_position(self) -> Optional[int]:
        """读取当前位置 - 改进错误处理 / Read current position - improved error handling"""
        try:
            position, speed, comm_result, error = self.packet_handler.ReadPosSpeed(self.id)
            if comm_result == COMM_SUCCESS:
                self.last_position = position
                # 应用配置变换 / Apply configuration transform
                if self.invert:
                    position = -position
                return position
            else:
                # 通信失败时返回None而不是异常 / Return None instead of exception on communication failure
                return None
        except Exception:
            return None
    
    def read_present_speed(self) -> Optional[int]:
        """读取当前速度 / Read current speed"""
        try:
            position, speed, comm_result, error = self.packet_handler.ReadPosSpeed(self.id)
            if comm_result == COMM_SUCCESS:
                return speed
            return None
        except Exception:
            return None
    
    def read_all_feedback(self) -> Dict[str, Any]:
        """读取所有反馈数据 / Read all feedback data"""
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
        """
        更新位置限制 - 不自动移动到极限位置
        Update position limits - no automatic movement to limits
        """
        self.min_reg = min_pos
        self.max_reg = max_pos
        self.config['min_reg'] = min_pos
        self.config['max_reg'] = max_pos
        print(f"Servo {self.id}: Updated limits to [{min_pos}, {max_pos}]")
        # 删除：不自动移动到极限位置 / Removed: no automatic movement to limits
    
    def is_position_valid(self, position: int) -> bool:
        """检查位置是否在有效范围内 / Check if position is within valid range"""
        return self.min_reg <= position <= self.max_reg
    
    def get_position_limits(self) -> tuple:
        """获取位置限制 / Get position limits"""
        return (self.min_reg, self.max_reg)
    