import logging
from .workflow_manager import setup

# 设置日志
logger = logging.getLogger('workflow_manager_plugin')

# ComfyUI节点映射（此插件没有添加新节点）
NODE_CLASS_MAPPINGS = {}
NODE_DISPLAY_NAME_MAPPINGS = {}

# Web目录，用于前端文件
WEB_DIRECTORY = "./web"

__all__ = ['NODE_CLASS_MAPPINGS', 'NODE_DISPLAY_NAME_MAPPINGS', 'WEB_DIRECTORY', 'setup']

def init():
    """插件初始化函数"""
    logger.info("初始化工作流管理器插件...")
    from server import PromptServer
    setup(PromptServer.instance.app)

init()
