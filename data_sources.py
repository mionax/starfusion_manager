import os
import json
import logging
from abc import ABC, abstractmethod

logger = logging.getLogger('data_sources')

class WorkflowDataSource(ABC):
    """工作流数据源基类，定义统一接口"""
    
    def __init__(self, name="Base"):
        self.name = name
    
    @abstractmethod
    def scan_directory(self, base_path):
        """扫描目录，返回工作流列表"""
        pass
    
    @abstractmethod
    def get_workflow(self, path):
        """获取特定工作流文件内容"""
        pass


class LocalWorkflowSource(WorkflowDataSource):
    """本地文件系统工作流数据源"""
    
    def __init__(self, base_dir):
        super().__init__(name="Local")
        self.base_dir = base_dir
    
    def scan_directory(self, base_path=None):
        """扫描本地目录，返回工作流列表"""
        data = []
        scan_dir = self.base_dir
        if base_path:
            scan_dir = os.path.join(self.base_dir, base_path)
            
        try:
            logger.info(f"开始扫描本地目录: {scan_dir}")
            if not os.path.exists(scan_dir):
                logger.warning(f"警告: 目录不存在: {scan_dir}")
                return data

            for root, dirs, files in os.walk(scan_dir):
                rel_root = os.path.relpath(root, self.base_dir)
                if rel_root == ".":
                    rel_root = ""
                # 过滤非.json文件
                json_files = [f for f in files if f.endswith(".json")]
                if json_files and rel_root != ".":
                    data.append({
                        "name": rel_root if rel_root != "" else "/",
                        "files": json_files
                    })
                    logger.info(f"添加本地文件夹: {rel_root}")
                    logger.info(f"发现本地文件: {json_files}")

        except Exception as e:
            logger.error(f"扫描本地工作流目录时出错: {e}")
        return data
    
    def get_workflow(self, path):
        """获取本地工作流文件内容"""
        try:
            file_path = os.path.join(self.base_dir, path)
            logger.info(f"读取本地工作流文件: {file_path}")
            
            if not os.path.exists(file_path):
                logger.warning(f"本地文件不存在: {file_path}")
                return None, "File not found"
                
            with open(file_path, 'r', encoding='utf-8') as f:
                content = json.load(f)
                logger.info(f"成功加载本地工作流文件: {file_path}")
                return content, None
        except json.JSONDecodeError:
            return None, "Invalid JSON content"
        except Exception as e:
            logger.error(f"加载本地工作流文件时出错: {e}")
            return None, str(e)


class GitHubWorkflowSource(WorkflowDataSource):
    """GitHub工作流数据源"""
    
    def __init__(self, github_api, base_path="", cache=None):
        super().__init__(name="GitHub")
        self.github_api = github_api
        self.base_path = base_path
        self.cache = cache
    
    def scan_directory(self, path=None):
        """扫描GitHub目录，返回工作流列表"""
        data = []
        full_path = path if path else self.base_path
        
        try:
            logger.info(f"开始扫描GitHub目录: {full_path}")
            
            # 检查缓存
            if self.cache:
                cache_key = f"dir_list:{full_path}"
                cached_contents = self.cache.get(cache_key)
                
                if cached_contents is not None:
                    contents = cached_contents
                else:
                    contents = self.github_api.get_contents(full_path)
                    if contents is not None:
                        self.cache.set(cache_key, contents)
            else:
                contents = self.github_api.get_contents(full_path)

            if contents is None:
                logger.warning(f"获取GitHub目录内容失败或目录不存在: {full_path}")
                return data
                
            # 分离文件和目录
            files = [item for item in contents if item['type'] == 'file' and item['name'].endswith('.json')]
            dirs = [item for item in contents if item['type'] == 'dir']

            # 添加当前目录的文件
            if files:
                folder_name = full_path if full_path != '' else '/'
                data.append({
                    "name": folder_name,
                    "files": [f['name'] for f in files]
                })
                logger.info(f"添加GitHub文件夹: {folder_name}")
                logger.info(f"发现GitHub文件: {[f['name'] for f in files]}")

            # 递归扫描子目录
            for d in dirs:
                sub_path = os.path.join(full_path, d['name']).replace('\\', '/') # GitHub路径使用/
                data.extend(self.scan_directory(sub_path))

        except Exception as e:
            logger.error(f"扫描GitHub工作流目录时出错: {e}")
        return data
    
    def get_workflow(self, path):
        """获取GitHub工作流文件内容"""
        try:
            # 处理路径，移除开头的/
            github_path = path.lstrip('/')
            logger.info(f"读取GitHub工作流文件: {github_path}")
            
            # 检查缓存
            content = None
            if self.cache:
                cache_key = f"file_content:{github_path}"
                cached_content = self.cache.get(cache_key)
                
                if cached_content is not None:
                    content = cached_content
                else:
                    content = self.github_api.get_file_content(github_path)
                    if content is not None:
                        self.cache.set(cache_key, content)
            else:
                content = self.github_api.get_file_content(github_path)

            if content is None:
                logger.warning(f"GitHub文件不存在或获取失败: {github_path}")
                return None, "Remote file not found or access denied"

            # 解析JSON内容
            try:
                workflow_json = json.loads(content)
                logger.info(f"成功加载GitHub工作流文件: {github_path}")
                return workflow_json, None
            except json.JSONDecodeError:
                logger.warning(f"解析GitHub工作流JSON失败: {github_path}")
                return None, "Invalid JSON content"
                
        except Exception as e:
            logger.error(f"加载GitHub工作流文件时出错: {e}")
            return None, str(e) 