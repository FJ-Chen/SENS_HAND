#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
servo_manager.py - 修复版
使用 SyncWritePosEx 进行批量写入
"""

from typing import Dict, List, Optional
import threading
import time
import json
import os
from datetime import datetime
from .servo import Servo

# 从 hls.py 导入常量
HLS_TORQUE_ENABLE = 40
HLS_ACC = 41


class ServoManager:
    """多舵机管理器"""
    
    def __init__(self, serial_manager, config: dict):
        self.serial_manager = serial_manager
        self.packet_handler = serial_manager.packet_handler  # hls 实例
        self.config = config
        
        # 校准相关
        self.calibration_active = False
        self.calibration_thread = None
        self.calibration_data = {}
        
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
        
        self.load_calibration_data()
    
    def set_all_positions(self, positions: Dict[int, int], 
                          speed: Optional[int] = None,
                          acceleration: Optional[int] = None,
                          torque: Optional[int] = None) -> Dict[int, bool]:
        """
        设置多个舵机位置 - 使用 SyncWritePosEx 批量写入
        """
        results = {}
        
        if not positions:
            return results
        
        default_speed = speed if speed is not None else 500
        default_accel = acceleration if acceleration is not None else 50
        default_torque = torque if torque is not None else 700
        
        # 先清除之前的同步写入参数
        self.packet_handler.groupSyncWrite.clearParam()
        
        # 添加每个舵机的参数
        valid_count = 0
        for servo_id, position in positions.items():
            servo = self.servos.get(servo_id)
            if servo and servo.connected:
                # 应用反转
                actual_position = -position if servo.invert else position
                
                # 使用 SyncWritePosEx 添加参数
                success = self.packet_handler.SyncWritePosEx(
                    servo_id, 
                    actual_position, 
                    default_speed, 
                    default_accel, 
                    default_torque
                )
                
                if success:
                    valid_count += 1
                    results[servo_id] = True
                else:
                    results[servo_id] = False
            else:
                results[servo_id] = False
        
        # 发送同步写入命令
        if valid_count > 0:
            tx_result = self.packet_handler.groupSyncWrite.txPacket()
            if tx_result != 0:  # COMM_SUCCESS = 0
                print(f"SyncWrite txPacket failed: {tx_result}")
                # 如果同步写入失败，尝试逐个写入
                return self._fallback_individual_write(positions, default_speed, default_accel, default_torque)
        
        # 清除参数，为下次写入做准备
        self.packet_handler.groupSyncWrite.clearParam()
        
        return results
    
    def _fallback_individual_write(self, positions: Dict[int, int],
                                   speed: int, accel: int, torque: int) -> Dict[int, bool]:
        """降级：逐个写入（当同步写入失败时）"""
        results = {}
        for servo_id, position in positions.items():
            servo = self.servos.get(servo_id)
            if servo and servo.connected:
                results[servo_id] = servo.set_goal_position_with_torque(
                    position, torque, speed, accel
                )
                time.sleep(0.002)  # 短延迟避免总线冲突
            else:
                results[servo_id] = False
        return results
    
    def get_servo(self, servo_id: int) -> Optional[Servo]:
        """获取舵机实例"""
        return self.servos.get(servo_id)
    
    def ping_all(self) -> Dict[int, bool]:
        """检查所有舵机连接"""
        results = {}
        for servo_id in range(1, 18):
            servo = self.servos.get(servo_id)
            if servo:
                results[servo_id] = servo.ping()
            else:
                results[servo_id] = False
            time.sleep(0.01)
        return results
    
    def torque_on_all(self) -> Dict[int, bool]:
        """所有舵机上电"""
        results = {}
        for servo_id, servo in self.servos.items():
            if servo.connected:
                results[servo_id] = servo.torque_on()
                time.sleep(0.01)
            else:
                results[servo_id] = False
        return results
    
    def torque_off_all(self) -> Dict[int, bool]:
        """所有舵机下电"""
        results = {}
        for servo_id, servo in self.servos.items():
            if servo.connected:
                results[servo_id] = servo.torque_off()
                time.sleep(0.01)
            else:
                results[servo_id] = False
        return results
    
    def read_all_positions(self) -> Dict[int, Optional[int]]:
        """读取所有舵机位置"""
        positions = {}
        for servo_id, servo in self.servos.items():
            if servo.connected:
                positions[servo_id] = servo.read_present_position()
                time.sleep(0.002)
            else:
                positions[servo_id] = None
        return positions
    
    # ========== 校准相关方法 ==========
    
    def get_calibration_file_path(self):
        """获取校准文件路径"""
        config_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config')
        os.makedirs(config_dir, exist_ok=True)
        return os.path.join(config_dir, 'servo_calibration.json')
    
    def load_calibration_data(self):
        """加载校准数据"""
        try:
            file_path = self.get_calibration_file_path()
            if os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                for servo_id, limits in data.get('limits', {}).items():
                    servo_id = int(servo_id)
                    if servo_id in self.servos:
                        self.servos[servo_id].update_limits(limits['min'], limits['max'])
                
                print(f"Loaded calibration from {file_path}")
                return True
        except Exception as e:
            print(f"Error loading calibration: {e}")
        return False
    
    def save_calibration_data(self):
        """保存校准数据"""
        try:
            file_path = self.get_calibration_file_path()
            
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
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(calibration_data, f, indent=2, ensure_ascii=False)
            
            print(f"Saved calibration to {file_path}")
            return True
        except Exception as e:
            print(f"Error saving calibration: {e}")
            return False
    
    def start_calibration(self) -> bool:
        """开始校准"""
        if self.calibration_active:
            return False
        
        self.calibration_data = {}
        for servo_id in range(1, 18):
            self.calibration_data[servo_id] = {'positions': []}
        
        self.calibration_active = True
        self.calibration_thread = threading.Thread(target=self._calibration_worker, daemon=True)
        self.calibration_thread.start()
        
        print("Calibration started")
        return True
    
    def stop_calibration(self) -> bool:
        """停止校准"""
        if not self.calibration_active:
            return False
        
        self.calibration_active = False
        
        if self.calibration_thread and self.calibration_thread.is_alive():
            self.calibration_thread.join(timeout=1.0)
        
        success = self.save_calibration_data()
        
        if success:
            for servo_id, data in self.calibration_data.items():
                if data['positions']:
                    servo = self.servos.get(servo_id)
                    if servo:
                        min_pos = min(data['positions'])
                        max_pos = max(data['positions'])
                        servo.update_limits(min_pos, max_pos)
        
        print("Calibration stopped")
        return success
    
    def _calibration_worker(self):
        """校准工作线程"""
        while self.calibration_active:
            try:
                for servo_id, servo in self.servos.items():
                    if servo.connected:
                        position = servo.read_present_position()
                        if position is not None:
                            self.calibration_data[servo_id]['positions'].append(position)
                
                time.sleep(0.1)
            except Exception as e:
                print(f"Calibration error: {e}")
                time.sleep(0.1)
    
    def has_calibration_data(self) -> bool:
        """检查是否有校准数据"""
        return os.path.exists(self.get_calibration_file_path())
    
    def get_servo_limits(self, servo_id: int) -> Optional[Dict[str, int]]:
        """获取舵机限制"""
        servo = self.servos.get(servo_id)
        if servo:
            return {'min': servo.min_reg, 'max': servo.max_reg}
        return None
    