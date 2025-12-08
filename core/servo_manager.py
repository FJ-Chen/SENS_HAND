#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Servo Manager / 舵机管理器
Manages collection of 17 servos with batch operations
管理17个舵机的集合，支持批量操作
"""

from typing import Dict, List, Optional, Callable
import threading
import time
from .servo import Servo
from .feetech_protocol import FeetchProtocol
from .serial_manager import SerialManager


class ServoManager:
    """
    Manager for multiple servos with batch control and status monitoring
    多舵机管理器，支持批量控制和状态监控
    """
    
    def __init__(self, serial_manager: SerialManager, config: dict):
        """
        Initialize servo manager / 初始化舵机管理器
        
        Args:
            serial_manager: Serial port manager / 串口管理器
            config: Configuration dict with servo settings / 配置字典
        """
        self.serial_manager = serial_manager
        self.protocol = FeetchProtocol(serial_manager)
        self.config = config
        
        # Create 17 servo instances / 创建17个舵机实例
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
            self.servos[servo_id] = Servo(servo_id, self.protocol, servo_config)
        
        # Monitoring thread / 监控线程
        self.monitoring = False
        self.monitor_thread: Optional[threading.Thread] = None
        self.monitor_callbacks: List[Callable] = []
        self.monitor_interval = 0.05  # 20Hz default / 默认20Hz
        
    def get_servo(self, servo_id: int) -> Optional[Servo]:
        """
        Get servo instance by ID / 通过ID获取舵机实例
        
        Args:
            servo_id: Servo ID (1-17) / 舵机ID
            
        Returns:
            Servo instance or None / 舵机实例或None
        """
        return self.servos.get(servo_id)
    
    def ping_all(self) -> Dict[int, bool]:
        """
        Ping all servos to check connection / 检查所有舵机连接
        
        Returns:
            Dict of {servo_id: connected_status} / 舵机连接状态字典
        """
        results = {}
        for servo_id, servo in self.servos.items():
            results[servo_id] = servo.ping()
            time.sleep(0.01)  # Small delay between pings / 检查间隔
        return results
    
    def torque_on_all(self) -> Dict[int, bool]:
        """
        Enable torque for all servos / 所有舵机上电
        
        Returns:
            Dict of {servo_id: success_status} / 操作结果字典
        """
        results = {}
        for servo_id, servo in self.servos.items():
            if servo.connected:
                results[servo_id] = servo.torque_on()
                time.sleep(0.005)
        return results
    
    def torque_off_all(self) -> Dict[int, bool]:
        """
        Disable torque for all servos / 所有舵机下电
        
        Returns:
            Dict of {servo_id: success_status} / 操作结果字典
        """
        results = {}
        for servo_id, servo in self.servos.items():
            if servo.connected:
                results[servo_id] = servo.torque_off()
                time.sleep(0.005)
        return results
    
    def set_all_positions(self, positions: Dict[int, int], speed: Optional[int] = None,
                          acceleration: Optional[int] = None) -> Dict[int, bool]:
        """
        Set positions for multiple servos / 设置多个舵机位置
        
        Args:
            positions: Dict of {servo_id: position} / 位置字典
            speed: Optional speed for all servos / 可选的统一速度
            acceleration: Optional acceleration for all / 可选的统一加速度
            
        Returns:
            Dict of {servo_id: success_status} / 操作结果字典
        """
        results = {}
        
        # Set speed and acceleration if provided / 如果提供则设置速度和加速度
        if speed is not None:
            for servo_id in positions.keys():
                servo = self.servos.get(servo_id)
                if servo and servo.connected:
                    servo.set_goal_speed(speed)
        
        if acceleration is not None:
            for servo_id in positions.keys():
                servo = self.servos.get(servo_id)
                if servo and servo.connected:
                    servo.set_goal_acceleration(acceleration)
        
        # Set positions / 设置位置
        for servo_id, position in positions.items():
            servo = self.servos.get(servo_id)
            if servo and servo.connected:
                results[servo_id] = servo.set_goal_position(position)
                time.sleep(0.003)
        
        return results
    
    def read_all_positions(self) -> Dict[int, Optional[int]]:
        """
        Read current positions of all servos / 读取所有舵机当前位置
        
        Returns:
            Dict of {servo_id: position} / 位置字典
        """
        positions = {}
        for servo_id, servo in self.servos.items():
            if servo.connected:
                positions[servo_id] = servo.read_present_position()
                time.sleep(0.003)
        return positions
    
    def read_all_feedback(self) -> Dict[int, dict]:
        """
        Read all feedback data from all servos / 读取所有舵机的反馈数据
        
        Returns:
            Dict of {servo_id: feedback_dict} / 反馈数据字典
        """
        feedback = {}
        for servo_id, servo in self.servos.items():
            if servo.connected:
                feedback[servo_id] = servo.read_all_feedback()
                time.sleep(0.003)
        return feedback
    
    def start_monitoring(self, callback: Optional[Callable] = None, interval: float = 0.05):
        """
        Start background monitoring thread / 启动后台监控线程
        
        Args:
            callback: Function to call with feedback data / 回调函数
            interval: Monitoring interval in seconds / 监控间隔（秒）
        """
        if self.monitoring:
            return
        
        self.monitor_interval = interval
        if callback:
            self.monitor_callbacks.append(callback)
        
        self.monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
    
    def stop_monitoring(self):
        """Stop background monitoring / 停止后台监控"""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=1.0)
    
    def add_monitor_callback(self, callback: Callable):
        """Add callback for monitoring data / 添加监控数据回调"""
        if callback not in self.monitor_callbacks:
            self.monitor_callbacks.append(callback)
    
    def _monitor_loop(self):
        """
        Background monitoring loop / 后台监控循环
        Continuously reads servo feedback and calls callbacks
        持续读取舵机反馈并调用回调函数
        """
        while self.monitoring:
            try:
                feedback = self.read_all_feedback()
                
                for callback in self.monitor_callbacks:
                    try:
                        callback(feedback)
                    except Exception as e:
                        print(f"Monitor callback error: {e}")
                
                time.sleep(self.monitor_interval)
                
            except Exception as e:
                print(f"Monitoring error: {e}")
                time.sleep(0.1)
    
    def calibrate_limits(self, duration: float = 10.0) -> Dict[int, dict]:
        """
        Calibrate servo limits by tracking min/max positions / 校准舵机极限
        
        Args:
            duration: Calibration duration in seconds / 校准时长（秒）
            
        Returns:
            Dict of {servo_id: {'min': min_pos, 'max': max_pos}} / 极限值字典
        """
        # Disable all torques / 关闭所有扭矩
        self.torque_off_all()
        time.sleep(0.1)
        
        # Track min/max for each servo / 跟踪每个舵机的最小/最大值
        limits = {sid: {'min': float('inf'), 'max': float('-inf')} 
                  for sid in range(1, 18)}
        
        start_time = time.time()
        sample_count = 0
        
        print("Calibration started. Move servos through full range...")
        print("校准开始。请移动舵机到完整范围...")
        
        while time.time() - start_time < duration:
            positions = self.read_all_positions()
            
            for servo_id, position in positions.items():
                if position is not None:
                    limits[servo_id]['min'] = min(limits[servo_id]['min'], position)
                    limits[servo_id]['max'] = max(limits[servo_id]['max'], position)
            
            sample_count += 1
            time.sleep(0.05)  # 20Hz sampling / 20Hz采样
        
        # Update servo configurations / 更新舵机配置
        for servo_id, limit_data in limits.items():
            if limit_data['min'] != float('inf'):
                servo = self.servos.get(servo_id)
                if servo:
                    servo.update_limits(limit_data['min'], limit_data['max'])
                    print(f"Servo {servo_id}: min={limit_data['min']}, max={limit_data['max']}")
        
        print(f"Calibration complete. Sampled {sample_count} times.")
        print(f"校准完成。采样{sample_count}次。")
        
        return limits
    
    def save_config(self, filepath: str):
        """
        Save current configuration to file / 保存当前配置到文件
        
        Args:
            filepath: Path to save config / 配置文件路径
        """
        import yaml
        
        # Update config with current servo settings / 更新配置
        for servo_id, servo in self.servos.items():
            self.config['servos'][servo_id] = {
                'min_reg': servo.min_reg,
                'max_reg': servo.max_reg,
                'offset': servo.offset,
                'scale': servo.scale,
                'invert': servo.invert
            }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            yaml.dump(self.config, f, allow_unicode=True)
        
        print(f"Configuration saved to {filepath}")