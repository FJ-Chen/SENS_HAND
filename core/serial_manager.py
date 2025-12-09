#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Serial Port Manager using local SCServo SDK
使用本地SCServo SDK的串口管理器
"""

import sys
import os
# 添加本地scservo_sdk路径
current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sdk_path = os.path.join(current_dir, 'scservo_sdk')
if sdk_path not in sys.path:
    sys.path.append(sdk_path)

try:
    from scservo_sdk import *
except ImportError as e:
    print(f"Failed to import scservo_sdk: {e}")
    print(f"SDK path: {sdk_path}")
    raise


class SerialManager:
    """
    Serial port management using SCServo SDK
    使用SCServo SDK的串口管理
    """
    
    def __init__(self, baudrate: int = 1000000, timeout: float = 1.0):
        self.baudrate = baudrate
        self.timeout = timeout
        self.port_handler = None
        self.packet_handler = None
        self.connected = False
        self.port_name = None
        
    def connect(self, port_name: str) -> bool:
        """连接到串口"""
        try:
            # 如果已连接，先断开
            if self.connected:
                self.disconnect()
                
            # 初始化端口处理器
            self.port_handler = PortHandler(port_name)
            
            # 打开端口
            if not self.port_handler.openPort():
                print(f"Failed to open port {port_name}")
                return False
            
            # 设置波特率
            if not self.port_handler.setBaudRate(self.baudrate):
                print(f"Failed to set baudrate {self.baudrate}")
                self.port_handler.closePort()
                return False
            
            # 初始化数据包处理器
            self.packet_handler = hls(self.port_handler)
            
            self.connected = True
            self.port_name = port_name
            print(f"Connected to {port_name} at {self.baudrate} baud")
            return True
            
        except Exception as e:
            print(f"Connection error: {e}")
            self.connected = False
            return False
    
    def disconnect(self):
        """断开连接"""
        if self.port_handler:
            try:
                self.port_handler.closePort()
                print(f"Disconnected from {self.port_name}")
            except Exception as e:
                print(f"Error closing port: {e}")
        
        self.connected = False
        self.port_handler = None
        self.packet_handler = None
        self.port_name = None
        
    def is_connected(self) -> bool:
        """检查连接状态"""
        return self.connected and self.port_handler is not None
    
    @staticmethod
    def list_available_ports():
        """列出可用端口"""
        import serial.tools.list_ports
        ports = serial.tools.list_ports.comports()
        return [port.device for port in ports]
    