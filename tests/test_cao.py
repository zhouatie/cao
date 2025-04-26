#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest
import os
import sys
from unittest.mock import patch, MagicMock

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.cao import get_terminal_size, parse_args, call_ai_api

class TestCao(unittest.TestCase):
    """测试 cao 工具的功能"""
    
    def test_get_terminal_size(self):
        """测试获取终端大小"""
        width, height = get_terminal_size()
        # 检查是否返回了正整数
        self.assertIsInstance(width, int)
        self.assertIsInstance(height, int)
        self.assertGreater(width, 0)
        self.assertGreater(height, 0)
    
    def test_parse_args(self):
        """测试命令行参数解析"""
        with patch('sys.argv', ['cao', 'ls', '-l']):
            args = parse_args()
            self.assertEqual(args.command, ['ls', '-l'])
            self.assertEqual(args.model, 'deepseek')
            self.assertFalse(args.last)
            self.assertFalse(args.debug)
        
        with patch('sys.argv', ['cao', '-m', 'openai', '--last']):
            args = parse_args()
            self.assertEqual(args.model, 'openai')
            self.assertTrue(args.last)
            self.assertEqual(args.command, [])
    
    @patch('requests.post')
    def test_call_ai_api(self, mock_post):
        """测试调用 AI API"""
        # 模拟 API 响应
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "测试 AI 响应"}}]
        }
        mock_post.return_value = mock_response
        
        # 设置环境变量
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test_key', 'DEEPSEEK_API_KEY': 'test_deepseek_key'}):
            model_config = {
                "api_base": "https://api.deepseek.com/v1",
                "model": "deepseek-chat"
            }
            error_info = {
                "command": "test command",
                "error": "test error",
                "returncode": 1
            }
            
            result = call_ai_api(model_config, error_info)
            
            # 验证 API 调用
            mock_post.assert_called_once()
            self.assertIn("test_key", mock_post.call_args[1]['headers']['Authorization'])
            
            # 验证结果
            self.assertIsInstance(result, str)

if __name__ == '__main__':
    unittest.main()
