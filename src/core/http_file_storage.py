# -*- coding: utf-8 -*-
"""
HTTP File Storage Client
用于上传和下载经验 MD 文件到云端服务器
"""

import os
import json
import hashlib
import urllib.request
import urllib.error
from typing import Optional, Dict, Any
from pathlib import Path


class HTTPFileStorage:
    """
    HTTP 文件存储客户端
    
    用于连接远程 Experience File Server
    """
    
    def __init__(
        self,
        host: str = "218.201.18.131",
        port: int = 8998,
        token: str = "agent-memory-token-2026"
    ):
        self.host = host
        self.port = port
        self.token = token
        self.base_url = f"http://{host}:{port}"
    
    def _make_request(self, method: str, path: str, data: dict = None) -> dict:
        """发送 HTTP 请求"""
        url = f"{self.base_url}{path}"
        
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
        
        body = json.dumps(data, ensure_ascii=False).encode('utf-8') if data else None
        
        req = urllib.request.Request(url, data=body, headers=headers, method=method)
        
        try:
            with urllib.request.urlopen(req, timeout=10) as response:
                response_data = response.read().decode('utf-8')
                return json.loads(response_data)
        except urllib.error.HTTPError as e:
            return {"error": f"HTTP {e.code}: {e.reason}"}
        except urllib.error.URLError as e:
            return {"error": f"Connection error: {e.reason}"}
        except Exception as e:
            return {"error": str(e)}
    
    def upload(
        self,
        code: str,
        content: str,
        filename: str = None
    ) -> Dict[str, Any]:
        """
        上传经验 MD 文件
        
        Args:
            code: 经验代码
            content: MD 文件内容
            filename: 文件名（可选）
        
        Returns:
            上传结果
        """
        if filename is None:
            filename = f"{code}.md"
        
        return self._make_request("POST", "/upload", {
            "code": code,
            "content": content,
            "filename": filename
        })
    
    def download(self, path: str) -> Optional[str]:
        """
        下载经验 MD 文件
        
        Args:
            path: 文件路径，如 /experiences/2026-04/EXP-BACKEND-FASTAPI-0001.md
        
        Returns:
            文件内容或 None
        """
        url = f"{self.base_url}{path}"
        
        headers = {
            "Authorization": f"Bearer {self.token}"
        }
        
        req = urllib.request.Request(url, headers=headers, method="GET")
        
        try:
            with urllib.request.urlopen(req, timeout=10) as response:
                return response.read().decode('utf-8')
        except Exception as e:
            print(f"Download error: {e}")
            return None
    
    def list(self) -> Dict[str, Any]:
        """列出所有文件"""
        return self._make_request("GET", "/")
    
    def delete(self, path: str) -> Dict[str, Any]:
        """删除文件"""
        return self._make_request("POST", "/delete", {"path": path})
    
    def health(self) -> Dict[str, Any]:
        """健康检查"""
        return self._make_request("GET", "/health")


# 全局实例
_http_storage: Optional[HTTPFileStorage] = None


def get_http_storage(
    host: str = "218.201.18.131",
    port: int = 8998,
    token: str = "agent-memory-token-2026"
) -> HTTPFileStorage:
    """获取全局 HTTP 存储实例"""
    global _http_storage
    if _http_storage is None:
        _http_storage = HTTPFileStorage(host, port, token)
    return _http_storage
