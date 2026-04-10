#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Agent Memory Skill - 状态检查脚本
用于验证配置和数据库连接
"""

import sys
import os

# 添加 skills 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent-memory.scripts.config import get_config, ConfigurationError
from agent-memory.scripts.client import ExperienceClient, MemoryClient, PYMYSQL_AVAILABLE


def check_config():
    """检查配置"""
    print("\n[1] 配置检查")
    print("-" * 40)
    
    config = get_config()
    print(f"  数据库地址: {config.host}")
    print(f"  数据库端口: {config.port}")
    print(f"  数据库名: {config.database}")
    print(f"  用户名: {config.user}")
    print(f"  密码: {'*' * len(config.password) if config.password else '(未设置)'}")
    print(f"  字符集: {config.charset}")
    print(f"  已配置: {'是' if config.is_configured else '否'}")
    
    return config.is_configured


def check_dependencies():
    """检查依赖"""
    print("\n[2] 依赖检查")
    print("-" * 40)
    
    print(f"  PyMySQL: {'已安装' if PYMYSQL_AVAILABLE else '未安装'}")
    
    if not PYMYSQL_AVAILABLE:
        print("\n  请运行以下命令安装：")
        print("    pip install pymysql")
    
    return PYMYSQL_AVAILABLE


def check_database():
    """检查数据库连接"""
    print("\n[3] 数据库连接检查")
    print("-" * 40)
    
    if not PYMYSQL_AVAILABLE:
        print("  [跳过] PyMySQL 未安装")
        return False
    
    config = get_config()
    if not config.is_configured:
        print("  [跳过] 数据库未配置")
        return False
    
    try:
        client = ExperienceClient()
        conn = client._get_connection()
        print(f"  数据库连接: 成功")
        print(f"  服务器版本: {conn.get_server_info()}")
        
        # 检查表是否存在
        with conn.cursor() as cursor:
            cursor.execute("SHOW TABLES")
            tables = [t['Tables_in_agent_memory'] for t in cursor.fetchall()]
            print(f"  现有表: {', '.join(tables) if tables else '(无)'}")
        
        conn.close()
        return True
    except ConfigurationError as e:
        print(f"  [错误] {e}")
        return False
    except Exception as e:
        print(f"  [错误] {e}")
        return False


def check_experiences():
    """检查经验数据"""
    print("\n[4] 经验数据检查")
    print("-" * 40)
    
    if not PYMYSQL_AVAILABLE:
        print("  [跳过] PyMySQL 未安装")
        return
    
    config = get_config()
    if not config.is_configured:
        print("  [跳过] 数据库未配置")
        return
    
    try:
        client = ExperienceClient()
        
        # 统计
        results = client.search_experiences("", limit=100)
        print(f"  云端经验总数: {len(results)}")
        
        if results:
            print(f"\n  最新 3 条经验:")
            for exp in results[:3]:
                print(f"    [{exp['code']}] {exp['title']}")
        
        return results
    except Exception as e:
        print(f"  [错误] {e}")
        return []


def main():
    print("=" * 40)
    print("  Agent Memory Skill 状态检查")
    print("=" * 40)
    
    config_ok = check_config()
    deps_ok = check_dependencies()
    db_ok = check_database()
    
    if deps_ok and config_ok and db_ok:
        check_experiences()
    
    print("\n" + "=" * 40)
    print("  检查完成")
    print("=" * 40)
    
    if not config_ok:
        print("\n[提示] 请设置数据库连接信息：")
        print("  PowerShell:")
        print("    $env:MEMORY_DB_HOST = 'your-host.com'")
        print("    $env:MEMORY_DB_USER = 'your-user'")
        print("    $env:MEMORY_DB_PASSWORD = 'your-password'")
        print()
        print("  或编辑 config.yaml 文件")


if __name__ == "__main__":
    main()
