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
        self.positions = positions
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
            positions = self.servo_manager.read_all_positions()
        
        timestamp = time.time() - self.start_time
        frame = RecordingFrame(timestamp, positions, speeds, accelerations, torques)
        self.frames.append(frame)
        
        print(f"Frame {len(self.frames)} added at {timestamp:.3f}s / 第{len(self.frames)}帧已添加")
    
    def _realtime_record_loop(self):
        """
        Real-time recording loop / 实时录制循环
        Samples servo positions at specified frequency
        按指定频率采样舵机位置
        """
        interval = 1.0 / self.freq
        
        while self.recording:
            try:
                positions = self.servo_manager.read_all_positions()
                timestamp = time.time() - self.start_time
                
                frame = RecordingFrame(timestamp, positions)
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
            print(f"从{filepath}加载了{len(self.frames)}帧")
            
            return True
            
        except Exception as e:
            print(f"Failed to load recording: {e}")
            print(f"加载录制失败: {e}")
            return False
    
    def start_playback(self, speed: float = 1.0):
        """
        Start playback / 开始播放
        
        Args:
            speed: Playback speed multiplier / 播放速度倍率
        """
        if self.playing:
            print("Already playing / 已在播放中")
            return
        
        if not self.frames:
            print("No frames to play / 没有帧可播放")
            return
        
        self.playing = True
        self.playback_speed = speed
        
        self.play_thread = threading.Thread(target=self._playback_loop, daemon=True)
        self.play_thread.start()
        
        print(f"Playback started at {speed}x speed / 播放开始，速度{speed}x")
    
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
            
            # Send positions to servos / 发送位置到舵机
            try:
                self.servo_manager.set_all_positions(
                    frame.positions,
                    speed=frame.speeds.get(1) if frame.speeds else None,
                    acceleration=frame.accelerations.get(1) if frame.accelerations else None
                )
            except Exception as e:
                print(f"Playback error at frame {i}: {e}")
        
        self.playing = False
        print("Playback completed / 播放完成")