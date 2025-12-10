#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Custom UI Widgets / 自定义UI组件
PyQt5 custom widgets for servo control
PyQt5自定义舵机控制组件
"""

from typing import Optional
from PyQt5.QtWidgets import (QWidget, QGroupBox, QVBoxLayout, QHBoxLayout, 
                             QLabel, QSlider, QPushButton, QSpinBox, QFrame, QMessageBox)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont

from .translations import Translations as T


class ServoControlWidget(QFrame):
    """
    Individual servo control widget / 单个舵机控制组件
    Displays and controls a single servo motor
    显示和控制单个舵机
    """
    
    # Signals / 信号
    position_changed = pyqtSignal(int, int)  # servo_id, position
    speed_changed = pyqtSignal(int, int)     # servo_id, speed
    accel_changed = pyqtSignal(int, int)     # servo_id, acceleration
    torque_changed = pyqtSignal(int, int)    # servo_id, torque_value
    torque_toggled = pyqtSignal(int, bool)   # servo_id, enabled
    
    def __init__(self, servo_id: int, parent: Optional[QWidget] = None):
        """
        Initialize servo control widget / 初始化舵机控制组件
        
        Args:
            servo_id: Servo ID (1-17) / 舵机ID (1-17)
            parent: Parent widget / 父组件
        """
        super().__init__(parent)
        self.servo_id = servo_id
        self.connected = False
        
        # Position limits / 位置限制
        self.min_position = -32767
        self.max_position = 32767
        
        # Calibration limits / 校准限制
        self.calibration_limits = None
        
        # Initialize UI / 初始化UI
        self.init_ui()
        
    def init_ui(self):
        """Initialize user interface / 初始化用户界面"""
        # Main layout / 主布局
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Title / 标题
        title = QLabel(f"{T.get('servo_id')} {self.servo_id}")
        title.setFont(QFont("Arial", 10, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # Connection status / 连接状态
        self.status_label = QLabel(T.get('disconnected'))
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("color: red;")
        layout.addWidget(self.status_label)
        
        # Position control / 位置控制
        pos_group = QGroupBox(T.get('position'))
        pos_layout = QVBoxLayout()
        
        # Position slider / 位置滑块
        self.position_slider = QSlider(Qt.Horizontal)
        self.position_slider.setMinimum(self.min_position)
        self.position_slider.setMaximum(self.max_position)
        self.position_slider.setValue(0)
        self.position_slider.wheelEvent = lambda event: None 
        self.position_slider.valueChanged.connect(self.on_position_changed)
        pos_layout.addWidget(self.position_slider)
        
        # Position limits display / 位置限制显示
        limits_layout = QHBoxLayout()
        self.min_limit_label = QLabel(str(self.min_position))
        self.min_limit_label.setAlignment(Qt.AlignLeft)
        self.max_limit_label = QLabel(str(self.max_position))
        self.max_limit_label.setAlignment(Qt.AlignRight)
        
        limits_layout.addWidget(self.min_limit_label)
        limits_layout.addStretch()
        limits_layout.addWidget(self.max_limit_label)
        pos_layout.addLayout(limits_layout)
        
        # Position display / 位置显示
        pos_display_layout = QHBoxLayout()
        pos_display_layout.addWidget(QLabel(T.get('target') + ":"))
        
        self.position_spinbox = QSpinBox()
        self.position_spinbox.setMinimum(self.min_position)
        self.position_spinbox.setMaximum(self.max_position)
        self.position_spinbox.setValue(0)
        # 禁用鼠标滚轮
        self.position_spinbox.wheelEvent = lambda event: None
        self.position_spinbox.setFocusPolicy(Qt.StrongFocus)
        self.position_spinbox.valueChanged.connect(self.on_target_position_changed)
        pos_display_layout.addWidget(self.position_spinbox)
        
        pos_display_layout.addWidget(QLabel(T.get('current') + ":"))
        self.current_position_label = QLabel("0")
        pos_display_layout.addWidget(self.current_position_label)
        
        pos_layout.addLayout(pos_display_layout)
        pos_group.setLayout(pos_layout)
        layout.addWidget(pos_group)
        
        # Speed control / 速度控制
        speed_group = QGroupBox(T.get('speed'))
        speed_layout = QVBoxLayout()
        
        self.speed_slider = QSlider(Qt.Horizontal)
        self.speed_slider.setMinimum(0)
        self.speed_slider.setMaximum(1000)
        self.speed_slider.setValue(100)
        self.speed_slider.valueChanged.connect(self.on_speed_changed)
        speed_layout.addWidget(self.speed_slider)
        
        speed_display_layout = QHBoxLayout()
        self.speed_spinbox = QSpinBox()
        self.speed_spinbox.setMinimum(0)
        self.speed_spinbox.setMaximum(1000)
        self.speed_spinbox.setValue(100)
        # 禁用鼠标滚轮
        self.speed_spinbox.wheelEvent = lambda event: None
        self.speed_spinbox.setFocusPolicy(Qt.StrongFocus)
        self.speed_spinbox.valueChanged.connect(self.speed_slider.setValue)
        speed_display_layout.addWidget(self.speed_spinbox)
        
        speed_layout.addLayout(speed_display_layout)
        speed_group.setLayout(speed_layout)
        layout.addWidget(speed_group)
        
        # Acceleration control / 加速度控制
        accel_group = QGroupBox(T.get('accel'))
        accel_layout = QVBoxLayout()
        
        self.accel_slider = QSlider(Qt.Horizontal)
        self.accel_slider.setMinimum(0)
        self.accel_slider.setMaximum(255)
        self.accel_slider.setValue(50)
        self.accel_slider.valueChanged.connect(self.on_accel_changed)
        accel_layout.addWidget(self.accel_slider)
        
        accel_display_layout = QHBoxLayout()
        self.accel_spinbox = QSpinBox()
        self.accel_spinbox.setMinimum(0)
        self.accel_spinbox.setMaximum(255)
        self.accel_spinbox.setValue(50)
        # 禁用鼠标滚轮
        self.accel_spinbox.wheelEvent = lambda event: None
        self.accel_spinbox.setFocusPolicy(Qt.StrongFocus)
        self.accel_spinbox.valueChanged.connect(self.accel_slider.setValue)
        accel_display_layout.addWidget(self.accel_spinbox)
        
        accel_layout.addLayout(accel_display_layout)
        accel_group.setLayout(accel_layout)
        layout.addWidget(accel_group)
        
        # Torque control / 扭矩控制
        torque_group = QGroupBox("扭矩控制")
        torque_layout = QVBoxLayout()
        
        # Torque value / 扭矩值
        torque_value_layout = QHBoxLayout()
        torque_value_layout.addWidget(QLabel("扭矩值:"))
        
        self.torque_spinbox = QSpinBox()
        self.torque_spinbox.setMinimum(0)
        self.torque_spinbox.setMaximum(1000)
        self.torque_spinbox.setValue(500)
        self.torque_spinbox.setSuffix("(max:2047)")
        # 禁用鼠标滚轮
        self.torque_spinbox.wheelEvent = lambda event: None
        self.torque_spinbox.setFocusPolicy(Qt.StrongFocus)
        self.torque_spinbox.valueChanged.connect(self.on_torque_value_changed)
        torque_value_layout.addWidget(self.torque_spinbox)
        
        torque_layout.addLayout(torque_value_layout)
        
        # Torque enable button / 扭矩启用按钮
        self.torque_button = QPushButton(T.get('torque_off'))
        self.torque_button.setCheckable(True)
        self.torque_button.clicked.connect(self.on_torque_toggled)
        torque_layout.addWidget(self.torque_button)
        
        torque_group.setLayout(torque_layout)
        layout.addWidget(torque_group)
        
        # Style frame / 设置框架样式
        self.setFrameStyle(QFrame.StyledPanel | QFrame.Raised)
        self.setLineWidth(2)
        
        # Disable controls initially / 初始禁用控制
        self.set_enabled(False)
        
    def set_connected(self, connected: bool):
        """
        Set connection status / 设置连接状态
        
        Args:
            connected: True if servo is connected / 舵机是否连接
        """
        self.connected = connected
        
        if connected:
            self.status_label.setText(T.get('online'))
            self.status_label.setStyleSheet("color: green;")
            # 连接后默认不启用位置控制（需要先上电）
            # Position control disabled by default after connection (need to enable torque first)
            self.speed_slider.setEnabled(True)
            self.speed_spinbox.setEnabled(True)
            self.accel_slider.setEnabled(True)
            self.accel_spinbox.setEnabled(True)
            self.torque_spinbox.setEnabled(True)
            self.torque_button.setEnabled(True)
            # 位置控制需要扭矩启用后才能使用
            # Position controls require torque to be enabled
            self.position_slider.setEnabled(False)
            self.position_spinbox.setEnabled(False)
        else:
            self.status_label.setText(T.get('offline'))
            self.status_label.setStyleSheet("color: red;")
            self.set_enabled(False)
            
    def set_enabled(self, enabled: bool):
        """
        Enable/disable controls / 启用/禁用控制
        
        Args:
            enabled: True to enable controls / 是否启用控制
        """
        self.position_slider.setEnabled(enabled)
        self.position_spinbox.setEnabled(enabled)
        self.speed_slider.setEnabled(enabled)
        self.speed_spinbox.setEnabled(enabled)
        self.accel_slider.setEnabled(enabled)
        self.accel_spinbox.setEnabled(enabled)
        self.torque_spinbox.setEnabled(enabled)
        self.torque_button.setEnabled(enabled)
        
    def update_limits(self, min_pos: int, max_pos: int):
        """
        Update position limits / 更新位置限制
        
        Args:
            min_pos: Minimum position / 最小位置
            max_pos: Maximum position / 最大位置
        """
        self.min_position = min_pos
        self.max_position = max_pos
        self.calibration_limits = (min_pos, max_pos)
        
        # Update UI elements
        self.position_slider.setMinimum(min_pos)
        self.position_slider.setMaximum(max_pos)
        self.position_spinbox.setMinimum(min_pos)
        self.position_spinbox.setMaximum(max_pos)
        
        # Update limit labels
        self.min_limit_label.setText(str(min_pos))
        self.max_limit_label.setText(str(max_pos))
        
    def update_position(self, position: int):
        """
        Update current position display / 更新当前位置显示
        
        Args:
            position: Current position / 当前位置
        """
        self.current_position_label.setText(str(position))
        
    def validate_position(self, position: int) -> bool:
        """
        Validate if position is within calibrated limits
        
        Args:
            position: Position to validate
            
        Returns:
            True if valid, False otherwise
        """
        if self.calibration_limits:
            min_pos, max_pos = self.calibration_limits
            return min_pos <= position <= max_pos
        return True
        
    def on_target_position_changed(self, value: int):
        """Handle target position spinbox change"""
        # Validate against calibration limits
        if not self.validate_position(value):
            min_pos, max_pos = self.calibration_limits if self.calibration_limits else (self.min_position, self.max_position)
            QMessageBox.warning(self, "位置限制", 
                              f"目标位置 {value} 超出校准范围 [{min_pos}, {max_pos}]")
            # Reset to current slider value
            self.position_spinbox.blockSignals(True)
            self.position_spinbox.setValue(self.position_slider.value())
            self.position_spinbox.blockSignals(False)
            return
        
        # Update slider and emit signal
        self.position_slider.blockSignals(True)
        self.position_slider.setValue(value)
        self.position_slider.blockSignals(False)
        self.position_changed.emit(self.servo_id, value)
        
    def on_position_changed(self, value: int):
        """Handle position slider change / 处理位置滑块变化"""
        self.position_spinbox.blockSignals(True)
        self.position_spinbox.setValue(value)
        self.position_spinbox.blockSignals(False)
        self.position_changed.emit(self.servo_id, value)
        
    def on_speed_changed(self, value: int):
        """Handle speed slider change / 处理速度滑块变化"""
        self.speed_spinbox.blockSignals(True)
        self.speed_spinbox.setValue(value)
        self.speed_spinbox.blockSignals(False)
        self.speed_changed.emit(self.servo_id, value)
        
    def on_accel_changed(self, value: int):
        """Handle acceleration slider change / 处理加速度滑块变化"""
        self.accel_spinbox.blockSignals(True)
        self.accel_spinbox.setValue(value)
        self.accel_spinbox.blockSignals(False)
        self.accel_changed.emit(self.servo_id, value)
    
    def on_torque_value_changed(self, value: int):
        """Handle torque value change"""
        self.torque_changed.emit(self.servo_id, value)
        
    def on_torque_toggled(self):
        """
        Handle torque button toggle / 处理扭矩按钮切换
        下电时禁用位置控制 / Disable position control when torque off
        """
        enabled = self.torque_button.isChecked()
        self.update_torque_button_text(enabled)
        
        # 根据扭矩状态启用/禁用位置控制
        # Enable/disable position controls based on torque state
        self.position_slider.setEnabled(enabled and self.connected)
        self.position_spinbox.setEnabled(enabled and self.connected)
        
        self.torque_toggled.emit(self.servo_id, enabled)
        
    def update_torque_button_text(self, enabled: bool):
        """
        Update torque button text / 更新扭矩按钮文本
        
        Args:
            enabled: True if torque is enabled / 扭矩是否启用
        """
        if enabled:
            self.torque_button.setText(T.get('torque_on'))
            self.torque_button.setStyleSheet("background-color: #90EE90;")
        else:
            self.torque_button.setText(T.get('torque_off'))
            self.torque_button.setStyleSheet("")

    def get_torque_value(self) -> int:
        """Get current torque value"""
        return self.torque_spinbox.value()