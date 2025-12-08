#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Gesture Recognition Worker / 手势识别工作器
Uses MediaPipe for hand tracking and controls servos
使用MediaPipe进行手部追踪并控制舵机
"""

import cv2
import mediapipe as mp
import threading
import time
from typing import Optional, Dict
import numpy as np
from PyQt5.QtCore import QObject, pyqtSignal

from .mapper import JointMapper


class GestureWorker(QObject):
    """
    Gesture recognition worker thread / 手势识别工作线程
    Captures video, detects hand landmarks, maps to servo positions
    捕获视频，检测手部关键点，映射到舵机位置
    """
    
    # 信号：发送处理后的帧用于显示
    frame_ready = pyqtSignal(object)  # numpy array
    
    def __init__(self, servo_manager, config: dict):
        """
        Initialize gesture worker / 初始化手势工作器
        
        Args:
            servo_manager: ServoManager instance (can be None) / 舵机管理器实例（可为None）
            config: Configuration dict / 配置字典
        """
        super().__init__()
        
        self.servo_manager = servo_manager
        self.config = config
        
        # MediaPipe setup / MediaPipe设置
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=1,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
        self.mp_draw = mp.solutions.drawing_utils
        
        # Joint mapper / 关节映射器
        self.mapper = JointMapper(config)
        
        # Video capture / 视频捕获
        camera_id = config.get('gesture', {}).get('camera_id', 0)
        self.cap = cv2.VideoCapture(camera_id)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        
        # Worker thread / 工作线程
        self.running = False
        self.thread: Optional[threading.Thread] = None
        
        # Sensitivity / 灵敏度
        self.sensitivity = 1.0
        
    def start(self):
        """Start worker thread / 启动工作线程"""
        if self.running:
            return
        
        if not self.cap.isOpened():
            raise RuntimeError("Failed to open camera / 无法打开摄像头")
        
        self.running = True
        self.thread = threading.Thread(target=self._worker_loop, daemon=True)
        self.thread.start()
        
    def stop(self):
        """Stop worker thread / 停止工作线程"""
        self.running = False
        
        if self.thread:
            self.thread.join(timeout=2.0)
        
        if self.cap:
            self.cap.release()
            
    def set_sensitivity(self, sensitivity: float):
        """
        Set control sensitivity / 设置控制灵敏度
        
        Args:
            sensitivity: Sensitivity value (0.1 - 2.0) / 灵敏度值
        """
        self.sensitivity = max(0.1, min(2.0, sensitivity))
        
    def _worker_loop(self):
        """
        Main worker loop / 主工作循环
        Continuously processes video frames and controls servos
        持续处理视频帧并控制舵机
        """
        while self.running:
            try:
                ret, frame = self.cap.read()
                if not ret:
                    print("Failed to read frame / 读取帧失败")
                    time.sleep(0.1)
                    continue
                
                # Flip frame horizontally for mirror effect / 水平翻转实现镜像效果
                frame = cv2.flip(frame, 1)
                
                # Convert to RGB / 转换为RGB
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                
                # Process frame / 处理帧
                results = self.hands.process(rgb_frame)
                
                # Draw landmarks / 绘制关键点
                if results.multi_hand_landmarks:
                    for hand_landmarks in results.multi_hand_landmarks:
                        # Draw on frame / 在帧上绘制
                        self.mp_draw.draw_landmarks(
                            frame, 
                            hand_landmarks, 
                            self.mp_hands.HAND_CONNECTIONS,
                            self.mp_draw.DrawingSpec(color=(0, 255, 0), thickness=2, circle_radius=2),
                            self.mp_draw.DrawingSpec(color=(255, 0, 0), thickness=2)
                        )
                        
                        # Extract joint positions / 提取关节位置
                        joints = self._extract_joints(hand_landmarks)
                        
                        # Map to servo positions / 映射到舵机位置
                        servo_positions = self.mapper.map_joints_to_servos(joints)
                        
                        # Apply sensitivity / 应用灵敏度
                        servo_positions = {
                            sid: int(pos * self.sensitivity)
                            for sid, pos in servo_positions.items()
                        }
                        
                        # Send to servos (only if connected) / 发送到舵机（仅在已连接时）
                        if self.servo_manager:
                            try:
                                # ← 这里修改：直接传位置字典，使用默认参数
                                self.servo_manager.set_all_positions(servo_positions)
                            except Exception as e:
                                # 静默失败，避免日志刷屏
                                pass
                        
                        # 在画面上显示关节信息
                        cv2.putText(frame, "Hand Detected", (10, 30), 
                                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                else:
                    cv2.putText(frame, "No Hand Detected", (10, 30), 
                            cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
                
                # 显示状态信息
                status_text = "Connected" if self.servo_manager else "Preview Only"
                cv2.putText(frame, status_text, (10, 60), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
                
                # Emit frame for display / 发送帧用于显示
                self.frame_ready.emit(frame)
                
                time.sleep(0.03)  # ~30 FPS
                
            except Exception as e:
                print(f"Gesture worker error: {e}")
                time.sleep(0.1)
                    
    def _extract_joints(self, hand_landmarks) -> Dict[str, np.ndarray]:
        """
        Extract joint positions from hand landmarks / 从手部关键点提取关节位置
        
        Args:
            hand_landmarks: MediaPipe hand landmarks / MediaPipe手部关键点
            
        Returns:
            Dict of joint positions / 关节位置字典
        """
        joints = {}
        
        # MediaPipe hand landmark indices / MediaPipe手部关键点索引
        landmark_names = [
            'WRIST',
            'THUMB_CMC', 'THUMB_MCP', 'THUMB_IP', 'THUMB_TIP',
            'INDEX_MCP', 'INDEX_PIP', 'INDEX_DIP', 'INDEX_TIP',
            'MIDDLE_MCP', 'MIDDLE_PIP', 'MIDDLE_DIP', 'MIDDLE_TIP',
            'RING_MCP', 'RING_PIP', 'RING_DIP', 'RING_TIP',
            'PINKY_MCP', 'PINKY_PIP', 'PINKY_DIP', 'PINKY_TIP'
        ]
        
        for idx, name in enumerate(landmark_names):
            landmark = hand_landmarks.landmark[idx]
            joints[name] = np.array([landmark.x, landmark.y, landmark.z])
        
        return joints
    