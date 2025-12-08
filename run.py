#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Entry Point / 入口点
Main application launcher
主应用启动器
"""

import sys
import yaml
from PyQt5.QtWidgets import QApplication
from app.ui_main import MainWindow


def load_config(config_path: str = './config/servo_config.yaml') -> dict:
    """
    Load configuration from YAML file / 从YAML文件加载配置
    
    Args:
        config_path: Path to config file / 配置文件路径
        
    Returns:
        Configuration dict / 配置字典
    """
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        return config
    except FileNotFoundError:
        print(f"Config file not found: {config_path}")
        print(f"配置文件未找到: {config_path}")
        print("Using default configuration / 使用默认配置")
        return get_default_config()


def get_default_config() -> dict:
    """
    Get default configuration / 获取默认配置
    
    Returns:
        Default config dict / 默认配置字典
    """
    return {
        'serial': {
            'port': 'COM3',
            'baudrate': 1000000,
            'timeout': 0.1
        },
        'servos': {
            i: {
                'min_reg': -32767,
                'max_reg': 32767,
                'offset': 0,
                'scale': 1.0,
                'invert': False
            } for i in range(1, 18)
        },
        'recording': {
            'mode': 'realtime',
            'freq': 20,
            'save_dir': './recordings'
        },
        'gesture': {
            'camera_id': 0,
            'mapping': {
                i: {
                    'min': -32767,
                    'max': 32767,
                    'scale': 1.0,
                    'offset': 0
                } for i in range(1, 18)
            }
        }
    }


def main():
    """Main application entry point / 主应用入口点"""
    # Load configuration / 加载配置
    config = load_config()
    
    # Create Qt application / 创建Qt应用
    app = QApplication(sys.argv)
    app.setStyle('Fusion')  # Modern look / 现代外观
    
    # Create and show main window / 创建并显示主窗口
    window = MainWindow(config)
    window.show()
    
    # Run application / 运行应用
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()