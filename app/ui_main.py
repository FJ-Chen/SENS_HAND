#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Main Window / 主窗口
PyQt5 main application window with all controls
PyQt5主应用窗口,包含所有控制
"""

import sys
from typing import Dict, Optional
from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QTabWidget, QGroupBox, QComboBox, QPushButton,
                             QLabel, QTextEdit, QFileDialog, QMessageBox,
                             QScrollArea, QGridLayout, QSpinBox, QSlider,
                             QCheckBox, QDoubleSpinBox)
from PyQt5.QtCore import Qt, QTimer, pyqtSlot
from PyQt5.QtGui import QFont

from .translations import Translations as T
from .ui_widgets import ServoControlWidget
from core.serial_manager import SerialManager
from core.servo_manager import ServoManager
from core.recorder import Recorder
from gesture.gesture_worker import GestureWorker


class MainWindow(QMainWindow):
    """
    Main application window / 主应用窗口
    """
    
    def __init__(self, config: dict):
        """
        Initialize main window / 初始化主窗口
        
        Args:
            config: Application configuration / 应用配置
        """
        super().__init__()
        self.config = config
        
        # Core components / 核心组件
        self.serial_manager: Optional[SerialManager] = None
        self.servo_manager: Optional[ServoManager] = None
        self.recorder: Optional[Recorder] = None
        self.gesture_worker: Optional[GestureWorker] = None
        
        # UI components / UI组件
        self.servo_widgets: Dict[int, ServoControlWidget] = {}
        
        # Initialize UI / 初始化UI
        self.init_ui()
        
        # Setup update timer / 设置更新定时器
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_servo_feedback)
        
        # Set window properties / 设置窗口属性
        self.setWindowTitle(T.get('main_window'))
        self.setGeometry(100, 100, 1400, 900)

        # Check calibrate / 检查校准
        self.calibrating = False
        
    def init_ui(self):
        """Initialize user interface / 初始化用户界面"""
        # Central widget / 中心部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout / 主布局
        main_layout = QVBoxLayout()
        central_widget.setLayout(main_layout)
        
        # Top control bar / 顶部控制栏
        control_bar = self.create_control_bar()
        main_layout.addWidget(control_bar)
        
        # Tab widget for different sections / 标签页组件
        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)
        
        # Create tabs / 创建标签页
        self.create_servo_control_tab()
        self.create_recording_tab()
        self.create_gesture_tab()
        self.create_log_tab()
        
        # Bottom status bar / 底部状态栏
        self.statusBar().showMessage(T.get('disconnected'))
        
    def retranslate_ui(self):
        """
        Re-apply translations to all UI elements / 重新应用翻译到所有UI元素
        """
        # Window title / 窗口标题
        self.setWindowTitle(T.get('main_window'))
        
        # Tab titles / 标签页标题
        self.tabs.setTabText(0, T.get('servo_id'))
        self.tabs.setTabText(1, T.get('recording'))
        self.tabs.setTabText(2, T.get('gesture'))
        self.tabs.setTabText(3, T.get('log'))
        
        # Control bar / 控制栏
        self.refresh_ports_btn.setText(T.get('refresh_ports'))
        if self.serial_manager and self.serial_manager.is_connected():
            self.connect_btn.setText(T.get('disconnect'))
        else:
            self.connect_btn.setText(T.get('connect'))
        
        # Servo control tab / 舵机控制标签页
        self.all_on_btn.setText(T.get('all_on'))
        self.all_off_btn.setText(T.get('all_off'))
        self.calibrate_btn.setText(T.get('calibrate'))
        
        # Recording tab / 录制标签页
        self.recording_group.setTitle(T.get('recording'))
        if self.recorder and self.recorder.recording:
            self.record_btn.setText(T.get('stop_record'))
        else:
            self.record_btn.setText(T.get('record'))
        self.add_frame_btn.setText(T.get('add_frame'))
        self.save_record_btn.setText(T.get('save_recording'))
        self.load_record_btn.setText(T.get('load_recording'))
        
        self.playback_group.setTitle(T.get('play'))
        if self.recorder and self.recorder.playing:
            self.play_btn.setText(T.get('stop_play'))
        else:
            self.play_btn.setText(T.get('play'))
        
        # Gesture tab / 手势标签页
        self.gesture_control_group.setTitle(T.get('gesture'))
        self.gesture_enable_cb.setText(T.get('gesture_enable'))
        
        # Update status labels / 更新状态标签
        if self.serial_manager and self.serial_manager.is_connected():
            self.statusBar().showMessage(T.get('connected'))
        else:
            self.statusBar().showMessage(T.get('disconnected'))
        
        if self.gesture_worker:
            self.gesture_status_label.setText(T.get('status') + ": " + T.get('online'))
        else:
            self.gesture_status_label.setText(T.get('status') + ": " + T.get('offline'))
        
        # Log message / 日志消息
        self.log(f"Language changed / 语言已切换")
        
    def create_control_bar(self) -> QWidget:
        """
        Create top control bar / 创建顶部控制栏
        
        Returns:
            Control bar widget / 控制栏组件
        """
        group = QGroupBox(T.get('connect'))
        layout = QHBoxLayout()
        
        # Port selection / 端口选择
        layout.addWidget(QLabel(T.get('port') + ":"))
        self.port_combo = QComboBox()
        self.refresh_ports()
        layout.addWidget(self.port_combo)
        
        # Refresh button / 刷新按钮
        self.refresh_ports_btn = QPushButton(T.get('refresh_ports'))
        self.refresh_ports_btn.clicked.connect(self.refresh_ports)
        layout.addWidget(self.refresh_ports_btn)
        
        # Baudrate selection / 波特率选择
        layout.addWidget(QLabel(T.get('baudrate') + ":"))
        self.baudrate_combo = QComboBox()
        self.baudrate_combo.addItems(['1000000', '115200', '57600', '38400', '19200', '9600'])
        self.baudrate_combo.setCurrentText('1000000')
        layout.addWidget(self.baudrate_combo)
        
        # Connect button / 连接按钮
        self.connect_btn = QPushButton(T.get('connect'))
        self.connect_btn.clicked.connect(self.toggle_connection)
        layout.addWidget(self.connect_btn)
        
        layout.addStretch()
        
        # Language selection / 语言选择
        layout.addWidget(QLabel(T.get('language') + ":"))
        self.lang_combo = QComboBox()
        self.lang_combo.addItems([T.get('chinese'), T.get('english')])
        
        # Set current language / 设置当前语言
        current_lang = self.config.get('ui', {}).get('language', 'cn')
        if current_lang == 'en':
            self.lang_combo.setCurrentText(T.get('english'))
        else:
            self.lang_combo.setCurrentText(T.get('chinese'))
        
        # Connect signal / 连接信号
        self.lang_combo.currentTextChanged.connect(self.on_language_changed)
        layout.addWidget(self.lang_combo)
        
        group.setLayout(layout)
        return group
        
    def create_servo_control_tab(self):
        """Create servo control tab / 创建舵机控制标签页"""
        tab = QWidget()
        layout = QVBoxLayout()
        
        # Batch control buttons / 批量控制按钮
        batch_layout = QHBoxLayout()
        
        self.all_on_btn = QPushButton(T.get('all_on'))
        self.all_on_btn.clicked.connect(self.torque_on_all)
        batch_layout.addWidget(self.all_on_btn)
        
        self.all_off_btn = QPushButton(T.get('all_off'))
        self.all_off_btn.clicked.connect(self.torque_off_all)
        batch_layout.addWidget(self.all_off_btn)
        
        self.calibrate_btn = QPushButton(T.get('calibrate'))
        self.calibrate_btn.clicked.connect(self.calibrate_limits)
        batch_layout.addWidget(self.calibrate_btn)
        
        batch_layout.addStretch()
        layout.addLayout(batch_layout)
        
        # Scroll area for servo widgets / 舵机组件滚动区域
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_widget = QWidget()
        scroll_layout = QGridLayout()
        scroll_widget.setLayout(scroll_layout)
        scroll.setWidget(scroll_widget)
        
        # Create 17 servo control widgets / 创建17个舵机控制组件
        for i in range(1, 18):
            servo_widget = ServoControlWidget(i)
            servo_widget.position_changed.connect(self.on_servo_position_changed)
            servo_widget.speed_changed.connect(self.on_servo_speed_changed)
            servo_widget.accel_changed.connect(self.on_servo_accel_changed)
            servo_widget.torque_changed.connect(self.on_servo_torque_changed)
            servo_widget.torque_toggled.connect(self.on_servo_torque_toggled)
            
            row = (i - 1) // 4
            col = (i - 1) % 4
            scroll_layout.addWidget(servo_widget, row, col)
            
            self.servo_widgets[i] = servo_widget
        
        layout.addWidget(scroll)
        tab.setLayout(layout)
        self.tabs.addTab(tab, T.get('servo_id'))
        
    # 在create_recording_tab方法中修改录制频率选择
    def create_recording_tab(self):
        """Create recording tab / 创建录制标签页"""
        tab = QWidget()
        layout = QVBoxLayout()
        
        # Recording controls / 录制控制
        self.recording_group = QGroupBox(T.get('recording'))
        control_layout = QVBoxLayout()
        
        # Mode selection / 模式选择
        mode_layout = QHBoxLayout()
        mode_layout.addWidget(QLabel(T.get('mode_frame') + " / " + T.get('mode_realtime') + ":"))
        
        self.record_mode_combo = QComboBox()
        self.record_mode_combo.addItems([T.get('mode_realtime'), T.get('mode_frame')])
        mode_layout.addWidget(self.record_mode_combo)
        
        mode_layout.addStretch()
        control_layout.addLayout(mode_layout)
        
        # Recording frequency selection / 录制频率选择
        freq_layout = QHBoxLayout()
        freq_layout.addWidget(QLabel("Freq (Hz) / 频率:"))
        
        self.freq_combo = QComboBox()
        self.freq_combo.addItems(['10', '20', '30', '40'])
        self.freq_combo.setCurrentText('20')
        freq_layout.addWidget(self.freq_combo)
        
        freq_layout.addStretch()
        control_layout.addLayout(freq_layout)
        
        # Recording buttons / 录制按钮
        btn_layout = QHBoxLayout()
        
        self.record_btn = QPushButton(T.get('record'))
        self.record_btn.clicked.connect(self.toggle_recording)
        btn_layout.addWidget(self.record_btn)
        
        self.add_frame_btn = QPushButton(T.get('add_frame'))
        self.add_frame_btn.clicked.connect(self.add_recording_frame)
        self.add_frame_btn.setEnabled(False)
        btn_layout.addWidget(self.add_frame_btn)
        
        # 改为"完成并保存录制"
        self.save_record_btn = QPushButton("完成并保存录制 / Finish & Save")
        self.save_record_btn.clicked.connect(self.finish_and_save_recording)
        btn_layout.addWidget(self.save_record_btn)
        
        self.load_record_btn = QPushButton(T.get('load_recording'))
        self.load_record_btn.clicked.connect(self.load_recording)
        btn_layout.addWidget(self.load_record_btn)
        
        control_layout.addLayout(btn_layout)
        self.recording_group.setLayout(control_layout)
        layout.addWidget(self.recording_group)
        
        # Playback controls / 播放控制
        self.playback_group = QGroupBox(T.get('play'))
        playback_layout = QVBoxLayout()
        
        # Playback speed / 播放速度
        speed_layout = QHBoxLayout()
        speed_layout.addWidget(QLabel(T.get('playback_speed') + ":"))
        
        self.playback_speed = QDoubleSpinBox()
        self.playback_speed.setMinimum(0.1)
        self.playback_speed.setMaximum(5.0)
        self.playback_speed.setSingleStep(0.1)
        self.playback_speed.setValue(1.0)
        self.playback_speed.wheelEvent = lambda event: None  # 禁用滚轮
        speed_layout.addWidget(self.playback_speed)
        
        speed_layout.addStretch()
        playback_layout.addLayout(speed_layout)
        
        # Repeat count / 重复次数
        repeat_layout = QHBoxLayout()
        repeat_layout.addWidget(QLabel("重复次数 / Repeat Count:"))
        
        self.repeat_count_spinbox = QSpinBox()
        self.repeat_count_spinbox.setMinimum(1)
        self.repeat_count_spinbox.setMaximum(999)
        self.repeat_count_spinbox.setValue(1)
        self.repeat_count_spinbox.wheelEvent = lambda event: None  # 禁用滚轮
        repeat_layout.addWidget(self.repeat_count_spinbox)
        
        repeat_layout.addStretch()
        playback_layout.addLayout(repeat_layout)
        
        # Frame mode specific settings / 帧模式专用设置
        self.frame_settings_group = QGroupBox("帧模式播放设置 / Frame Mode Settings")
        frame_settings_layout = QVBoxLayout()
        
        # Servo speed / 舵机速度
        frame_speed_layout = QHBoxLayout()
        frame_speed_layout.addWidget(QLabel("舵机速度 / Servo Speed:"))
        self.frame_speed_spinbox = QSpinBox()
        self.frame_speed_spinbox.setMinimum(1)
        self.frame_speed_spinbox.setMaximum(1000)
        self.frame_speed_spinbox.setValue(500)
        self.frame_speed_spinbox.wheelEvent = lambda event: None
        frame_speed_layout.addWidget(self.frame_speed_spinbox)
        frame_settings_layout.addLayout(frame_speed_layout)
        
        # Servo acceleration / 舵机加速度
        frame_accel_layout = QHBoxLayout()
        frame_accel_layout.addWidget(QLabel("舵机加速度 / Servo Acceleration:"))
        self.frame_accel_spinbox = QSpinBox()
        self.frame_accel_spinbox.setMinimum(0)
        self.frame_accel_spinbox.setMaximum(255)
        self.frame_accel_spinbox.setValue(50)
        self.frame_accel_spinbox.wheelEvent = lambda event: None
        frame_accel_layout.addWidget(self.frame_accel_spinbox)
        frame_settings_layout.addLayout(frame_accel_layout)
        
        # Servo torque / 舵机扭矩
        frame_torque_layout = QHBoxLayout()
        frame_torque_layout.addWidget(QLabel("舵机扭矩 / Servo Torque:"))
        self.frame_torque_spinbox = QSpinBox()
        self.frame_torque_spinbox.setMinimum(0)
        self.frame_torque_spinbox.setMaximum(1000)
        self.frame_torque_spinbox.setValue(700)
        self.frame_torque_spinbox.wheelEvent = lambda event: None
        frame_torque_layout.addWidget(self.frame_torque_spinbox)
        frame_settings_layout.addLayout(frame_torque_layout)
        
        # Frame interval / 帧间隔
        frame_interval_layout = QHBoxLayout()
        frame_interval_layout.addWidget(QLabel("帧间隔(秒) / Frame Interval(s):"))
        self.frame_interval_spinbox = QDoubleSpinBox()
        self.frame_interval_spinbox.setMinimum(0.1)
        self.frame_interval_spinbox.setMaximum(10.0)
        self.frame_interval_spinbox.setSingleStep(0.1)
        self.frame_interval_spinbox.setValue(1.0)
        self.frame_interval_spinbox.wheelEvent = lambda event: None
        frame_interval_layout.addWidget(self.frame_interval_spinbox)
        frame_settings_layout.addLayout(frame_interval_layout)
        
        self.frame_settings_group.setLayout(frame_settings_layout)
        playback_layout.addWidget(self.frame_settings_group)
        
        # Playback buttons / 播放按钮
        play_btn_layout = QHBoxLayout()
        
        self.play_btn = QPushButton(T.get('play'))
        self.play_btn.clicked.connect(self.toggle_playback)
        play_btn_layout.addWidget(self.play_btn)
        
        play_btn_layout.addStretch()
        playback_layout.addLayout(play_btn_layout)
        
        self.playback_group.setLayout(playback_layout)
        layout.addWidget(self.playback_group)
        
        layout.addStretch()
        tab.setLayout(layout)
        self.tabs.addTab(tab, T.get('recording'))

    # 添加新的方法
    @pyqtSlot()
    def finish_and_save_recording(self):
        """完成并保存录制"""
        if self.recorder and self.recorder.recording:
            # 先停止录制
            frame_count = self.recorder.stop_recording()
            self.record_btn.setText(T.get('record'))
            self.add_frame_btn.setEnabled(False)
            self.log(f"Recording finished with {frame_count} frames / 录制完成，共{frame_count}帧")
        
        # 然后保存
        if self.recorder and self.recorder.frames:
            filename, _ = QFileDialog.getSaveFileName(
                self, "完成并保存录制 / Finish & Save Recording", "./recordings",
                "JSON Files (*.json)"
            )
            
            if filename:
                filepath = self.recorder.save_recording(filename)
                self.log(f"Recording saved to {filepath} / 录制已保存到 {filepath}")
        else:
            QMessageBox.warning(self, T.get('warning'),
                            "No recording to save / 没有录制可保存")

    @pyqtSlot()
    def toggle_recording(self):
        """Toggle recording / 切换录制"""
        if not self.recorder:
            return
        
        if not self.recorder.recording:
            # Start recording / 开始录制
            mode = 'realtime' if self.record_mode_combo.currentIndex() == 0 else 'frame'
            self.recorder.freq = int(self.freq_combo.currentText())  # 使用选择的频率
            self.recorder.start_recording(mode)
            
            self.record_btn.setText(T.get('stop_record'))
            self.log(f"Recording started ({mode}) at {self.recorder.freq}Hz / 录制开始 ({mode})，频率{self.recorder.freq}Hz")
            
            if mode == 'frame':
                self.add_frame_btn.setEnabled(True)
        else:
            # Stop recording / 停止录制
            frame_count = self.recorder.stop_recording()
            
            self.record_btn.setText(T.get('record'))
            self.add_frame_btn.setEnabled(False)
            self.log(f"Recording stopped, {frame_count} frames / 录制停止，{frame_count}帧")

    @pyqtSlot()
    def toggle_playback(self):
        """Toggle playback / 切换播放"""
        if not self.recorder:
            return
        
        if not self.recorder.playing:
            # Start playback / 开始播放
            if not self.recorder.frames:
                QMessageBox.warning(self, T.get('warning'),
                                "No recording to play / 没有录制可播放")
                return
            
            speed = self.playback_speed.value()
            repeat_count = self.repeat_count_spinbox.value()
            
            # 如果是帧模式，设置播放参数
            if hasattr(self.recorder, 'mode') and self.recorder.mode == 'frame':
                frame_speed = self.frame_speed_spinbox.value()
                frame_accel = self.frame_accel_spinbox.value()
                frame_torque = self.frame_torque_spinbox.value()
                frame_interval = self.frame_interval_spinbox.value()
                
                self.recorder.set_frame_playback_settings(
                    frame_speed, frame_accel, frame_torque, frame_interval
                )
            
            self.recorder.start_playback(speed, repeat_count)
            
            self.play_btn.setText(T.get('stop_play'))
            self.log(f"Playback started at {speed}x speed, {repeat_count} repeats / 播放开始，速度{speed}x，重复{repeat_count}次")
        else:
            # Stop playback / 停止播放
            self.recorder.stop_playback()
            
            self.play_btn.setText(T.get('play'))
            self.log("Playback stopped / 播放停止")
        
    def create_gesture_tab(self):
        """Create gesture recognition tab / 创建手势识别标签页"""
        tab = QWidget()
        layout = QVBoxLayout()
        
        # Gesture control / 手势控制
        self.gesture_control_group = QGroupBox(T.get('gesture'))
        control_layout = QVBoxLayout()
        
        # Enable checkbox / 启用复选框
        self.gesture_enable_cb = QCheckBox(T.get('gesture_enable'))
        self.gesture_enable_cb.stateChanged.connect(self.toggle_gesture_recognition)
        control_layout.addWidget(self.gesture_enable_cb)
        
        # Sensitivity slider / 灵敏度滑块
        sens_layout = QHBoxLayout()
        sens_layout.addWidget(QLabel(T.get('sensitivity') + ":"))
        
        self.sensitivity_slider = QSlider(Qt.Horizontal)
        self.sensitivity_slider.setMinimum(1)
        self.sensitivity_slider.setMaximum(10)
        self.sensitivity_slider.setValue(5)
        self.sensitivity_slider.valueChanged.connect(self.on_sensitivity_changed)
        sens_layout.addWidget(self.sensitivity_slider)
        
        self.sensitivity_label = QLabel("5")
        sens_layout.addWidget(self.sensitivity_label)
        
        control_layout.addLayout(sens_layout)
        
        # Status label / 状态标签
        self.gesture_status_label = QLabel(T.get('status') + ": " + T.get('disconnected'))
        control_layout.addWidget(self.gesture_status_label)
        
        self.gesture_control_group.setLayout(control_layout)
        layout.addWidget(self.gesture_control_group)
        
        # Hand preview area / 手部预览区域
        preview_group = QGroupBox("Hand Preview / 手部预览")
        preview_layout = QVBoxLayout()
        
        self.hand_preview_label = QLabel("No camera feed / 无摄像头画面")
        self.hand_preview_label.setMinimumHeight(400)
        self.hand_preview_label.setAlignment(Qt.AlignCenter)
        self.hand_preview_label.setStyleSheet("border: 1px solid gray; background-color: #f0f0f0;")
        preview_layout.addWidget(self.hand_preview_label)
        
        preview_group.setLayout(preview_layout)
        layout.addWidget(preview_group)
        
        layout.addStretch()
        tab.setLayout(layout)
        self.tabs.addTab(tab, T.get('gesture'))
        
    def create_log_tab(self):
        """Create log tab / 创建日志标签页"""
        tab = QWidget()
        layout = QVBoxLayout()
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Courier New", 9))
        layout.addWidget(self.log_text)
        
        # Clear button / 清除按钮
        clear_btn = QPushButton("Clear Log / 清除日志")
        clear_btn.clicked.connect(self.log_text.clear)
        layout.addWidget(clear_btn)
        
        tab.setLayout(layout)
        self.tabs.addTab(tab, T.get('log'))
        
    def log(self, message: str):
        """
        Add message to log / 添加消息到日志
        
        Args:
            message: Log message / 日志消息
        """
        from datetime import datetime
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        self.log_text.append(f"[{timestamp}] {message}")
        
        # Auto scroll to bottom / 自动滚动到底部
        scrollbar = self.log_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
        
    def refresh_ports(self):
        """Refresh available serial ports / 刷新可用串口"""
        import serial.tools.list_ports
        
        self.port_combo.clear()
        ports = serial.tools.list_ports.comports()
        
        for port in ports:
            self.port_combo.addItem(f"{port.device} - {port.description}")
        
        if not ports:
            self.port_combo.addItem("No ports found / 未找到端口")
            
    @pyqtSlot()
    def toggle_connection(self):
        """Toggle serial connection / 切换串口连接"""
        if self.serial_manager is None or not self.serial_manager.is_connected():
            # Connect / 连接
            port_text = self.port_combo.currentText()
            if "No ports" in port_text:
                QMessageBox.warning(self, T.get('warning'), 
                                  "No serial ports available / 没有可用串口")
                return
            
            port = port_text.split(" - ")[0]
            baudrate = int(self.baudrate_combo.currentText())
            
            try:
                self.serial_manager = SerialManager(baudrate, timeout=1.0)
                self.serial_manager.connect(port)
                
                # Create servo manager / 创建舵机管理器
                self.servo_manager = ServoManager(self.serial_manager, self.config)
                
                # Ping all servos / 检查所有舵机
                self.log("Pinging all servos... / 检查所有舵机...")
                results = self.servo_manager.ping_all()
                
                online_count = sum(1 for v in results.values() if v)
                self.log(f"Found {online_count}/17 servos online / 找到{online_count}/17个舵机在线")
                
                # Update servo widgets / 更新舵机组件
                for servo_id, connected in results.items():
                    if servo_id in self.servo_widgets:
                        self.servo_widgets[servo_id].set_connected(connected)
                
                # Create recorder / 创建录制器
                self.recorder = Recorder(self.servo_manager, self.config)
                
                # Update UI / 更新UI
                self.connect_btn.setText(T.get('disconnect'))
                self.statusBar().showMessage(T.get('connected') + f" - {port}")
                self.log(f"Connected to {port} / 已连接到{port}")
                
                # Start feedback update timer / 启动反馈更新定时器
                self.update_timer.start(50)  # 20Hz

                self.check_calibration_on_startup()
                
            except Exception as e:
                QMessageBox.critical(self, T.get('error'), 
                                   f"Connection failed / 连接失败: {str(e)}")
                self.log(f"Connection error / 连接错误: {str(e)}")
                
        else:
            # Disconnect / 断开
            self.update_timer.stop()
            
            if self.gesture_worker:
                self.gesture_worker.stop()
                self.gesture_worker = None
            
            if self.recorder:
                if self.recorder.recording:
                    self.recorder.stop_recording()
                if self.recorder.playing:
                    self.recorder.stop_playback()
            
            if self.servo_manager:
                self.servo_manager.torque_off_all()
            
            if self.serial_manager:
                self.serial_manager.disconnect()
                self.serial_manager = None
            
            # Update UI / 更新UI
            for widget in self.servo_widgets.values():
                widget.set_connected(False)
            
            self.connect_btn.setText(T.get('connect'))
            self.statusBar().showMessage(T.get('disconnected'))
            self.log("Disconnected / 已断开连接")
            
    @pyqtSlot()
    def torque_on_all(self):
        """
        Enable torque for all servos / 所有舵机上电
        上电时恢复默认参数 / Restore default parameters on power on
        """
        if not self.servo_manager:
            return
        
        self.log("Enabling torque for all servos / 所有舵机上电...")
        
        # 先恢复所有舵机的默认扭矩值
        # First restore default torque values for all servos
        for servo_id, widget in self.servo_widgets.items():
            if widget.connected:
                widget.torque_spinbox.setValue(500)  # 恢复默认扭矩 / Restore default torque
        
        results = self.servo_manager.torque_on_all()
        
        success_count = sum(1 for v in results.values() if v)
        self.log(f"Torque enabled for {success_count} servos / {success_count}个舵机已上电")
        
        for servo_id, success in results.items():
            if success and servo_id in self.servo_widgets:
                self.servo_widgets[servo_id].torque_button.setChecked(True)
                self.servo_widgets[servo_id].update_torque_button_text(True)
                # 启用位置控制 / Enable position controls
                self.servo_widgets[servo_id].position_slider.setEnabled(True)
                self.servo_widgets[servo_id].position_spinbox.setEnabled(True)

    @pyqtSlot()
    def torque_off_all(self):
        """
        Disable torque for all servos / 所有舵机下电
        下电时禁用位置控制 / Disable position controls when powered off
        """
        if not self.servo_manager:
            return
        
        self.log("Disabling torque for all servos / 所有舵机下电...")
        results = self.servo_manager.torque_off_all()
        
        success_count = sum(1 for v in results.values() if v)
        self.log(f"Torque disabled for {success_count} servos / {success_count}个舵机已下电")
        
        for servo_id, success in results.items():
            if success and servo_id in self.servo_widgets:
                widget = self.servo_widgets[servo_id]
                widget.torque_button.setChecked(False)
                widget.update_torque_button_text(False)
                # 禁用位置控制 / Disable position controls
                widget.position_slider.setEnabled(False)
                widget.position_spinbox.setEnabled(False)
                
    @pyqtSlot()
    def calibrate_limits(self):
        """Calibrate servo limits / 校准舵机极限"""
        if not self.servo_manager:
            QMessageBox.warning(self, T.get('warning'), "请先连接舵机")
            return
        
        if not self.calibrating:
            # 开始校准
            if not self.servo_manager.has_calibration_data():
                # 首次校准
                reply = QMessageBox.question(self, "首次校准", 
                                        "未找到校准数据，开始首次校准？\n"
                                        "校准期间请手动移动所有舵机到完整范围。",
                                        QMessageBox.Yes | QMessageBox.No)
                if reply != QMessageBox.Yes:
                    return
            else:
                # 重新校准
                reply = QMessageBox.question(self, "重新校准", 
                                        "将覆盖现有校准数据，确定继续？\n"
                                        "校准期间请手动移动所有舵机到完整范围。",
                                        QMessageBox.Yes | QMessageBox.No)
                if reply != QMessageBox.Yes:
                    return
            
            # 开始校准
            if self.servo_manager.start_calibration():
                self.calibrating = True
                self.calibrate_btn.setText("完成校准")
                self.statusBar().showMessage("校准中... 请移动舵机")
                # 禁用其他控制
                self.disable_servo_controls()
                self.log("校准开始 - 请手动移动所有舵机到完整范围")
        else:
            # 停止校准
            if self.servo_manager.stop_calibration():
                self.calibrating = False
                self.calibrate_btn.setText(T.get('calibrate'))
                self.statusBar().showMessage("校准完成")
                # 更新UI限制
                self.update_servo_limits()
                # 重新启用控制
                self.enable_servo_controls()
                self.log("校准完成并保存")

    def disable_servo_controls(self):
        """禁用舵机控制"""
        for widget in self.servo_widgets.values():
            widget.set_enabled(False)

    def enable_servo_controls(self):
        """启用舵机控制"""
        for servo_id, widget in self.servo_widgets.items():
            # 只启用已连接的舵机
            if self.servo_manager:
                servo = self.servo_manager.get_servo(servo_id)
                widget.set_enabled(servo and servo.connected)

    def update_servo_limits(self):
        """更新UI中的舵机限制"""
        if not self.servo_manager:
            return
        
        for servo_id, widget in self.servo_widgets.items():
            limits = self.servo_manager.get_servo_limits(servo_id)
            if limits:
                widget.update_limits(limits['min'], limits['max'])

    def check_calibration_on_startup(self):
        """启动时检查校准文件"""
        if not self.servo_manager:
            return
        
        if not self.servo_manager.has_calibration_data():
            reply = QMessageBox.question(self, "需要校准", 
                                    "未找到校准数据，现在校准吗？\n"
                                    "不校准将无法使用舵机功能。",
                                    QMessageBox.Yes | QMessageBox.No)
            if reply == QMessageBox.Yes:
                self.calibrate_limits()
            else:
                self.disable_servo_controls()
        else:
            self.update_servo_limits()
            self.enable_servo_controls()

    # 添加扭矩值变化处理
    @pyqtSlot(int, int)
    def on_servo_torque_changed(self, servo_id: int, torque_value: int):
        """Handle servo torque value change"""
        if not self.servo_manager:
            return
        
        servo = self.servo_manager.get_servo(servo_id)
        if servo and servo.connected:
            servo.torque_value = torque_value
            
    @pyqtSlot(int, int)
    def on_servo_position_changed(self, servo_id: int, position: int):
        """Handle servo position change / 处理舵机位置变化"""
        if not self.servo_manager:
            return
        
        servo = self.servo_manager.get_servo(servo_id)
        if servo and servo.connected:
            servo.set_goal_position(position)
            
    @pyqtSlot(int, int)
    def on_servo_speed_changed(self, servo_id: int, speed: int):
        """Handle servo speed change / 处理舵机速度变化"""
        if not self.servo_manager:
            return
        
        servo = self.servo_manager.get_servo(servo_id)
        if servo and servo.connected:
            servo.set_goal_speed(speed)
            
    @pyqtSlot(int, int)
    def on_servo_accel_changed(self, servo_id: int, accel: int):
        """Handle servo acceleration change / 处理舵机加速度变化"""
        if not self.servo_manager:
            return
        
        servo = self.servo_manager.get_servo(servo_id)
        if servo and servo.connected:
            servo.set_goal_acceleration(accel)
            
    @pyqtSlot(int, bool)
    def on_servo_torque_toggled(self, servo_id: int, enabled: bool):
        """
        Handle servo torque toggle / 处理舵机扭矩切换
        上电时恢复默认扭矩值 / Restore default torque when powering on
        """
        if not self.servo_manager:
            return
        
        servo = self.servo_manager.get_servo(servo_id)
        if servo and servo.connected:
            if enabled:
                # 上电：恢复默认扭矩值 / Power on: restore default torque
                widget = self.servo_widgets.get(servo_id)
                if widget:
                    widget.torque_spinbox.setValue(500)  # 恢复默认扭矩 / Restore default torque
                servo.torque_on()
            else:
                # 下电：扭矩设为0 / Power off: set torque to 0
                servo.torque_off()
                
    @pyqtSlot()
    def update_servo_feedback(self):
        """Update servo feedback display / 更新舵机反馈显示"""
        if not self.servo_manager:
            return
        
        try:
            positions = self.servo_manager.read_all_positions()
            
            for servo_id, position in positions.items():
                if position is not None and servo_id in self.servo_widgets:
                    self.servo_widgets[servo_id].update_position(position)
                    
        except Exception as e:
            # Don't log every error to avoid spam / 避免日志刷屏
            pass
            
    @pyqtSlot()
    def toggle_recording(self):
        """Toggle recording / 切换录制"""
        if not self.recorder:
            return
        
        if not self.recorder.recording:
            # Start recording / 开始录制
            mode = 'realtime' if self.record_mode_combo.currentIndex() == 0 else 'frame'
            # 修改：使用 freq_combo 而不是 freq_spinbox
            self.recorder.freq = int(self.freq_combo.currentText())  # 使用选择的频率
            self.recorder.start_recording(mode)
            
            self.record_btn.setText(T.get('stop_record'))
            self.log(f"Recording started ({mode}) at {self.recorder.freq}Hz / 录制开始 ({mode})，频率{self.recorder.freq}Hz")
            
            if mode == 'frame':
                self.add_frame_btn.setEnabled(True)
        else:
            # Stop recording / 停止录制
            frame_count = self.recorder.stop_recording()
            
            self.record_btn.setText(T.get('record'))
            self.add_frame_btn.setEnabled(False)
            self.log(f"Recording stopped, {frame_count} frames / 录制停止，{frame_count}帧")

    @pyqtSlot()
    def add_recording_frame(self):
        """Add frame to recording / 添加帧到录制"""
        if not self.recorder or not self.recorder.recording:
            return
        
        self.recorder.add_frame()
        
    @pyqtSlot()
    def save_recording(self):
        """Save recording to file / 保存录制到文件"""
        if not self.recorder or not self.recorder.frames:
            QMessageBox.warning(self, T.get('warning'),
                              "No recording to save / 没有录制可保存")
            return
        
        filename, _ = QFileDialog.getSaveFileName(
            self, T.get('save_recording'), "./recordings",
            "JSON Files (*.json)"
        )
        
        if filename:
            filepath = self.recorder.save_recording(filename)
            self.log(f"Recording saved to {filepath} / 录制已保存到 {filepath}")
            
    @pyqtSlot()
    def load_recording(self):
        """Load recording from file / 从文件加载录制"""
        if not self.recorder:
            return
        
        filename, _ = QFileDialog.getOpenFileName(
            self, T.get('load_recording'), "./recordings",
            "JSON Files (*.json)"
        )
        
        if filename:
            success = self.recorder.load_recording(filename)
            if success:
                self.log(f"Recording loaded from {filename} / 录制已加载")
            else:
                QMessageBox.critical(self, T.get('error'),
                                   "Failed to load recording / 加载录制失败")
                
    @pyqtSlot()
    def toggle_playback(self):
        """Toggle playback / 切换播放"""
        if not self.recorder:
            return
        
        if not self.recorder.playing:
            # Start playback / 开始播放
            if not self.recorder.frames:
                QMessageBox.warning(self, T.get('warning'),
                                  "No recording to play / 没有录制可播放")
                return
            
            speed = self.playback_speed.value()
            self.recorder.start_playback(speed)
            
            self.play_btn.setText(T.get('stop_play'))
            self.log(f"Playback started at {speed}x / 播放开始，速度{speed}x")
        else:
            # Stop playback / 停止播放
            self.recorder.stop_playback()
            
            self.play_btn.setText(T.get('play'))
            self.log("Playback stopped / 播放停止")
            
    @pyqtSlot(int)
    def toggle_gesture_recognition(self, state: int):
        """Toggle gesture recognition / 切换手势识别"""
        if state == Qt.Checked:
            # Start gesture recognition / 启动手势识别
            try:
                # 检查是否已连接舵机（可选）
                if not self.servo_manager:
                    reply = QMessageBox.question(
                        self, 
                        T.get('warning'),
                        "Servo not connected. Start gesture recognition in preview mode?\n"
                        "舵机未连接。以预览模式启动手势识别？",
                        QMessageBox.Yes | QMessageBox.No
                    )
                    if reply == QMessageBox.No:
                        self.gesture_enable_cb.setChecked(False)
                        return
                
                self.gesture_worker = GestureWorker(self.servo_manager, self.config)
                
                # 连接画面更新信号
                self.gesture_worker.frame_ready.connect(self.update_gesture_preview)
                
                self.gesture_worker.start()
                
                self.gesture_status_label.setText(T.get('status') + ": " + T.get('online'))
                self.log("Gesture recognition started / 手势识别已启动")
                
            except Exception as e:
                QMessageBox.critical(self, T.get('error'),
                                f"Failed to start gesture recognition / 启动手势识别失败: {str(e)}")
                self.gesture_enable_cb.setChecked(False)
                self.log(f"Gesture error / 手势错误: {str(e)}")
        else:
            # Stop gesture recognition / 停止手势识别
            if self.gesture_worker:
                self.gesture_worker.stop()
                self.gesture_worker = None
                
                # 清空预览
                self.hand_preview_label.setText("No camera feed / 无摄像头画面")
                
                self.gesture_status_label.setText(T.get('status') + ": " + T.get('offline'))
                self.log("Gesture recognition stopped / 手势识别已停止")

    @pyqtSlot(object)
    def update_gesture_preview(self, frame):
        """
        Update gesture preview image / 更新手势预览图像
        
        Args:
            frame: OpenCV frame (numpy array) / OpenCV帧（numpy数组）
        """
        from PyQt5.QtGui import QImage, QPixmap
        import cv2
        
        # 转换 OpenCV BGR 到 RGB
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_frame.shape
        bytes_per_line = ch * w
        
        # 创建 QImage
        qt_image = QImage(rgb_frame.data, w, h, bytes_per_line, QImage.Format_RGB888)
        
        # 缩放以适应显示区域
        scaled_pixmap = QPixmap.fromImage(qt_image).scaled(
            self.hand_preview_label.width(),
            self.hand_preview_label.height(),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )
        
        # 显示
        self.hand_preview_label.setPixmap(scaled_pixmap)

    @pyqtSlot(int)
    def on_sensitivity_changed(self, value: int):
        """Handle sensitivity slider change / 处理灵敏度滑块变化"""
        self.sensitivity_label.setText(str(value))
        
        if self.gesture_worker:
            self.gesture_worker.set_sensitivity(value / 10.0)
    
    @pyqtSlot(str)
    def on_language_changed(self, text: str):
        """
        Handle language change / 处理语言切换
        
        Args:
            text: Selected language text / 选中的语言文本
        """
        # Map display text to language code / 映射显示文本到语言代码
        if text == T.get('english', 'cn'):  # Check Chinese version
            language_code = 'en'
        elif text == T.get('english', 'en'):  # Check English version
            language_code = 'en'
        else:
            language_code = 'cn'
        
        # Skip if already current language / 如果已是当前语言则跳过
        if T.get_current_language() == language_code:
            return
        
        # Change language / 切换语言
        self.change_language(language_code)

    def change_language(self, language: str):
        """
        Change UI language / 切换UI语言
        
        Args:
            language: Language code ('cn' or 'en') / 语言代码
        """
        # Save to config / 保存到配置
        if 'ui' not in self.config:
            self.config['ui'] = {}
        self.config['ui']['language'] = language
        self.save_config()
        
        # Update translator / 更新翻译器
        T.set_language(language)
        
        # Re-translate all UI elements / 重新翻译所有UI元素
        self.retranslate_ui()
    
    def save_config(self):
        """Save configuration to file / 保存配置到文件"""
        import yaml
        try:
            with open('./config/app_config.yaml', 'w', encoding='utf-8') as f:
                yaml.dump(self.config, f, allow_unicode=True)
        except Exception as e:
            self.log(f"Failed to save config / 保存配置失败: {str(e)}")
            