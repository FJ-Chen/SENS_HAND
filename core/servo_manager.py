#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Servo Manager using SCServo SDK
使用SCServo SDK的舵机管理器
"""

from typing import Dict, List, Optional, Callable
import threading
import time
import json
import os
from datetime import datetime
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
        
        # 校准相关
        self.calibration_active = False
        self.calibration_data = {}
        self.calibration_thread = None
        
        # 监控相关
        self.monitoring = False
        self.monitor_thread: Optional[threading.Thread] = None
        self.monitor_callbacks: List[Callable] = []
        self.monitor_interval = 0.05
        
        # 加载校准文件
        self.load_calibration_data()
    
    def get_calibration_file_path(self):
        """获取校准文件路径"""
        config_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config')
        os.makedirs(config_dir, exist_ok=True)
        return os.path.join(config_dir, 'servo_calibration.json')
    
    def load_calibration_data(self):
        """加载校准数据 - 不自动移动舵机"""
        try:
            file_path = self.get_calibration_file_path()
            if os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                # 只更新舵机限制，不移动舵机
                for servo_id, limits in data.get('limits', {}).items():
                    servo_id = int(servo_id)
                    if servo_id in self.servos:
                        servo = self.servos[servo_id]
                        servo.update_limits(limits['min'], limits['max'])
                
                print(f"Loaded calibration data from {file_path}")
                return True
            else:
                print("No calibration file found")
                return False
        except Exception as e:
            print(f"Error loading calibration data: {e}")
            return False
    
    def save_calibration_data(self):
        """保存校准数据"""
        try:
            file_path = self.get_calibration_file_path()
            
            # 构建校准数据
            calibration_data = {
                'timestamp': datetime.now().isoformat(),
                'limits': {}
            }
            
            for servo_id, data in self.calibration_data.items():
                if data['positions']:
                    calibration_data['limits'][servo_id] = {
                        'min': min(data['positions']),
                        'max': max(data['positions'])
                    }
            
            # 保存到文件
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(calibration_data, f, indent=2, ensure_ascii=False)
            
            print(f"Saved calibration data to {file_path}")
            return True
            
        except Exception as e:
            print(f"Error saving calibration data: {e}")
            return False
    
    def start_calibration(self) -> bool:
        """开始校准"""
        if self.calibration_active:
            return False
        
        # 初始化校准数据
        self.calibration_data = {}
        for servo_id in range(1, 18):
            self.calibration_data[servo_id] = {
                'positions': [],
                'min_pos': float('inf'),
                'max_pos': float('-inf')
            }
        
        self.calibration_active = True
        
        # 启动校准线程
        self.calibration_thread = threading.Thread(target=self._calibration_worker)
        self.calibration_thread.daemon = True
        self.calibration_thread.start()
        
        print("Calibration started")
        return True
    
    def stop_calibration(self) -> bool:
        """停止校准 - 不自动移动舵机"""
        if not self.calibration_active:
            return False
        
        self.calibration_active = False
        
        # 等待线程结束
        if self.calibration_thread and self.calibration_thread.is_alive():
            self.calibration_thread.join(timeout=1.0)
        
        # 保存校准结果
        success = self.save_calibration_data()
        
        # 只更新舵机限制，不自动移动
        if success:
            for servo_id, data in self.calibration_data.items():
                if data['positions']:
                    servo = self.servos.get(servo_id)
                    if servo:
                        min_pos = min(data['positions'])
                        max_pos = max(data['positions'])
                        servo.update_limits(min_pos, max_pos)
        
        print("Calibration stopped and saved")
        return success
    
    def _calibration_worker(self):
        """校准工作线程（10Hz采样）"""
        while self.calibration_active:
            try:
                # 读取所有舵机位置
                for servo_id, servo in self.servos.items():
                    if servo.connected:
                        position = servo.read_present_position()
                        if position is not None:
                            # 记录位置
                            self.calibration_data[servo_id]['positions'].append(position)
                            
                            # 更新最大最小值
                            current_min = self.calibration_data[servo_id]['min_pos']
                            current_max = self.calibration_data[servo_id]['max_pos']
                            
                            self.calibration_data[servo_id]['min_pos'] = min(current_min, position)
                            self.calibration_data[servo_id]['max_pos'] = max(current_max, position)
                
                time.sleep(0.1)  # 10Hz采样
                
            except Exception as e:
                print(f"Calibration error: {e}")
                time.sleep(0.1)
    
    def get_calibration_status(self) -> Dict:
        """获取校准状态"""
        status = {
            'active': self.calibration_active,
            'data': {}
        }
        
        if self.calibration_active:
            for servo_id, data in self.calibration_data.items():
                if data['positions']:
                    status['data'][servo_id] = {
                        'samples': len(data['positions']),
                        'min_pos': data['min_pos'] if data['min_pos'] != float('inf') else None,
                        'max_pos': data['max_pos'] if data['max_pos'] != float('-inf') else None,
                        'range': data['max_pos'] - data['min_pos'] if data['min_pos'] != float('inf') else 0
                    }
        
        return status
    
    def has_calibration_data(self) -> bool:
        """检查是否有校准数据"""
        return os.path.exists(self.get_calibration_file_path())
    
    def get_servo_limits(self, servo_id: int) -> Optional[Dict[str, int]]:
        """获取舵机限制"""
        servo = self.servos.get(servo_id)
        if servo:
            return {
                'min': servo.min_reg,
                'max': servo.max_reg
            }
        return None
    
    def get_servo(self, servo_id: int) -> Optional[Servo]:
        """获取舵机实例"""
        return self.servos.get(servo_id)
    
    def ping_all(self) -> Dict[int, bool]:
        """检查所有舵机连接（限制超时）- 不自动移动"""
        results = {}
        for servo_id in range(1, 18):
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
        """所有连接的舵机下电 - 确保完全断电"""
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
                          acceleration: Optional[int] = None,
                          torque: Optional[int] = None) -> Dict[int, bool]:
        """设置多个舵机位置 - 改进参数处理"""
        results = {}
        default_speed = speed or 100
        default_accel = acceleration or 50
        default_torque = torque or 500
        
        for servo_id, position in positions.items():
            servo = self.servos.get(servo_id)
            if servo and servo.connected:
                # 使用指定的扭矩值
                results[servo_id] = servo.set_goal_position_with_torque(
                    position, default_torque, default_speed, default_accel
                )
                time.sleep(0.003)  # 减少延迟
            else:
                results[servo_id] = False
        return results
    
    def read_all_positions(self) -> Dict[int, Optional[int]]:
        """读取所有连接舵机的位置 - 改进错误处理"""
        positions = {}
        for servo_id, servo in self.servos.items():
            if servo.connected:
                try:
                    position = servo.read_present_position()
                    positions[servo_id] = position
                except Exception:
                    # 出错时记录None而不是跳过
                    positions[servo_id] = None
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
    