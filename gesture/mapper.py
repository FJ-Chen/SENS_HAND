#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Joint to Servo Mapper / 关节到舵机映射器
Maps hand joint positions to servo positions
将手部关节位置映射到舵机位置
"""

import numpy as np
from typing import Dict


class JointMapper:
    """
    Maps hand joint positions to 17 servo positions / 将手部关节位置映射到17个舵机位置
    """
    
    def __init__(self, config: dict):
        """
        Initialize mapper / 初始化映射器
        
        Args:
            config: Mapping configuration / 映射配置
        """
        self.config = config
        self.mapping = config.get('gesture', {}).get('mapping', {})
        
    def map_joints_to_servos(self, joints: Dict[str, np.ndarray]) -> Dict[int, int]:
        """
        Map joint positions to servo positions / 将关节位置映射到舵机位置
        
        Args:
            joints: Dict of joint positions / 关节位置字典
            
        Returns:
            Dict of {servo_id: position} / 舵机位置字典
        """
        servo_positions = {}
        
        # Thumb / 拇指 (servos 1-4)
        thumb_angle = self._calculate_finger_angle(joints, 'THUMB')
        servo_positions[1] = self._angle_to_servo(thumb_angle, 1)
        servo_positions[2] = self._angle_to_servo(thumb_angle * 0.8, 2)
        servo_positions[3] = self._angle_to_servo(thumb_angle * 0.6, 3)
        servo_positions[4] = self._angle_to_servo(thumb_angle * 0.4, 4)
        
        # Index finger / 食指 (servos 5-7)
        index_angle = self._calculate_finger_angle(joints, 'INDEX')
        servo_positions[5] = self._angle_to_servo(index_angle, 5)
        servo_positions[6] = self._angle_to_servo(index_angle * 0.8, 6)
        servo_positions[7] = self._angle_to_servo(index_angle * 0.6, 7)
        
        # Middle finger / 中指 (servos 8-10)
        middle_angle = self._calculate_finger_angle(joints, 'MIDDLE')
        servo_positions[8] = self._angle_to_servo(middle_angle, 8)
        servo_positions[9] = self._angle_to_servo(middle_angle * 0.8, 9)
        servo_positions[10] = self._angle_to_servo(middle_angle * 0.6, 10)
        
        # Ring finger / 无名指 (servos 11-13)
        ring_angle = self._calculate_finger_angle(joints, 'RING')
        servo_positions[11] = self._angle_to_servo(ring_angle, 11)
        servo_positions[12] = self._angle_to_servo(ring_angle * 0.8, 12)
        servo_positions[13] = self._angle_to_servo(ring_angle * 0.6, 13)
        
        # Pinky / 小指 (servos 14-16)
        pinky_angle = self._calculate_finger_angle(joints, 'PINKY')
        servo_positions[14] = self._angle_to_servo(pinky_angle, 14)
        servo_positions[15] = self._angle_to_servo(pinky_angle * 0.8, 15)
        servo_positions[16] = self._angle_to_servo(pinky_angle * 0.6, 16)
        
        # Wrist / 手腕 (servo 17)
        wrist_angle = self._calculate_wrist_angle(joints)
        servo_positions[17] = self._angle_to_servo(wrist_angle, 17)
        
        return servo_positions
        
    def _calculate_finger_angle(self, joints: Dict[str, np.ndarray], 
                                finger: str) -> float:
        """
        Calculate finger bend angle / 计算手指弯曲角度
        
        Args:
            joints: Joint positions / 关节位置
            finger: Finger name / 手指名称
            
        Returns:
            Angle in degrees / 角度（度）
        """
        # Get finger joints / 获取手指关节
        if finger == 'THUMB':
            base = joints.get('THUMB_CMC')
            tip = joints.get('THUMB_TIP')
        else:
            base = joints.get(f'{finger}_MCP')
            tip = joints.get(f'{finger}_TIP')
        
        if base is None or tip is None:
            return 0.0
        
        # Calculate distance / 计算距离
        distance = np.linalg.norm(tip - base)
        
        # Map distance to angle (0-180 degrees) / 距离映射到角度
        # Shorter distance = more bent = higher angle / 距离短=弯曲多=角度大
        max_distance = 0.3  # Calibrate based on hand size / 根据手部大小校准
        angle = (1.0 - min(distance / max_distance, 1.0)) * 180.0
        
        return angle
        
    def _calculate_wrist_angle(self, joints: Dict[str, np.ndarray]) -> float:
        """
        Calculate wrist rotation angle / 计算手腕旋转角度
        
        Args:
            joints: Joint positions / 关节位置
            
        Returns:
            Angle in degrees / 角度（度）
        """
        wrist = joints.get('WRIST')
        index_mcp = joints.get('INDEX_MCP')
        pinky_mcp = joints.get('PINKY_MCP')
        
        if wrist is None or index_mcp is None or pinky_mcp is None:
            return 0.0
        
        # Calculate hand plane normal / 计算手掌平面法向量
        v1 = index_mcp - wrist
        v2 = pinky_mcp - wrist
        normal = np.cross(v1, v2)
        
        # Project to XY plane and calculate angle / 投影到XY平面并计算角度
        angle = np.degrees(np.arctan2(normal[1], normal[0]))
        
        return angle
        
    def _angle_to_servo(self, angle: float, servo_id: int) -> int:
        """
        Convert angle to servo position / 将角度转换为舵机位置
        
        Args:
            angle: Angle in degrees / 角度（度）
            servo_id: Servo ID / 舵机ID
            
        Returns:
            Servo position value / 舵机位置值
        """
        # Get servo range from mapping config / 从映射配置获取舵机范围
        servo_config = self.mapping.get(servo_id, {
            'min': -32767,
            'max': 32767,
            'scale': 1.0,
            'offset': 0
        })
        
        # Map angle (0-180) to servo range / 将角度(0-180)映射到舵机范围
        servo_range = servo_config['max'] - servo_config['min']
        position = servo_config['min'] + (angle / 180.0) * servo_range
        
        # Apply scale and offset / 应用缩放和偏移
        position = position * servo_config['scale'] + servo_config['offset']
        
        # Clamp to limits / 限制在范围内
        position = max(servo_config['min'], min(servo_config['max'], position))
        
        return int(position)