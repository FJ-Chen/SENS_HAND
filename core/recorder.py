#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
recorder.py - 修复版录制与播放模块
"""

import json
import time
import threading
from typing import List, Dict, Optional
from datetime import datetime
from pathlib import Path


class RecordingFrame:
    """单个录制帧"""
    def __init__(self, timestamp: float, positions: Dict[int, int]):
        self.timestamp = timestamp
        self.positions = {int(k): v for k, v in positions.items() if v is not None}
    
    def to_dict(self) -> dict:
        return {
            'timestamp': self.timestamp,
            'positions': {str(k): v for k, v in self.positions.items()}
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'RecordingFrame':
        return cls(
            timestamp=data['timestamp'],
            positions={int(k): v for k, v in data['positions'].items()}
        )


class Recorder:
    """录制与播放管理器"""
    
    MODE_FRAME = 'frame'
    MODE_REALTIME = 'realtime'
    
    def __init__(self, servo_manager, config: dict):
        self.servo_manager = servo_manager
        self.config = config
        
        self.mode = config.get('recording', {}).get('mode', self.MODE_REALTIME)
        self.freq = config.get('recording', {}).get('freq', 20)
        self.save_dir = Path(config.get('recording', {}).get('save_dir', './recordings'))
        self.save_dir.mkdir(parents=True, exist_ok=True)
        
        # Recording state
        self.recording = False
        self.frames: List[RecordingFrame] = []
        self.record_thread: Optional[threading.Thread] = None
        self.start_time: float = 0
        
        # Playback state
        self.playing = False
        self.play_thread: Optional[threading.Thread] = None
        self.repeat_count = 1
        self.current_repeat = 0
        
        # 当前选择的播放文件
        self.selected_file: Optional[str] = None
        self.selected_file_info: Optional[dict] = None
        
        # Frame mode playback settings
        self.frame_interval = 1.0
        self.playback_servo_speed = 500
        self.playback_acceleration = 50
        self.playback_torque = 700
    
    def start_recording(self, mode: Optional[str] = None):
        """开始录制"""
        if self.recording:
            return
        
        if mode:
            self.mode = mode
        
        self.frames = []
        self.recording = True
        self.start_time = time.time()
        
        if self.mode == self.MODE_REALTIME:
            self.record_thread = threading.Thread(target=self._realtime_record_loop, daemon=True)
            self.record_thread.start()
            print(f"Realtime recording started at {self.freq}Hz")
        else:
            print("Frame-based recording started")
    
    def stop_recording(self) -> int:
        """停止录制"""
        if not self.recording:
            return 0
        
        self.recording = False
        
        if self.record_thread:
            self.record_thread.join(timeout=1.0)
            self.record_thread = None
        
        return len(self.frames)
    
    def add_frame(self):
        """手动添加帧（帧式录制）"""
        if not self.recording or self.mode != self.MODE_FRAME:
            return
        
        all_positions = self.servo_manager.read_all_positions()
        valid_positions = {k: v for k, v in all_positions.items() if v is not None}
        
        if not valid_positions:
            print("Warning: No valid positions")
            return
        
        timestamp = time.time() - self.start_time
        frame = RecordingFrame(timestamp, valid_positions)
        self.frames.append(frame)
        
        print(f"Frame {len(self.frames)} added at t={timestamp:.3f}s")
    
    def _realtime_record_loop(self):
        """实时录制循环"""
        interval = 1.0 / self.freq
        
        while self.recording:
            try:
                loop_start = time.time()
                
                all_positions = self.servo_manager.read_all_positions()
                valid_positions = {k: v for k, v in all_positions.items() if v is not None}
                
                if valid_positions:
                    timestamp = time.time() - self.start_time
                    frame = RecordingFrame(timestamp, valid_positions)
                    self.frames.append(frame)
                
                elapsed = time.time() - loop_start
                if elapsed < interval:
                    time.sleep(interval - elapsed)
                
            except Exception as e:
                print(f"Recording error: {e}")
                time.sleep(0.05)
    
    def save_recording(self, filename: Optional[str] = None) -> str:
        """保存录制到文件"""
        if not self.frames:
            return ""
        
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"recording_{self.mode}_{timestamp}.json"
        
        if not filename.endswith('.json'):
            filename = filename + '.json'
        
        if Path(filename).is_absolute():
            filepath = Path(filename)
        else:
            filepath = self.save_dir / Path(filename).name
        
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        data = {
            'meta': {
                'mode': self.mode,
                'freq': self.freq,
                'frame_count': len(self.frames),
                'duration': self.frames[-1].timestamp if self.frames else 0,
                'created': datetime.now().isoformat(),
                'servo_ids': list(self.frames[0].positions.keys()) if self.frames else []
            },
            'frames': [frame.to_dict() for frame in self.frames]
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        print(f"Recording saved to {filepath}")
        return str(filepath)
    
    def select_file(self, filepath: str) -> bool:
        """选择要播放的文件"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self.mode = data['meta']['mode']
            self.freq = data['meta'].get('freq', 20)
            self.frames = [RecordingFrame.from_dict(frame_data) 
                          for frame_data in data['frames']]
            
            self.selected_file = filepath
            self.selected_file_info = {
                'path': filepath,
                'name': Path(filepath).name,
                'mode': self.mode,
                'frame_count': len(self.frames),
                'duration': data['meta'].get('duration', 0),
                'servo_ids': data['meta'].get('servo_ids', [])
            }
            
            print(f"Selected: {Path(filepath).name}, {len(self.frames)} frames")
            return True
            
        except Exception as e:
            print(f"Failed to load file: {e}")
            self.selected_file = None
            self.selected_file_info = None
            return False
    
    def get_selected_file_info(self) -> Optional[dict]:
        """获取当前选择文件的信息"""
        return self.selected_file_info
    
    def start_playback(self, repeat_count: int = 1) -> bool:
        """开始播放"""
        if self.playing:
            return False
        
        if not self.frames:
            print("No frames to play")
            return False
        
        # 确保舵机已上电
        if not self._ensure_torque_on():
            print("Failed to enable torque")
            return False
        
        self.playing = True
        self.repeat_count = repeat_count
        self.current_repeat = 0
        
        self.play_thread = threading.Thread(target=self._playback_loop, daemon=True)
        self.play_thread.start()
        
        print(f"Playback started: {len(self.frames)} frames, {repeat_count} repeats")
        return True
    
    def stop_playback(self):
        """停止播放"""
        if not self.playing:
            return
        
        self.playing = False
        
        if self.play_thread:
            self.play_thread.join(timeout=2.0)
            self.play_thread = None
        
        print("Playback stopped")
    
    def _ensure_torque_on(self) -> bool:
        """确保舵机已上电"""
        if not self.servo_manager:
            return False
        
        enabled_count = 0
        for servo_id, servo in self.servo_manager.servos.items():
            if servo.connected:
                if not servo.torque_enabled:
                    servo.torque_on()
                    time.sleep(0.01)
                enabled_count += 1
        
        return enabled_count > 0
    
    def _playback_loop(self):
        """播放主循环"""
        try:
            for repeat in range(self.repeat_count):
                if not self.playing:
                    break
                
                self.current_repeat = repeat + 1
                print(f"Playing repeat {self.current_repeat}/{self.repeat_count}")
                
                if self.mode == self.MODE_REALTIME:
                    self._play_realtime_mode()
                else:
                    self._play_frame_mode()
                
                if repeat < self.repeat_count - 1 and self.playing:
                    time.sleep(0.3)
            
        except Exception as e:
            print(f"Playback error: {e}")
        finally:
            self.playing = False
            print("Playback completed")
    
    def _play_realtime_mode(self):
        """
        实时模式播放 - 参考 replay_angles.py
        关键：精确时间控制 + 插值
        """
        if len(self.frames) < 2:
            if self.frames:
                self._send_positions(self.frames[0].positions)
            return
        
        step_time = 1.0 / self.freq
        print(f"  Realtime: step_time={step_time:.3f}s")
        
        for i in range(len(self.frames) - 1):
            if not self.playing:
                break
            
            current_frame = self.frames[i]
            next_frame = self.frames[i + 1]
            
            frame_duration = next_frame.timestamp - current_frame.timestamp
            if frame_duration <= 0:
                frame_duration = step_time
            
            n_steps = max(1, int(frame_duration / step_time))
            start_time = time.time()
            
            for step in range(n_steps):
                if not self.playing:
                    break
                
                # 线性插值
                t = step / n_steps
                interpolated = {}
                for servo_id in current_frame.positions:
                    if servo_id in next_frame.positions:
                        start_pos = current_frame.positions[servo_id]
                        end_pos = next_frame.positions[servo_id]
                        interpolated[servo_id] = int((1 - t) * start_pos + t * end_pos)
                
                # 发送位置 - 使用高速和低加速度实现平滑运动
                self._send_positions(interpolated, speed=1000, acceleration=0, torque=700)
                
                # 精确时间控制
                target_time = start_time + step * step_time
                now = time.time()
                if now < target_time:
                    time.sleep(target_time - now)
        
        # 确保到达最后一帧
        if self.playing and self.frames:
            self._send_positions(self.frames[-1].positions, speed=500, acceleration=50, torque=700)
    
    def _play_frame_mode(self):
        """帧模式播放"""
        print(f"  Frame mode: interval={self.frame_interval}s")
        
        for i, frame in enumerate(self.frames):
            if not self.playing:
                break
            
            print(f"    Frame {i+1}/{len(self.frames)}")
            
            self._send_positions(
                frame.positions,
                speed=self.playback_servo_speed,
                acceleration=self.playback_acceleration,
                torque=self.playback_torque
            )
            
            time.sleep(self.frame_interval)
    
    def _send_positions(self, positions: Dict[int, int], 
                       speed: int = 500, acceleration: int = 50, torque: int = 700):
        """
        发送位置命令 - 使用 servo_manager 的批量写入
        """
        if not self.servo_manager or not positions:
            return
        
        try:
            self.servo_manager.set_all_positions(
                positions,
                speed=speed,
                acceleration=acceleration,
                torque=torque
            )
        except Exception as e:
            print(f"Send positions error: {e}")
    
    def set_frame_playback_settings(self, speed: int, acceleration: int, 
                                   torque: int, frame_interval: float):
        """设置帧模式播放参数"""
        self.playback_servo_speed = speed
        self.playback_acceleration = acceleration
        self.playback_torque = torque
        self.frame_interval = frame_interval
        