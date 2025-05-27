import os
import logging
from aiohttp import web
from server import PromptServer
from dotenv import load_dotenv
from .github_api import GitHubAPI
from .utils import load_config, ensure_dir_exists, WorkflowCache
from .data_sources import LocalWorkflowSource, GitHubWorkflowSource
from .auth_service import get_user_custom_data
from .auth_manager import AuthManager
from .api_handlers import (
    handle_get_workflows, 
    handle_get_workflow,
    handle_get_remote_workflows, 
    handle_get_remote_workflow,
    handle_clear_remote_cache,
    handle_get_user_info,
    handle_get_user_workflows,
    handle_get_user_workflow,
    handle_auth_login,
    handle_auth_register,
    handle_get_authorized_workflows,
    handle_check_workflow_auth,
    workflow_cache
)

# 加载环境变量
load_dotenv()

# 设置日志
logger = logging.getLogger('workflow_manager')
logger.info("="*50)
logger.info("工作流管理器插件开始加载...")
logger.info("="*50)

# 读取配置
cloud_config = load_config()

# GitHub相关配置
GITHUB_REPO_OWNER = cloud_config.get('github_repo_owner', '')
GITHUB_REPO_NAME = cloud_config.get('github_repo_name', '')
GITHUB_TOKEN = os.getenv('GITHUB_TOKEN') or cloud_config.get('github_token', '')
REMOTE_WORKFLOW_BASE_PATH = cloud_config.get('workflows_base_path', '')

# 工作流目录配置
LOCAL_WORKFLOW_DIR = cloud_config.get('local_workflow_dir', None)
if LOCAL_WORKFLOW_DIR:
    # 如果是相对路径，转换为绝对路径（相对于当前py文件目录）
    if not os.path.isabs(LOCAL_WORKFLOW_DIR):
        WORKFLOW_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), LOCAL_WORKFLOW_DIR))
    else:
        WORKFLOW_DIR = LOCAL_WORKFLOW_DIR
    logger.info(f"使用自定义本地工作流目录: {WORKFLOW_DIR}")
else:
    WORKFLOW_DIR = os.path.join(os.path.dirname(__file__), "workflows")
    logger.info(f"使用默认本地工作流目录: {WORKFLOW_DIR}")

# 确保工作流目录存在
ensure_dir_exists(WORKFLOW_DIR)

# 初始化GitHub API客户端
if not GITHUB_TOKEN:
    logger.warning("警告: 未设置 GITHUB_TOKEN，云端工作流功能将无法使用。")

github_api = GitHubAPI(GITHUB_REPO_OWNER, GITHUB_REPO_NAME, token=GITHUB_TOKEN)

# 初始化缓存
global_workflow_cache = WorkflowCache()
# 配置API处理模块的缓存实例
import sys
module = sys.modules['.'.join(__name__.split('.')[:-1]) + '.api_handlers']
setattr(module, 'workflow_cache', global_workflow_cache)

# 初始化数据源
local_source = LocalWorkflowSource(WORKFLOW_DIR)
github_source = GitHubWorkflowSource(github_api, REMOTE_WORKFLOW_BASE_PATH, global_workflow_cache)

def get_auth_manager_for_user(user_id, token=None):
    """为指定用户创建授权管理器
    
    Args:
        user_id: 用户ID
        token: 用户Token
    
    Returns:
        AuthManager实例
    """
    # 获取用户自定义数据
    udf_data = get_user_custom_data(token)
    
    # 创建并返回授权管理器
    auth_manager = AuthManager.from_authing_udf(udf_data)
    logger.info(f"为用户 {user_id} 创建授权管理器")
    return auth_manager

def get_user_workflows(user_id, token=None):
    """获取用户可访问的工作流列表，结合授权信息
    
    Args:
        user_id: 用户ID
        token: 用户Token
        
    Returns:
        用户可访问的工作流列表
    """
    logger.info(f"获取用户 {user_id} 的专属工作流")
    
    # 如果GitHub Token未配置，返回空列表
    if not GITHUB_TOKEN:
        logger.warning("获取用户工作流失败：GitHub Token未配置")
        return []
    
    try:
        # 从缓存获取用户工作流
        cache_key = f"user_workflows:{user_id}"
        cached_workflows = global_workflow_cache.get(cache_key)
        if cached_workflows is not None:
            return cached_workflows
        
        # 获取用户授权管理器
        auth_manager = get_auth_manager_for_user(user_id, token)
        
        # 获取授权工作流ID列表
        authorized_workflow_ids = auth_manager.get_workflow_list()
        if not authorized_workflow_ids:
            logger.warning(f"用户 {user_id} 没有授权的工作流")
            return []
            
        logger.info(f"用户 {user_id} 有 {len(authorized_workflow_ids)} 个授权工作流")
            
        # 定义用户工作流在GitHub仓库中的路径
        user_workflow_base_path = f"{REMOTE_WORKFLOW_BASE_PATH}/user_workflows"
        
        # 创建用户专用的GitHubWorkflowSource
        user_source = GitHubWorkflowSource(github_api, user_workflow_base_path, global_workflow_cache)
        
        # 获取全部可用工作流
        all_workflows = []
        
        # 扫描用户专属目录
        user_workflows = user_source.scan_directory()
        if user_workflows:
            all_workflows.extend(user_workflows)
            
        # 扫描公共目录
        public_source = GitHubWorkflowSource(github_api, REMOTE_WORKFLOW_BASE_PATH, global_workflow_cache)
        public_workflows = public_source.scan_directory()
        if public_workflows:
            all_workflows.extend(public_workflows)
            
        # 过滤工作流，只保留授权的工作流
        filtered_workflows = []
        
        for folder in all_workflows:
            folder_name = folder.get("name", "")
            files = folder.get("files", [])
            
            # 过滤文件列表，只保留授权的工作流
            authorized_files = []
            for file_name in files:
                # 提取工作流ID（去掉.json后缀）
                workflow_id = os.path.splitext(file_name)[0]
                
                # 检查是否有权限
                if workflow_id in authorized_workflow_ids:
                    authorized_files.append(file_name)
            
            # 如果有授权的文件，添加到结果中
            if authorized_files:
                filtered_workflows.append({
                    "name": folder_name,
                    "files": authorized_files
                })
        
        # 缓存结果
        global_workflow_cache.set(cache_key, filtered_workflows)
        
        logger.info(f"用户 {user_id} 授权工作流列表: {len(filtered_workflows)} 个文件夹")
        return filtered_workflows
    except Exception as e:
        logger.error(f"获取用户工作流失败: {e}")
        return []

def setup(app):
    """设置路由和初始化插件"""
    try:
        logger.info("="*50)
        logger.info("开始设置工作流管理器...")
        
        # 注册路由
        # 本地工作流路由
        app.router.add_get("/workflow_manager/list", handle_get_workflows)
        app.router.add_get("/workflow_manager/workflows/{path:.*}", handle_get_workflow)

        # 云端工作流路由
        app.router.add_get("/workflow_manager/list_remote", handle_get_remote_workflows)
        app.router.add_get("/workflow_manager/workflows_remote/{path:.*}", handle_get_remote_workflow)

        # 缓存清理路由
        app.router.add_post("/workflow_manager/clear_remote_cache", handle_clear_remote_cache)
        
        # 用户信息API路由
        app.router.add_get("/workflow_manager/user/info", handle_get_user_info)
        
        # 用户认证API路由
        app.router.add_post("/workflow_manager/auth/login", handle_auth_login)
        app.router.add_post("/workflow_manager/auth/register", handle_auth_register)
        
        # 用户工作流路由
        app.router.add_get("/workflow_manager/user/workflows", handle_get_user_workflows)
        app.router.add_get("/workflow_manager/user/workflows/{path:.*}", handle_get_user_workflow)
        
        # 授权工作流相关路由
        app.router.add_get("/workflow_manager/auth/workflows", handle_get_authorized_workflows)
        app.router.add_post("/workflow_manager/auth/check_workflow", handle_check_workflow_auth)

        logger.info("工作流管理器路由已注册")
        logger.info("="*50)
    except Exception as e:
        logger.error(f"设置过程中出错: {e}")
        raise
