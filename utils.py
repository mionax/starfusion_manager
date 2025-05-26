import os
import json
import time
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('workflow_manager')

# 定义一个简单的缓存类
class WorkflowCache:
    def __init__(self, expire_time=3600):  # 缓存在3600秒(1小时)后过期
        self.cache = {}
        self.expire_time = expire_time
        logger.info(f"缓存初始化，过期时间: {self.expire_time} 秒")

    def get(self, key):
        """从缓存获取数据（如果未过期）"""
        if key in self.cache:
            data, timestamp = self.cache[key]
            if time.time() - timestamp < self.expire_time:
                logger.info(f"缓存命中: {key}")
                return data
            else:
                logger.info(f"缓存过期: {key}")
                del self.cache[key]
        logger.info(f"缓存未命中: {key}")
        return None

    def set(self, key, value):
        """将数据存入缓存，带有当前时间戳"""
        self.cache[key] = (value, time.time())
        logger.info(f"缓存更新: {key}")
        
    def clear(self):
        """清空缓存"""
        self.cache.clear()
        logger.info("缓存已清空")

def load_config():
    """加载配置文件"""
    config_path = os.path.join(os.path.dirname(__file__), 'cloud_workflow_config.json')
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        return config
    except Exception as e:
        logger.error(f"加载配置文件出错: {e}")
        return {}

def ensure_dir_exists(dir_path):
    """确保目录存在，不存在则创建"""
    if not os.path.exists(dir_path):
        os.makedirs(dir_path, exist_ok=True)
        logger.info(f"创建目录: {dir_path}")
    return dir_path 