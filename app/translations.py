#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Bilingual (Chinese/English) text resources
双语（中英文）文本资源
"""

class Translations:
    """Text translations for UI / UI文本翻译"""
    
    # Supported languages / 支持的语言
    LANG_CN = 'cn'
    LANG_EN = 'en'
    
    _current_lang = LANG_CN
    
    # Translation dictionary / 翻译字典
    _texts = {
        # Window titles / 窗口标题
        'main_window': {
            'cn': 'SENS HAND 手部控制器',
            'en': 'SENS HAND Controller'
        },
        
        # Connection / 连接
        'connect': {'cn': '连接', 'en': 'Connect'},
        'disconnect': {'cn': '断开', 'en': 'Disconnect'},
        'refresh_ports': {'cn': '刷新端口', 'en': 'Refresh Ports'},
        'connected': {'cn': '已连接', 'en': 'Connected'},
        'disconnected': {'cn': '已断开', 'en': 'Disconnected'},
        'port': {'cn': '端口', 'en': 'Port'},
        'baudrate': {'cn': '波特率', 'en': 'Baudrate'},
        
        # Servo control / 舵机控制
        'servo_id': {'cn': '舵机ID', 'en': 'Servo ID'},
        'position': {'cn': '位置', 'en': 'Position'},
        'speed': {'cn': '速度', 'en': 'Speed'},
        'acceleration': {'cn': '加速度', 'en': 'Acceleration'},
        'torque': {'cn': '扭矩', 'en': 'Torque'},
        'torque_on': {'cn': '上电', 'en': 'Torque On'},
        'torque_off': {'cn': '下电', 'en': 'Torque Off'},
        'all_on': {'cn': '全部上电', 'en': 'All On'},
        'all_off': {'cn': '全部下电', 'en': 'All Off'},
        
        # Calibration / 校准
        'calibrate': {'cn': '校准极限', 'en': 'Calibrate Limits'},
        'start_calibration': {'cn': '开始校准', 'en': 'Start Calibration'},
        'stop_calibration': {'cn': '完成校准', 'en': 'Finish Calibration'},
        'calibration_help': {
            'cn': '校准过程中请移动舵机到完整范围',
            'en': 'Move servos through full range during calibration'
        },
        
        # Recording / 录制
        'recording': {'cn': '录制', 'en': 'Recording'},
        'record': {'cn': '录制', 'en': 'Record'},
        'stop_record': {'cn': '停止录制', 'en': 'Stop Recording'},
        'add_frame': {'cn': '添加帧', 'en': 'Add Frame'},
        'save_recording': {'cn': '保存录制', 'en': 'Save Recording'},
        'load_recording': {'cn': '加载录制', 'en': 'Load Recording'},
        'play': {'cn': '播放', 'en': 'Play'},
        'stop_play': {'cn': '停止播放', 'en': 'Stop Playback'},
        'mode_frame': {'cn': '帧式', 'en': 'Frame-based'},
        'mode_realtime': {'cn': '实时', 'en': 'Real-time'},
        'playback_speed': {'cn': '播放速度', 'en': 'Playback Speed'},
        
        # Gesture / 手势
        'gesture': {'cn': '手势识别', 'en': 'Gesture Recognition'},
        'gesture_enable': {'cn': '启用手势', 'en': 'Enable Gesture'},
        'gesture_disable': {'cn': '停用手势', 'en': 'Disable Gesture'},
        'sensitivity': {'cn': '灵敏度', 'en': 'Sensitivity'},
        
        # Language / 语言
        'language': {'cn': '语言', 'en': 'Language'},
        'chinese': {'cn': '中文', 'en': 'Chinese'},
        'english': {'cn': 'English', 'en': 'English'},
        
        # Status / 状态
        'status': {'cn': '状态', 'en': 'Status'},
        'online': {'cn': '在线', 'en': 'Online'},
        'offline': {'cn': '离线', 'en': 'Offline'},
        'log': {'cn': '日志', 'en': 'Log'},
        
        # File operations / 文件操作
        'save': {'cn': '保存', 'en': 'Save'},
        'load': {'cn': '加载', 'en': 'Load'},
        'export': {'cn': '导出', 'en': 'Export'},
        'import': {'cn': '导入', 'en': 'Import'},
        
        # Messages / 消息
        'success': {'cn': '成功', 'en': 'Success'},
        'failed': {'cn': '失败', 'en': 'Failed'},
        'error': {'cn': '错误', 'en': 'Error'},
        'warning': {'cn': '警告', 'en': 'Warning'},
        'info': {'cn': '信息', 'en': 'Info'},
        
        # Units / 单位
        'degrees': {'cn': '度', 'en': 'deg'},
        'rpm': {'cn': '转/分', 'en': 'RPM'},
        'deg_s2': {'cn': '度/秒²', 'en': 'deg/s²'},
        'ma': {'cn': '毫安', 'en': 'mA'},
        'volt': {'cn': '伏', 'en': 'V'},
        'celsius': {'cn': '℃', 'en': '°C'},
    }
    
    @classmethod
    def set_language(cls, lang: str):
        """
        Set current language / 设置当前语言
        
        Args:
            lang: Language code ('cn' or 'en') / 语言代码
        """
        if lang in [cls.LANG_CN, cls.LANG_EN]:
            cls._current_lang = lang
    
    @classmethod
    def get(cls, key: str, lang: str | None = None) -> str:
        """
        Get translated text / 获取翻译文本
        
        Args:
            key: Text key / 文本键
            lang: Language code (uses current if None) / 语言代码
            
        Returns:
            Translated text / 翻译文本
        """
        lang = lang or cls._current_lang
        
        if key in cls._texts:
            return cls._texts[key].get(lang, key)
        return key
    
    @classmethod
    def get_current_language(cls) -> str:
        """Get current language / 获取当前语言"""
        return cls._current_lang