#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Feetech Protocol Implementation / Feetech 协议实现
Implements low-level SRAM register read/write for Feetech servos
实现 Feetech 舵机的底层 SRAM 寄存器读写
"""

import struct
import time
from typing import List, Optional, Tuple

# SRAM Control Registers / SRAM 控制寄存器
class SRAMControl:
    """SRAM Control Register Addresses / SRAM 控制寄存器地址"""
    TORQUE_SWITCH = 40      # 0x28 - Torque on/off / 扭矩开关 (0=off, 1=on, 2=damping)
    ACCELERATION = 41       # 0x29 - Acceleration / 加速度 (0-254, unit: 8.7°/s²)
    GOAL_POSITION_L = 42    # 0x2A - Goal position low byte / 目标位置低字节
    GOAL_POSITION_H = 43    # 0x2B - Goal position high byte / 目标位置高字节
    GOAL_TORQUE_L = 44      # 0x2C - Goal torque low byte / 目标扭矩低字节 (unit: 6.5mA)
    GOAL_TORQUE_H = 45      # 0x2D - Goal torque high byte / 目标扭矩高字节
    GOAL_SPEED_L = 46       # 0x2E - Goal speed low byte / 运行速度低字节 (unit: 0.732 RPM)
    GOAL_SPEED_H = 47       # 0x2F - Goal speed high byte / 运行速度高字节
    TORQUE_LIMIT_L = 48     # 0x30 - Torque limit low byte / 转矩限制低字节
    TORQUE_LIMIT_H = 49     # 0x31 - Torque limit high byte / 转矩限制高字节

# SRAM Feedback Registers / SRAM 反馈寄存器
class SRAMFeedback:
    """SRAM Feedback Register Addresses / SRAM 反馈寄存器地址"""
    PRESENT_POSITION_L = 56  # 0x38 - Present position low byte / 当前位置低字节 (unit: 0.087°)
    PRESENT_POSITION_H = 57  # 0x39 - Present position high byte / 当前位置高字节
    PRESENT_SPEED_L = 58     # 0x3A - Present speed low byte / 当前速度低字节 (unit: 0.732 RPM)
    PRESENT_SPEED_H = 59     # 0x3B - Present speed high byte / 当前速度高字节
    PRESENT_LOAD_L = 60      # 0x3C - Present load low byte / 当前负载低字节 (unit: 0.1%)
    PRESENT_LOAD_H = 61      # 0x3D - Present load high byte / 当前负载高字节
    PRESENT_VOLTAGE = 62     # 0x3E - Present voltage / 当前电压 (unit: 0.1V)
    PRESENT_TEMPERATURE = 63 # 0x3F - Present temperature / 当前温度 (unit: °C)

# Protocol constants / 协议常量
BROADCAST_ID = 0xFE
HEADER = [0xFF, 0xFF]


class FeetchProtocol:
    """
    Feetech Protocol Handler / Feetech 协议处理器
    Handles packet construction, checksum, and communication
    处理数据包构建、校验和通信
    """
    
    def __init__(self, serial_manager):
        """
        Initialize protocol handler / 初始化协议处理器
        
        Args:
            serial_manager: Serial port manager instance / 串口管理器实例
        """
        self.serial_manager = serial_manager
        self.max_retries = 3  # Maximum retry attempts / 最大重试次数
        
    def _calculate_checksum(self, packet: List[int]) -> int:
        """
        Calculate packet checksum / 计算数据包校验和
        
        Args:
            packet: Packet data without header and checksum / 不含包头和校验和的数据
            
        Returns:
            Checksum byte / 校验和字节
        """
        checksum = 0
        for byte in packet[2:-1]:  # Skip header and checksum position
            checksum += byte
        return (~checksum) & 0xFF
    
    def _build_packet(self, servo_id: int, instruction: int, params: List[int]) -> List[int]:
        """
        Build instruction packet / 构建指令数据包
        
        Args:
            servo_id: Servo ID (1-17 or BROADCAST_ID) / 舵机ID
            instruction: Instruction code / 指令代码
            params: Parameter bytes / 参数字节列表
            
        Returns:
            Complete packet with checksum / 包含校验和的完整数据包
        """
        length = len(params) + 2  # Instruction + checksum
        packet = HEADER + [servo_id, length, instruction] + params + [0]
        packet[-1] = self._calculate_checksum(packet)
        return packet
    
    def write_byte(self, servo_id: int, address: int, value: int) -> bool:
        """
        Write single byte to SRAM / 写单字节到SRAM
        
        Args:
            servo_id: Servo ID / 舵机ID
            address: Register address / 寄存器地址
            value: Byte value (0-255) / 字节值
            
        Returns:
            Success status / 成功状态
        """
        packet = self._build_packet(servo_id, 0x03, [address, value & 0xFF])
        return self._send_packet(packet, servo_id)
    
    def write_word(self, servo_id: int, address: int, value: int) -> bool:
        """
        Write 16-bit word to SRAM / 写16位字到SRAM
        
        Args:
            servo_id: Servo ID / 舵机ID
            address: Register address / 寄存器地址
            value: Word value (-32768 to 32767) / 字值
            
        Returns:
            Success status / 成功状态
        """
        # Handle signed 16-bit value / 处理有符号16位值
        if value < 0:
            value = (1 << 15) | (-value)
        
        low_byte = value & 0xFF
        high_byte = (value >> 8) & 0xFF
        packet = self._build_packet(servo_id, 0x03, [address, low_byte, high_byte])
        return self._send_packet(packet, servo_id)
    
    def read_byte(self, servo_id: int, address: int) -> Optional[int]:
        """
        Read single byte from SRAM / 从SRAM读单字节
        
        Args:
            servo_id: Servo ID / 舵机ID
            address: Register address / 寄存器地址
            
        Returns:
            Byte value or None on failure / 字节值或失败时None
        """
        packet = self._build_packet(servo_id, 0x02, [address, 1])
        response = self._send_and_receive(packet, servo_id, 7)
        
        if response and len(response) >= 6:
            return response[5]
        return None
    
    def read_word(self, servo_id: int, address: int) -> Optional[int]:
        """
        Read 16-bit word from SRAM / 从SRAM读16位字
        
        Args:
            servo_id: Servo ID / 舵机ID
            address: Register address / 寄存器地址
            
        Returns:
            Signed word value or None on failure / 有符号字值或失败时None
        """
        packet = self._build_packet(servo_id, 0x02, [address, 2])
        response = self._send_and_receive(packet, servo_id, 8)
        
        if response and len(response) >= 7:
            low_byte = response[5]
            high_byte = response[6]
            value = (high_byte << 8) | low_byte
            
            # Convert to signed if BIT15 is set / 如果BIT15置位则转换为有符号
            if value & 0x8000:
                value = -(value & 0x7FFF)
            
            return value
        return None
    
    def _send_packet(self, packet: List[int], servo_id: int) -> bool:
        """
        Send packet with retry mechanism / 发送数据包（带重试机制）
        
        Args:
            packet: Packet bytes / 数据包字节
            servo_id: Servo ID for logging / 用于日志的舵机ID
            
        Returns:
            Success status / 成功状态
        """
        for attempt in range(self.max_retries):
            try:
                if self.serial_manager.write(bytes(packet)):
                    time.sleep(0.001)  # Small delay for servo processing / 短延迟等待舵机处理
                    return True
            except Exception as e:
                if attempt == self.max_retries - 1:
                    print(f"Failed to send to servo {servo_id}: {e}")
        return False
    
    def _send_and_receive(self, packet: List[int], servo_id: int, expected_length: int) -> Optional[List[int]]:
        """
        Send packet and receive response / 发送数据包并接收响应
        
        Args:
            packet: Packet to send / 要发送的数据包
            servo_id: Servo ID / 舵机ID
            expected_length: Expected response length / 期望的响应长度
            
        Returns:
            Response packet or None / 响应数据包或None
        """
        for attempt in range(self.max_retries):
            try:
                self.serial_manager.clear_buffer()
                if not self.serial_manager.write(bytes(packet)):
                    continue
                
                time.sleep(0.005)  # Wait for response / 等待响应
                response = self.serial_manager.read(expected_length)
                
                if response and len(response) >= expected_length:
                    # Verify checksum / 验证校验和
                    calc_checksum = self._calculate_checksum(list(response))
                    if response[-1] == calc_checksum:
                        return list(response)
                        
            except Exception as e:
                if attempt == self.max_retries - 1:
                    print(f"Failed to receive from servo {servo_id}: {e}")
        
        return None