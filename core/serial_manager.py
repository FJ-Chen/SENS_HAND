#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Serial Port Manager / 串口管理器
Handles COM port detection, connection, and data transfer
处理COM端口检测、连接和数据传输
"""

import serial
import serial.tools.list_ports
from typing import List, Optional
import time
import threading


class SerialManager:
    """
    Serial port management with auto-detection and reconnection
    串口管理（支持自动检测和重连）
    """
    
    def __init__(self, baudrate: int = 1000000, timeout: float = 1.0):
        """
        Initialize serial manager / 初始化串口管理器
        
        Args:
            baudrate: Communication baud rate / 通信波特率
            timeout: Read timeout in seconds / 读取超时（秒）
        """
        self.baudrate = baudrate
        self.timeout = timeout
        self.port: Optional[serial.Serial] = None
        self.port_name: Optional[str] = None
        self.connected = False
        self.lock = threading.Lock()
        
    @staticmethod
    def list_available_ports() -> List[str]:
        """
        List all available COM ports / 列出所有可用COM端口
        
        Returns:
            List of port names / 端口名称列表
        """
        ports = serial.tools.list_ports.comports()
        return [port.device for port in ports]
    
    def connect(self, port_name: str) -> bool:
        """
        Connect to specified COM port / 连接到指定COM端口
        
        Args:
            port_name: Port name (e.g., 'COM3', '/dev/ttyUSB0') / 端口名
            
        Returns:
            Connection success status / 连接成功状态
        """
        with self.lock:
            try:
                if self.connected:
                    self.disconnect()
                
                self.port = serial.Serial(
                    port=port_name,
                    baudrate=self.baudrate,
                    bytesize=serial.EIGHTBITS,
                    parity=serial.PARITY_NONE,
                    stopbits=serial.STOPBITS_ONE,
                    timeout=self.timeout
                )
                
                self.port_name = port_name
                self.connected = True
                self.clear_buffer()
                
                print(f"Connected to {port_name} at {self.baudrate} baud")
                return True
                
            except serial.SerialException as e:
                print(f"Failed to connect to {port_name}: {e}")
                self.connected = False
                return False
    
    def disconnect(self):
        """Close serial connection / 关闭串口连接"""
        with self.lock:
            if self.port and self.port.is_open:
                try:
                    self.port.close()
                    print(f"Disconnected from {self.port_name}")
                except Exception as e:
                    print(f"Error closing port: {e}")
            
            self.connected = False
            self.port = None
            self.port_name = None
    
    def write(self, data: bytes) -> bool:
        """
        Write data to serial port / 向串口写入数据
        
        Args:
            data: Bytes to write / 要写入的字节
            
        Returns:
            Write success status / 写入成功状态
        """
        with self.lock:
            if not self.connected or not self.port:
                return False
            
            try:
                written = self.port.write(data)
                self.port.flush()
                return written == len(data)
            except serial.SerialException as e:
                print(f"Write error: {e}")
                self.connected = False
                return False
    
    def read(self, length: int) -> Optional[bytes]:
        """
        Read data from serial port / 从串口读取数据
        
        Args:
            length: Number of bytes to read / 要读取的字节数
            
        Returns:
            Read bytes or None on failure / 读取的字节或失败时None
        """
        with self.lock:
            if not self.connected or not self.port:
                return None
            
            try:
                data = self.port.read(length)
                return data if len(data) > 0 else None
            except serial.SerialException as e:
                print(f"Read error: {e}")
                self.connected = False
                return None
    
    def clear_buffer(self):
        """Clear input and output buffers / 清空输入输出缓冲区"""
        with self.lock:
            if self.connected and self.port:
                try:
                    self.port.reset_input_buffer()
                    self.port.reset_output_buffer()
                except serial.SerialException:
                    pass
    
    def is_connected(self) -> bool:
        """
        Check connection status / 检查连接状态
        
        Returns:
            Connection status / 连接状态
        """
        return self.connected and self.port is not None and self.port.is_open