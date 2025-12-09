#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Servo Manager using SCServo SDK
使用SCServo SDK的舵机管理器
"""

from typing import Dict, List, Optional, Callable
import threading
import time
from .servo import Servo


class ServoManager:
    """
    Manager for multiple servos using SCServo SDK
    使用SCServo SDK的多舵机管理器
    """
    
    def __init__(self, serial_manager, config: dict):
        self.serial_manager = serial_manager
        self.packet_handler = serial_manager.packet_handler
        self.config = config
        
        # 创建17个舵机实例
        self.servos: Dict[int, Servo] = {}
        servo_configs = config.get('servos', {})
        
        for servo_id in range(1, 18):
            servo_config = servo_configs.get(servo_id, {
                'min_reg': -32767,
                'max_reg': 32767,
                'offset': 0,
                'scale': 1.0,
                'invert': False
            })
            self.servos[servo_id] = Servo(servo_id, self.packet_handler, servo_config)
        
        # 监控相关
        self.monitoring = False
        self.monitor_thread: Optional[threading.Thread] = None
        self.monitor_callbacks: List[Callable] = []
        self.monitor_interval = 0.05
    
    def get_servo(self, servo_id: int) -> Optional[Servo]:
        """获取舵机实例"""
        return self.servos.get(servo_id)
    
    def ping_all(self) -> Dict[int, bool]:
        """检查所有舵机连接（限制超时）"""
        results = {}
        for servo_id in range(1, 18):  # 只检查前几个，避免超时
            servo = self.servos.get(servo_id)
            if servo:
                results[servo_id] = servo.ping()
            else:
                results[servo_id] = False
            time.sleep(0.01)  # 短延迟
        return results
    
    def torque_on_all(self) -> Dict[int, bool]:
        """所有连接的舵机上电"""
        results = {}
        for servo_id, servo in self.servos.items():
            if servo.connected:
                results[servo_id] = servo.torque_on()
                time.sleep(0.01)
            else:
                results[servo_id] = False
        return results
    
    def torque_off_all(self) -> Dict[int, bool]:
        """所有连接的舵机下电"""
        results = {}
        for servo_id, servo in self.servos.items():
            if servo.connected:
                results[servo_id] = servo.torque_off()
                time.sleep(0.01)
            else:
                results[servo_id] = False
        return results
    
    def set_all_positions(self, positions: Dict[int, int], 
                          speed: Optional[int] = None,
                          acceleration: Optional[int] = None) -> Dict[int, bool]:
        """设置多个舵机位置"""
        results = {}
        default_speed = speed or 100
        default_accel = acceleration or 50
        
        for servo_id, position in positions.items():
            servo = self.servos.get(servo_id)
            if servo and servo.connected:
                results[servo_id] = servo.set_goal_position(position, default_speed, default_accel)
                time.sleep(0.003)  # 减少延迟
            else:
                results[servo_id] = False
        return results
    
    def read_all_positions(self) -> Dict[int, Optional[int]]:
        """读取所有连接舵机的位置"""
        positions = {}
        for servo_id, servo in self.servos.items():
            if servo.connected:
                positions[servo_id] = servo.read_present_position()
                time.sleep(0.003)
        return positions
    
    def read_all_feedback(self) -> Dict[int, dict]:
        """读取所有舵机反馈"""
        feedback = {}
        for servo_id, servo in self.servos.items():
            if servo.connected:
                feedback[servo_id] = servo.read_all_feedback()
                time.sleep(0.003)
        return feedback
    