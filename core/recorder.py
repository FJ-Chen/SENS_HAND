#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Recording and Playback Module / 录制与播放模块
Supports frame-based and real-time 1:1 recording
支持帧式和实时1:1录制
"""

import json
import time
import threading
from typing import List, Dict, Optional, Any
from datetime import datetime
from pathlib import Path


class RecordingFrame:
    """
    Single recording frame / 单个录制帧
    """
    def __init__(self, timestamp: float, positions: Dict[int, int],
                 speeds: Optional[Dict[int, int]] = None,
                 accelerations: Optional[Dict[int, int]] = None,
                 torques: Optional[Dict[int, int]] = None):
        """
        Initialize recording frame / 初始化录制帧
        
        Args:
            timestamp: Frame timestamp / 帧时间戳
            positions: Servo positions / 舵机位置
            speeds: Optional servo speeds / 可选速度
            accelerations: Optional accelerations / 可选加速度
            torques: Optional torques / 可选扭矩
        """
        self.timestamp = timestamp
        # 过滤掉None值的位置数据
        self.positions = {k: v for k, v in positions.items() if v is not None}
        self.speeds = speeds or {}
        self.accelerations = accelerations or {}
        self.torques = torques or {}
    
    def to_dict(self) -> dict:
        """Convert to dictionary / 转换为字典"""
        return {
            'timestamp': self.timestamp,
            'positions': self.positions,
            'speeds': self.speeds,
            'accelerations': self.accelerations,
            'torques': self.torques
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'RecordingFrame':
        """Create from dictionary / 从字典创建"""
        return cls(
            timestamp=data['timestamp'],
            positions=data['positions'],
            speeds=data.get('speeds', {}),
            accelerations=data.get('accelerations', {}),
            torques=data.get('torques', {})
        )


class Recorder:
    """
    Recording and playback manager / 录制与播放管理器
    Supports both frame-based and real-time recording modes
    支持帧式和实时录制模式
    """
    
    MODE_FRAME = 'frame'
    MODE_REALTIME = 'realtime'
    
    def __init__(self, servo_manager, config: dict):
        """
        Initialize recorder / 初始化录制器
        
        Args:
            servo_manager: ServoManager instance / 舵机管理器实例
            config: Recording configuration / 录制配置
        """
        self.servo_manager = servo_manager
        self.config = config
        
        self.mode = config.get('recording', {}).get('mode', self.MODE_REALTIME)
        self.freq = config.get('recording', {}).get('freq', 20)
        self.save_dir = Path(config.get('recording', {}).get('save_dir', './recordings'))
        self.save_dir.mkdir(parents=True, exist_ok=True)
        
        # Recording state / 录制状态
        self.recording = False
        self.frames: List[RecordingFrame] = []
        self.record_thread: Optional[threading.Thread] = None
        self.start_time: float = 0
        
        # Playback state / 播放状态
        self.playing = False
        self.play_thread: Optional[threading.Thread] = None
        self.playback_speed = 1.0  # Speed multiplier / 速度倍率
        self.repeat_count = 1  # 重复次数
        self.current_repeat = 0  # 当前重复次数
        
        # Frame mode playback settings / 帧模式播放设置
        self.frame_interval = 1.0  # 帧间隔（秒）
        self.playback_servo_speed = 500  # 播放时舵机速度
        self.playback_acceleration = 50  # 播放时加速度
        self.playback_torque = 700  # 播放时扭矩
    
    def start_recording(self, mode: Optional[str] = None):
        """
        Start recording / 开始录制
        
        Args:
            mode: Recording mode ('frame' or 'realtime') / 录制模式
        """
        if self.recording:
            print("Already recording / 已在录制中")
            return
        
        if mode:
            self.mode = mode
        
        self.frames = []
        self.recording = True
        self.start_time = time.time()
        
        if self.mode == self.MODE_REALTIME:
            # Start real-time recording thread / 启动实时录制线程
            self.record_thread = threading.Thread(target=self._realtime_record_loop, daemon=True)
            self.record_thread.start()
            print(f"Real-time recording started at {self.freq}Hz / 实时录制开始，频率{self.freq}Hz")
        else:
            print("Frame-based recording started / 帧式录制开始")
    
    def stop_recording(self) -> int:
        """
        Stop recording / 停止录制
        
        Returns:
            Number of frames recorded / 录制的帧数
        """
        if not self.recording:
            return 0
        
        self.recording = False
        
        if self.record_thread:
            self.record_thread.join(timeout=1.0)
        
        frame_count = len(self.frames)
        duration = time.time() - self.start_time
        
        print(f"Recording stopped. {frame_count} frames, {duration:.2f}s")
        print(f"录制停止。{frame_count}帧，{duration:.2f}秒")
        
        return frame_count
    
    def add_frame(self, positions: Optional[Dict[int, int]] = None,
                  speeds: Optional[Dict[int, int]] = None,
                  accelerations: Optional[Dict[int, int]] = None,
                  torques: Optional[Dict[int, int]] = None):
        """
        Manually add a frame (for frame-based recording) / 手动添加帧（用于帧式录制）
        读取所有已连接舵机的当前位置
        
        Args:
            positions: Servo positions (if None, reads current) / 舵机位置
            speeds: Servo speeds / 舵机速度
            accelerations: Servo accelerations / 舵机加速度
            torques: Servo torques / 舵机扭矩
        """
        if not self.recording or self.mode != self.MODE_FRAME:
            print("Not in frame recording mode / 不在帧式录制模式")
            return
        
        if positions is None:
            # 读取所有已连接舵机的位置
            all_positions = self.servo_manager.read_all_positions()
            # 只保留有效位置（非None）
            positions = {k: v for k, v in all_positions.items() if v is not None}
        
        timestamp = time.time() - self.start_time
        frame = RecordingFrame(timestamp, positions, speeds, accelerations, torques)
        self.frames.append(frame)
        
        print(f"Frame {len(self.frames)} added at {timestamp:.3f}s with {len(positions)} servos")
        print(f"第{len(self.frames)}帧已添加，包含{len(positions)}个舵机")
    
    def _realtime_record_loop(self):
        """
        Real-time recording loop / 实时录制循环
        Samples servo positions at specified frequency
        按指定频率采样舵机位置
        """
        interval = 1.0 / self.freq
        
        while self.recording:
            try:
                all_positions = self.servo_manager.read_all_positions()
                # 过滤None值
                valid_positions = {k: v for k, v in all_positions.items() if v is not None}
                
                timestamp = time.time() - self.start_time
                frame = RecordingFrame(timestamp, valid_positions)
                self.frames.append(frame)
                
                time.sleep(interval)
                
            except Exception as e:
                print(f"Recording error: {e}")
                time.sleep(0.1)
    
    def save_recording(self, filename: Optional[str] = None) -> str:
        """
        Save recording to file / 保存录制到文件
        
        Args:
            filename: Optional filename (auto-generated if None) / 文件名
            
        Returns:
            Saved file path / 保存的文件路径
        """
        if not self.frames:
            print("No frames to save / 没有帧可保存")
            return ""
        
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"recording_{self.mode}_{timestamp}.json"
        
        filepath = self.save_dir / filename
        
        data = {
            'meta': {
                'mode': self.mode,
                'freq': self.freq,
                'frame_count': len(self.frames),
                'duration': self.frames[-1].timestamp if self.frames else 0,
                'created': datetime.now().isoformat()
            },
            'frames': [frame.to_dict() for frame in self.frames]
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        print(f"Recording saved to {filepath}")
        print(f"录制已保存到 {filepath}")
        
        return str(filepath)
    
    def load_recording(self, filepath: str) -> bool:
        """
        Load recording from file / 从文件加载录制
        
        Args:
            filepath: Path to recording file / 录制文件路径
            
        Returns:
            Success status / 成功状态
        """
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self.mode = data['meta']['mode']
            self.freq = data['meta'].get('freq', 20)
            self.frames = [RecordingFrame.from_dict(frame_data) 
                          for frame_data in data['frames']]
            
            print(f"Loaded {len(self.frames)} frames from {filepath}")
            print(f"Mode: {self.mode}")
            print(f"从{filepath}加载了{len(self.frames)}帧，模式：{self.mode}")
            
            return True
            
        except Exception as e:
            print(f"Failed to load recording: {e}")
            print(f"加载录制失败: {e}")
            return False
    
    def start_playback(self, speed: float = 1.0, repeat_count: int = 1):
        """
        Start playback / 开始播放
        
        Args:
            speed: Playback speed multiplier / 播放速度倍率
            repeat_count: Number of times to repeat / 重复次数
        """
        if self.playing:
            print("Already playing / 已在播放中")
            return
        
        if not self.frames:
            print("No frames to play / 没有帧可播放")
            return
        
        self.playing = True
        self.playback_speed = speed
        self.repeat_count = repeat_count
        self.current_repeat = 0
        
        self.play_thread = threading.Thread(target=self._playback_loop, daemon=True)
        self.play_thread.start()
        
        print(f"Playback started: {speed}x speed, {repeat_count} repeats, mode: {self.mode}")
        print(f"播放开始：速度{speed}x，重复{repeat_count}次，模式：{self.mode}")
    
    def stop_playback(self):
        """Stop playback / 停止播放"""
        if not self.playing:
            return
        
        self.playing = False
        
        if self.play_thread:
            self.play_thread.join(timeout=1.0)
        
        print("Playback stopped / 播放停止")
    
    def _playback_loop(self):
        """
        Playback loop / 播放循环
        Replays recorded frames with timing
        按时间重放录制的帧
        """
        for repeat in range(self.repeat_count):
            if not self.playing:
                break
                
            self.current_repeat = repeat + 1
            print(f"Repeat {self.current_repeat}/{self.repeat_count}")
            print(f"第{self.current_repeat}/{self.repeat_count}次重复")
            
            if self.mode == self.MODE_REALTIME:
                self._play_realtime_mode()
            else:
                self._play_frame_mode()
            
            # 如果不是最后一次重复，稍作暂停
            if repeat < self.repeat_count - 1 and self.playing:
                time.sleep(0.5)
        
        self.playing = False
        print("Playback completed / 播放完成")
    
    def _play_realtime_mode(self):
        """播放实时录制模式 - 固定参数"""
        start_time = time.time()
        
        for i, frame in enumerate(self.frames):
            if not self.playing:
                break
            
            # Calculate target time / 计算目标时间
            target_time = start_time + (frame.timestamp / self.playback_speed)
            
            # Wait until target time / 等待到目标时间
            current_time = time.time()
            if current_time < target_time:
                time.sleep(target_time - current_time)
            
            # Send positions to servos with fixed parameters / 使用固定参数发送位置
            try:
                self.servo_manager.set_all_positions(
                    frame.positions,
                    speed=1000,  # 固定速度
                    acceleration=0,  # 固定加速度（最大）
                    torque=700  # 固定扭矩
                )
            except Exception as e:
                print(f"Realtime playback error at frame {i}: {e}")
    
    def _play_frame_mode(self):
        """播放帧录制模式 - 可调参数"""
        for i, frame in enumerate(self.frames):
            if not self.playing:
                break
            
            # Send positions to servos with user settings / 使用用户设置发送位置
            try:
                self.servo_manager.set_all_positions(
                    frame.positions,
                    speed=self.playback_servo_speed,
                    acceleration=self.playback_acceleration,
                    torque=self.playback_torque
                )
                
                # Wait for frame interval / 等待帧间隔
                time.sleep(self.frame_interval)
                
            except Exception as e:
                print(f"Frame playback error at frame {i}: {e}")
    
    def set_frame_playback_settings(self, speed: int, acceleration: int, 
                                   torque: int, frame_interval: float):
        """
        Set frame mode playback parameters / 设置帧模式播放参数
        
        Args:
            speed: Servo speed / 舵机速度
            acceleration: Servo acceleration / 舵机加速度
            torque: Servo torque / 舵机扭矩
            frame_interval: Interval between frames in seconds / 帧间隔（秒）
        """
        self.playback_servo_speed = speed
        self.playback_acceleration = acceleration
        self.playback_torque = torque
        self.frame_interval = frame_interval
        
        print(f"Frame playback settings: Speed={speed}, Accel={acceleration}, Torque={torque}, Interval={frame_interval}s")
        print(f"帧播放设置：速度={speed}, 加速度={acceleration}, 扭矩={torque}, 间隔={frame_interval}秒")
        