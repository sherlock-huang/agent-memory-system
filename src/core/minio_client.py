#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MinIO 客户端 - 云端经验文件存储

基于 AWS S3 SDK，支持：
- 上传经验文件到 MinIO
- 下载经验文件
- 列出云端经验
"""

import os
import json
from datetime import datetime
from typing import Optional, List, Dict, Any

try:
    import boto3
    from botocore.config import Config
    from botocore.exceptions import ClientError
except ImportError:
    print("请安装 boto3: pip install boto3")
    raise


class MinIOClient:
    """MinIO S3 客户端"""
    
    def __init__(
        self,
        endpoint: str = "218.201.18.133:9002",
        access_key: str = "admin",
        secret_key: str = "Minio12345678",
        bucket: str = "openclaw",
        region: str = "cn-east-1",
        cache_dir: str = "./cache/experiences"
    ):
        """
        初始化 MinIO 客户端
        
        Args:
            endpoint: MinIO API 地址
            access_key: 访问密钥
            secret_key: 秘密密钥
            bucket: 存储桶名称
            region: 区域（用于签名）
            cache_dir: 本地缓存目录
        """
        self.endpoint = f"http://{endpoint}"
        self.access_key = access_key
        self.secret_key = secret_key
        self.bucket = bucket
        self.region = region
        self.cache_dir = cache_dir
        
        # 创建 S3 客户端
        self.s3 = boto3.client(
            's3',
            endpoint_url=self.endpoint,
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
            region_name=self.region,
            config=Config(signature_version='s3v4')
        )
        
        # 确保缓存目录存在
        os.makedirs(self.cache_dir, exist_ok=True)
    
    def upload_experience(self, local_path: str, remote_key: str) -> bool:
        """
        上传经验文件到云端
        
        Args:
            local_path: 本地文件路径
            remote_key: 远程存储路径，如 "experiences/2026-04/EXP-DEVOPS-MINIO-0001.md"
            
        Returns:
            bool: 上传是否成功
        """
        try:
            self.s3.upload_file(
                local_path,
                self.bucket,
                remote_key,
                ExtraArgs={'ContentType': 'text/markdown'}
            )
            print(f"✓ 上传成功: {local_path} -> {self.bucket}/{remote_key}")
            return True
        except ClientError as e:
            print(f"✗ 上传失败: {e}")
            return False
    
    def download_experience(self, remote_key: str, local_path: Optional[str] = None) -> Optional[str]:
        """
        从云端下载经验文件
        
        Args:
            remote_key: 远程存储路径
            local_path: 本地保存路径，默认保存到缓存目录
            
        Returns:
            str: 本地文件路径，失败返回 None
        """
        if local_path is None:
            # 默认保存到缓存目录
            filename = os.path.basename(remote_key)
            local_path = os.path.join(self.cache_dir, filename)
        
        # 确保目录存在
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        
        try:
            self.s3.download_file(
                self.bucket,
                remote_key,
                local_path
            )
            print(f"✓ 下载成功: {self.bucket}/{remote_key} -> {local_path}")
            return local_path
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                print(f"✗ 文件不存在: {self.bucket}/{remote_key}")
            else:
                print(f"✗ 下载失败: {e}")
            return None
    
    def list_experiences(self, prefix: str = "experiences/") -> List[Dict[str, Any]]:
        """
        列出云端经验文件
        
        Args:
            prefix: 前缀筛选，默认列出 experiences/ 目录下的文件
            
        Returns:
            List[Dict]: 文件列表，包含 key, size, last_modified
        """
        try:
            response = self.s3.list_objects_v2(
                Bucket=self.bucket,
                Prefix=prefix
            )
            
            files = []
            if 'Contents' in response:
                for obj in response['Contents']:
                    files.append({
                        'key': obj['Key'],
                        'size': obj['Size'],
                        'last_modified': obj['LastModified'].isoformat() if obj.get('LastModified') else None
                    })
            
            return files
        except ClientError as e:
            print(f"✗ 列出文件失败: {e}")
            return []
    
    def delete_experience(self, remote_key: str) -> bool:
        """
        删除云端经验文件
        
        Args:
            remote_key: 远程存储路径
            
        Returns:
            bool: 删除是否成功
        """
        try:
            self.s3.delete_object(
                Bucket=self.bucket,
                Key=remote_key
            )
            print(f"✓ 删除成功: {self.bucket}/{remote_key}")
            return True
        except ClientError as e:
            print(f"✗ 删除失败: {e}")
            return False
    
    def exists(self, remote_key: str) -> bool:
        """
        检查文件是否存在
        
        Args:
            remote_key: 远程存储路径
            
        Returns:
            bool: 文件是否存在
        """
        try:
            self.s3.head_object(
                Bucket=self.bucket,
                Key=remote_key
            )
            return True
        except ClientError:
            return False
    
    def get_url(self, remote_key: str, expires_in: int = 3600) -> Optional[str]:
        """
        获取文件的临时访问URL
        
        Args:
            remote_key: 远程存储路径
            expires_in: URL 有效期（秒）
            
        Returns:
            str: 临时访问URL
        """
        try:
            url = self.s3.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.bucket, 'Key': remote_key},
                ExpiresIn=expires_in
            )
            return url
        except ClientError as e:
            print(f"✗ 生成URL失败: {e}")
            return None
    
    def test_connection(self) -> bool:
        """
        测试 MinIO 连接
        
        Returns:
            bool: 连接是否正常
        """
        try:
            self.s3.head_bucket(Bucket=self.bucket)
            print(f"✓ MinIO 连接成功: {self.endpoint}")
            print(f"  Bucket: {self.bucket}")
            return True
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            if error_code == '404':
                print(f"✗ Bucket 不存在: {self.bucket}")
            elif error_code == '403':
                print(f"✗ 无权访问 Bucket: {self.bucket}")
            else:
                print(f"✗ MinIO 连接失败: {e}")
            return False


def main():
    """命令行测试"""
    import argparse
    
    parser = argparse.ArgumentParser(description='MinIO 客户端工具')
    parser.add_argument('command', choices=['upload', 'download', 'list', 'delete', 'test'],
                        help='操作命令')
    parser.add_argument('--file', help='本地文件路径')
    parser.add_argument('--key', help='远程存储路径')
    parser.add_argument('--output', help='输出路径')
    args = parser.parse_args()
    
    client = MinIOClient()
    
    if args.command == 'test':
        client.test_connection()
    elif args.command == 'upload':
        if not args.file or not args.key:
            print("请提供 --file 和 --key")
            return
        client.upload_experience(args.file, args.key)
    elif args.command == 'download':
        if not args.key:
            print("请提供 --key")
            return
        client.download_experience(args.key, args.output)
    elif args.command == 'list':
        files = client.list_experiences()
        print(f"共 {len(files)} 个文件:")
        for f in files:
            print(f"  {f['key']} ({f['size']} bytes)")
    elif args.command == 'delete':
        if not args.key:
            print("请提供 --key")
            return
        client.delete_experience(args.key)


if __name__ == '__main__':
    main()
