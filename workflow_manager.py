import os
import json
from aiohttp import web
from server import PromptServer
import requests # Added for completeness, though github_api uses it
from dotenv import load_dotenv # Import load_dotenv
from .github_api import GitHubAPI # Import GitHubAPI from the new file
from .authing_auth import validate_token  # 导入Authing验证函数
from authing.v2.authentication import AuthenticationClient, AuthenticationClientOptions
import logging
import time

# Load environment variables from a .env file
load_dotenv()

print("="*50)
print("工作流管理器插件开始加载...")
print("="*50)

# 读取云端仓库配置
CONFIG_PATH = os.path.join(os.path.dirname(__file__), 'cloud_workflow_config.json')
with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
    cloud_config = json.load(f)
GITHUB_REPO_OWNER = cloud_config.get('github_repo_owner', '')
GITHUB_REPO_NAME = cloud_config.get('github_repo_name', '')
# 优先从环境变量读取token
GITHUB_TOKEN = os.getenv('GITHUB_TOKEN') or cloud_config.get('github_token', '')
REMOTE_WORKFLOW_BASE_PATH = cloud_config.get('workflows_base_path', '')
# 新增：本地工作流目录可配置
LOCAL_WORKFLOW_DIR = cloud_config.get('local_workflow_dir', None)

# 新增：用户配置
AUTH_CONFIG = cloud_config.get('auth', {})
AUTH_ENABLED = AUTH_CONFIG.get('enabled', False)
AUTH_APP_ID = os.getenv('AUTH_APP_ID') or AUTH_CONFIG.get('app_id', '')
AUTH_APP_SECRET = os.getenv('AUTH_APP_SECRET') or AUTH_CONFIG.get('app_secret', '')
AUTH_REDIRECT_URI = AUTH_CONFIG.get('redirect_uri', '')
APP_HOST = os.getenv('AUTH_APP_HOST') or AUTH_CONFIG.get('app_host', 'https://starfusion.authing.cn')

if LOCAL_WORKFLOW_DIR:
    # 如果是相对路径，转换为绝对路径（相对于当前py文件目录）
    if not os.path.isabs(LOCAL_WORKFLOW_DIR):
        WORKFLOW_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), LOCAL_WORKFLOW_DIR))
    else:
        WORKFLOW_DIR = LOCAL_WORKFLOW_DIR
    print(f"[工作流管理器] 使用自定义本地工作流目录: {WORKFLOW_DIR}")
else:
    WORKFLOW_DIR = os.path.join(os.path.dirname(__file__), "workflows")
    print(f"[工作流管理器] 使用默认本地工作流目录: {WORKFLOW_DIR}")

if not GITHUB_TOKEN:
    print("[工作流管理器] 警告: 未设置 GITHUB_TOKEN，云端工作流功能将无法使用。")

if AUTH_ENABLED:
    if not AUTH_APP_ID or not AUTH_APP_SECRET:
        print("[工作流管理器] 警告: 登录功能已启用，但未设置完整的认证配置，可能无法正常工作。")
    else:
        print(f"[工作流管理器] 登录功能已启用，AppID: {AUTH_APP_ID}")
else:
    print("[工作流管理器] 登录功能未启用")

github_api = GitHubAPI(GITHUB_REPO_OWNER, GITHUB_REPO_NAME, token=GITHUB_TOKEN)

# Define a simple cache for workflow data
class WorkflowCache:
    def __init__(self, expire_time=3600): # Cache expires after 3600 seconds (1 hour)
        self.cache = {}
        self.expire_time = expire_time
        print(f"[工作流管理器] 缓存初始化，过期时间: {self.expire_time} 秒")

    def get(self, key):
        """Get data from cache if not expired."""
        if key in self.cache:
            data, timestamp = self.cache[key]
            if time.time() - timestamp < self.expire_time:
                print(f"[工作流管理器] 缓存命中: {key}")
                return data
            else:
                print(f"[工作流管理器] 缓存过期: {key}")
                del self.cache[key]
        print(f"[工作流管理器] 缓存未命中: {key}")
        return None

    def set(self, key, value):
        """Set data in cache with current timestamp."""
        self.cache[key] = (value, time.time())
        print(f"[工作流管理器] 缓存更新: {key}")

# Instantiate the cache
workflow_cache = WorkflowCache()

# 确保工作流目录存在
os.makedirs(WORKFLOW_DIR, exist_ok=True)

# 使用新的Authing验证函数（实现用户token验证，核心代码）
def validate_user_token(token):
    """
    验证用户Token并返回用户信息
    
    Args:
        token: 用户Token
        
    Returns:
        用户信息dict或None(验证失败)
    """
    print(f"[工作流管理器] 验证用户token: {token[:10] if token and len(token) > 10 else 'None or short token'}...")
    
    # 检查是否是模拟token
    if token and token.startswith('mock_token_'):
        print("[工作流管理器] 检测到模拟token，返回模拟用户数据")
        # 从本地存储获取用户数据
        return {
            "id": "mock_user",
            "username": "模拟用户",
            "nickname": "模拟用户",
            "avatar": "https://via.placeholder.com/100/3a80d2/ffffff?text=M",
            "is_mock": True
        }
    
    # 如果认证功能未启用，返回模拟用户数据
    if not AUTH_ENABLED:
        print("[工作流管理器] 认证功能未启用，返回模拟用户数据")
        return {
            "id": "test_user",
            "username": "test_user",
            "nickname": "测试用户",
            "avatar": "https://via.placeholder.com/100",
            "is_mock": True
        }
    
    # 调用Authing验证函数
    return validate_token(token)

# ====== 工作流数据源抽象类 ======
class WorkflowDataSource:
    """工作流数据源基类，定义统一接口"""
    
    def __init__(self):
        self.name = "Base"
    
    def scan_directory(self, base_path):
        """扫描目录，返回工作流列表"""
        raise NotImplementedError("子类必须实现scan_directory方法")
    
    def get_workflow(self, path):
        """获取特定工作流文件内容"""
        raise NotImplementedError("子类必须实现get_workflow方法")

# 本地文件系统数据源
class LocalWorkflowSource(WorkflowDataSource):
    """本地文件系统工作流数据源"""
    
    def __init__(self, base_dir):
        super().__init__()
        self.name = "Local"
        self.base_dir = base_dir
    
    def scan_directory(self, base_path=None):
        """扫描本地目录，返回工作流列表"""
        data = []
        scan_dir = self.base_dir
        if base_path:
            scan_dir = os.path.join(self.base_dir, base_path)
            
        try:
            print(f"[工作流管理器] 开始扫描本地目录: {scan_dir}")
            if not os.path.exists(scan_dir):
                print(f"[工作流管理器] 警告: 目录不存在: {scan_dir}")
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
                    print(f"[工作流管理器] 添加本地文件夹: {rel_root}")
                    print(f"[工作流管理器] 发现本地文件: {json_files}")

        except Exception as e:
            print(f"[工作流管理器] 扫描本地工作流目录时出错: {e}")
        return data
    
    def get_workflow(self, path):
        """获取本地工作流文件内容"""
        try:
            file_path = os.path.join(self.base_dir, path)
            print(f"[工作流管理器] 读取本地工作流文件: {file_path}")
            
            if not os.path.exists(file_path):
                print(f"[工作流管理器] 本地文件不存在: {file_path}")
                return None, "File not found"
                
            with open(file_path, 'r', encoding='utf-8') as f:
                content = json.load(f)
                print(f"[工作流管理器] 成功加载本地工作流文件: {file_path}")
                return content, None
        except json.JSONDecodeError:
            return None, "Invalid JSON content"
        except Exception as e:
            print(f"[工作流管理器] 加载本地工作流文件时出错: {e}")
            return None, str(e)

# GitHub数据源
class GitHubWorkflowSource(WorkflowDataSource):
    """GitHub工作流数据源"""
    
    def __init__(self, github_api, base_path="", cache=None):
        super().__init__()
        self.name = "GitHub"
        self.github_api = github_api
        self.base_path = base_path
        self.cache = cache
    
    def scan_directory(self, path=None):
        """扫描GitHub目录，返回工作流列表"""
        data = []
        full_path = path if path else self.base_path
        
        try:
            print(f"[工作流管理器] 开始扫描GitHub目录: {full_path}")
            
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
                print(f"[工作流管理器] 获取GitHub目录内容失败或目录不存在: {full_path}")
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
                print(f"[工作流管理器] 添加GitHub文件夹: {folder_name}")
                print(f"[工作流管理器] 发现GitHub文件: {[f['name'] for f in files]}")

            # 递归扫描子目录
            for d in dirs:
                sub_path = os.path.join(full_path, d['name']).replace('\\', '/') # GitHub路径使用/
                data.extend(self.scan_directory(sub_path))

        except Exception as e:
            print(f"[工作流管理器] 扫描GitHub工作流目录时出错: {e}")
        return data
    
    def get_workflow(self, path):
        """获取GitHub工作流文件内容"""
        try:
            # 处理路径，移除开头的/
            github_path = path.lstrip('/')
            print(f"[工作流管理器] 读取GitHub工作流文件: {github_path}")
            
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
                print(f"[工作流管理器] GitHub文件不存在或获取失败: {github_path}")
                return None, "Remote file not found or access denied"

            # 解析JSON内容
            try:
                workflow_json = json.loads(content)
                print(f"[工作流管理器] 成功加载GitHub工作流文件: {github_path}")
                return workflow_json, None
            except json.JSONDecodeError:
                print(f"[工作流管理器] 解析GitHub工作流JSON失败: {github_path}")
                return None, "Invalid JSON content"
                
        except Exception as e:
            print(f"[工作流管理器] 加载GitHub工作流文件时出错: {e}")
            return None, str(e)

# 获取用户专属工作流目录
def get_user_workflows(user_id):
    """获取用户可访问的工作流列表"""
    print(f"[工作流管理器] 获取用户 {user_id} 的专属工作流")
    
    # 如果GitHub Token未配置，返回空列表
    if not GITHUB_TOKEN:
        print("[工作流管理器] 获取用户工作流失败：GitHub Token未配置")
        return []
    
    try:
        # 定义用户工作流在GitHub仓库中的路径
        # 可以根据实际情况修改路径结构，例如可以添加用户ID作为子目录
        # 或者在仓库中创建专门的用户工作流目录
        user_workflow_base_path = f"{REMOTE_WORKFLOW_BASE_PATH}/user_workflows"
        
        # 从缓存中获取或从GitHub读取用户工作流目录内容
        cache_key = f"user_workflows:{user_id}"
        cached_workflows = workflow_cache.get(cache_key)
        
        if cached_workflows is not None:
            return cached_workflows
        
        # 使用GitHub API获取用户工作流目录结构
        user_workflows = scan_remote_workflow_dir(github_api, user_workflow_base_path)
        
        # 如果找不到用户工作流目录，尝试读取公共工作流
        if not user_workflows:
            print(f"[工作流管理器] 未找到用户工作流目录，尝试使用公共工作流: {user_workflow_base_path}")
            # 可以返回一部分云端工作流作为替代
            user_workflows = scan_remote_workflow_dir(github_api, REMOTE_WORKFLOW_BASE_PATH)
            
            # 如果有工作流数据，添加一个说明标签
            if user_workflows:
                # 如果目录结构层次太深，可以做一些简化
                user_workflows = [
                    {
                        "name": "推荐工作流",
                        "files": folder["files"] if folder.get("name") == "/" else []
                    } for folder in user_workflows if folder.get("files")
                ][:3]  # 只取前3个工作流文件夹作为示例
        
        # 缓存结果
        workflow_cache.set(cache_key, user_workflows)
        
        return user_workflows
    except Exception as e:
        print(f"[工作流管理器] 获取用户工作流失败: {e}")
        return []

# 添加统一的辅助函数和处理函数

# 统一的令牌验证辅助函数
async def get_and_validate_token(request):
    """从请求获取并验证令牌
    
    Args:
        request: aiohttp请求对象
        
    Returns:
        (user_info, error_response): 如果验证成功，error_response为None；否则user_info为None
    """
    # 从请求头获取token
    auth_header = request.headers.get('Authorization', '')
    token = auth_header.replace('Bearer ', '') if auth_header.startswith('Bearer ') else ''
    
    if not token:
        print("[工作流管理器] 未提供token")
        return None, web.json_response({"error": "Token required"}, status=401)
        
    # 验证token
    user_info = validate_user_token(token)
    if not user_info:
        print("[工作流管理器] token验证失败")
        return None, web.json_response({"error": "Invalid token"}, status=401)
    
    return user_info, None

# 统一的响应构建函数
def build_workflow_response(workflow_data, error=None, status=200):
    """构建统一的工作流响应
    
    Args:
        workflow_data: 工作流数据
        error: 错误信息
        status: HTTP状态码
        
    Returns:
        aiohttp响应对象
    """
    if error:
        return web.json_response({"error": error}, status=status)
    return web.json_response(workflow_data)

# 统一的工作流列表获取处理
async def handle_get_workflows_generic(request, data_source, source_name=""):
    """统一处理工作流列表获取
    
    Args:
        request: 请求对象
        data_source: 数据源对象
        source_name: 数据源名称
    """
    try:
        print(f"[工作流管理器] 收到获取{source_name}工作流列表请求")
        
        structure = data_source.scan_directory()
        print(f"[工作流管理器] {source_name}工作流列表: {json.dumps(structure, ensure_ascii=False)}")
        
        response = web.json_response(structure)
        print(f"[工作流管理器] {source_name}响应状态: {response.status}")
        return response
    except Exception as e:
        print(f"[工作流管理器] 获取{source_name}工作流列表时出错: {e}")
        return web.json_response({"error": str(e)}, status=500)

# 统一的工作流文件获取处理
async def handle_get_workflow_generic(request, data_source, source_name=""):
    """统一处理工作流文件获取
    
    Args:
        request: 请求对象
        data_source: 数据源对象
        source_name: 数据源名称
    """
    try:
        rel_path = request.match_info['path']
        print(f"[工作流管理器] 收到获取{source_name}工作流请求: {rel_path}")
        
        content, error = data_source.get_workflow(rel_path)
        if error:
            status = 404 if "not found" in error.lower() else 500
            return web.json_response({"error": error}, status=status)
        
        print(f"[工作流管理器] 成功加载{source_name}工作流: {rel_path}")
        return web.json_response(content)
    except Exception as e:
        print(f"[工作流管理器] 加载{source_name}工作流时出错: {e}")
        return web.json_response({"error": str(e)}, status=500)

# 更新现有的处理函数，使用新的数据源和统一处理函数
async def handle_get_workflows(request):
    """获取本地工作流列表"""
    local_source = LocalWorkflowSource(WORKFLOW_DIR)
    return await handle_get_workflows_generic(request, local_source, "本地")

async def handle_get_remote_workflows(request):
    """获取云端工作流列表"""
    try:
        print("[工作流管理器] 收到获取云端工作流列表请求")
        
        # 验证用户Token
        user_info, error_response = await get_and_validate_token(request)
        if error_response:
            return error_response
        
        if not GITHUB_TOKEN:
            return web.json_response({"error": "GitHub Token not configured"}, status=500)
        
        github_source = GitHubWorkflowSource(github_api, REMOTE_WORKFLOW_BASE_PATH, workflow_cache)
        return await handle_get_workflows_generic(request, github_source, "云端")
    except Exception as e:
        print(f"[工作流管理器] 获取云端工作流列表时出错: {e}")
        return web.json_response({"error": str(e)}, status=500)

async def handle_get_workflow(request):
    """获取本地工作流文件"""
    local_source = LocalWorkflowSource(WORKFLOW_DIR)
    return await handle_get_workflow_generic(request, local_source, "本地")

async def handle_get_remote_workflow(request):
    """获取云端工作流文件"""
    try:
        print("[工作流管理器] 收到获取云端工作流请求")
        
        # 验证用户Token
        user_info, error_response = await get_and_validate_token(request)
        if error_response:
            return error_response
        
        if not GITHUB_TOKEN:
            return web.json_response({"error": "GitHub Token not configured"}, status=500)
        
        github_source = GitHubWorkflowSource(github_api, REMOTE_WORKFLOW_BASE_PATH, workflow_cache)
        return await handle_get_workflow_generic(request, github_source, "云端")
    except Exception as e:
        print(f"[工作流管理器] 获取云端工作流时出错: {e}")
        return web.json_response({"error": str(e)}, status=500)

# 更新清除缓存处理函数
async def handle_clear_remote_cache(request):
    """清除远程缓存"""
    try:
        print("[工作流管理器] 收到清除云端缓存请求")
        
        # 验证用户Token
        user_info, error_response = await get_and_validate_token(request)
        if error_response:
            return error_response
            
        workflow_cache.cache.clear()
        print("[工作流管理器] 云端缓存已清除")
        return web.json_response({"status": "success", "message": "云端缓存已清除"})
    except Exception as e:
        print(f"[工作流管理器] 清除云端缓存时出错: {e}")
        return web.json_response({"error": str(e)}, status=500)

# 新增: 用户相关API处理函数
# 1. 获取用户信息
async def handle_get_user_info(request):
    try:
        print("[工作流管理器] 收到获取用户信息请求")
        
        # 从请求头获取token
        auth_header = request.headers.get('Authorization', '')
        token = auth_header.replace('Bearer ', '') if auth_header.startswith('Bearer ') else ''
        
        # 如果没有提供token，则返回匿名用户状态
        if not token:
            print("[工作流管理器] 未提供token，返回匿名用户状态")
            return web.json_response({
                "authenticated": False,
                "message": "未登录状态"
            })
            
        # 验证token
        user_info = validate_user_token(token)
        if not user_info:
            print("[工作流管理器] token验证失败")
            return web.json_response({"error": "Invalid token"}, status=401)
            
        # 添加认证状态到返回结果
        user_info['authenticated'] = True
        user_info['token'] = token
        
        print(f"[工作流管理器] 成功获取用户信息: {json.dumps(user_info, ensure_ascii=False)}")
        return web.json_response(user_info)
    except Exception as e:
        print(f"[工作流管理器] 获取用户信息时出错: {e}")
        return web.json_response({"error": str(e)}, status=500)

# 2. 获取用户工作流列表
async def handle_get_user_workflows(request):
    """获取用户工作流列表"""
    try:
        print("[工作流管理器] 收到获取用户工作流列表请求")
        
        # 验证用户Token
        user_info, error_response = await get_and_validate_token(request)
        if error_response:
            return error_response
        
        # 获取用户ID
        user_id = user_info.get('id')
        
        # 获取用户工作流列表
        # 首先检查GitHub Token是否配置
        if not GITHUB_TOKEN:
            return web.json_response({"error": "GitHub Token not configured"}, status=500)
        
        # 定义用户工作流在GitHub仓库中的路径
        user_workflow_base_path = f"{REMOTE_WORKFLOW_BASE_PATH}/user_workflows"
        
        # 从缓存中获取或从GitHub读取用户工作流目录内容
        cache_key = f"user_workflows:{user_id}"
        cached_workflows = workflow_cache.get(cache_key)
        
        if cached_workflows is not None:
            return web.json_response(cached_workflows)
        
        # 创建GitHub数据源
        github_source = GitHubWorkflowSource(github_api, user_workflow_base_path, workflow_cache)
        
        # 获取用户工作流
        user_workflows = github_source.scan_directory()
        
        # 如果找不到用户工作流目录，尝试读取公共工作流
        if not user_workflows:
            print(f"[工作流管理器] 未找到用户工作流目录，尝试使用公共工作流")
            
            # 使用公共目录数据源
            public_source = GitHubWorkflowSource(github_api, REMOTE_WORKFLOW_BASE_PATH, workflow_cache)
            public_workflows = public_source.scan_directory()
            
            # 如果有工作流数据，添加一个说明标签并简化
            if public_workflows:
                # 简化目录结构
                user_workflows = [
                    {
                        "name": "推荐工作流",
                        "files": folder["files"] if folder.get("name") == "/" else []
                    } for folder in public_workflows if folder.get("files")
                ][:3]  # 只取前3个工作流文件夹作为示例
        
        # 缓存结果
        workflow_cache.set(cache_key, user_workflows)
        
        print(f"[工作流管理器] 用户工作流列表: {json.dumps(user_workflows, ensure_ascii=False)}")
        return web.json_response(user_workflows)
    except Exception as e:
        print(f"[工作流管理器] 获取用户工作流列表时出错: {e}")
        return web.json_response({"error": str(e)}, status=500)

# 3. 获取用户特定工作流
async def handle_get_user_workflow(request):
    """获取用户特定工作流"""
    try:
        print("[工作流管理器] 收到获取用户特定工作流请求")
        rel_path = request.match_info['path']
        
        # 验证用户Token
        user_info, error_response = await get_and_validate_token(request)
        if error_response:
            return error_response
        
        # 获取用户ID
        user_id = user_info.get('id')
        
        print(f"[工作流管理器] 用户 {user_id} 请求工作流: {rel_path}")
        
        # 检查GitHub Token是否配置
        if not GITHUB_TOKEN:
            return web.json_response({"error": "GitHub Token not configured"}, status=500)
        
        # 构建在GitHub仓库中的完整路径 - 首先尝试用户专属目录
        # 创建用户工作流数据源
        user_path = f"{REMOTE_WORKFLOW_BASE_PATH}/user_workflows/{rel_path}"
        user_source = GitHubWorkflowSource(github_api, "", workflow_cache)
        
        # 尝试获取用户专属工作流
        content, error = user_source.get_workflow(user_path)
        
        # 如果找不到，尝试从公共目录获取
        if error and "not found" in error.lower():
            print(f"[工作流管理器] 用户工作流不存在，尝试从公共目录获取: {rel_path}")
            public_path = f"{REMOTE_WORKFLOW_BASE_PATH}/{rel_path}"
            content, error = user_source.get_workflow(public_path)
        
        # 如果仍然有错误，返回错误响应
        if error:
            status = 404 if "not found" in error.lower() else 500
            return web.json_response({"error": error}, status=status)
        
        print(f"[工作流管理器] 成功获取用户工作流: {rel_path}")
        return web.json_response(content)
    except Exception as e:
        print(f"[工作流管理器] 获取用户工作流时出错: {e}")
        return web.json_response({"error": str(e)}, status=500)

# # 新增: 处理Authing登录回调
# async def handle_authing_callback(request):
#     try:
#         print("[工作流管理器] 收到Authing回调请求")
#         # 这里处理回调，如果需要在服务端处理的话
#         # 实际上大部分处理都在前端authing_callback.html中完成了
#         return web.json_response({
#             "status": "success",
#             "message": "登录回调成功"
#         })
#     except Exception as e:
#         print(f"[工作流管理器] 处理Authing回调时出错: {e}")
#         return web.json_response({"error": str(e)}, status=500)

# 新增: 处理用户登录API
async def handle_auth_login(request):
    try:
        print("[工作流管理器] 收到用户登录请求")
        # 获取用户名和密码
        data = await request.json()
        username = data.get('username')
        password = data.get('password')
        
        if not username or not password:
            return web.json_response({
                "error": "Missing username or password",
                "message": "请提供用户名和密码"
            }, status=400)
        
        # 使用Authing API验证登录
        print(f"[工作流管理器] 尝试使用Authing验证用户: {username}")
        
        try:
            if not AUTH_ENABLED:
                print("[工作流管理器] 认证功能未启用，返回模拟登录结果")
                # 认证功能未启用，返回模拟登录结果
                mock_user = {
                    "id": f"mock_{username}",
                    "username": username,
                    "nickname": username,
                    "photo": f"https://via.placeholder.com/100/3a80d2/ffffff?text={username[0].upper()}",
                    "token": f"mock_token_{username}_{int(time.time())}",
                    "is_mock": True
                }
                return web.json_response(mock_user)
            
            # 初始化Authing客户端
            try:
                # 使用参考代码中的方式创建Authing客户端
                auth_client = AuthenticationClient(
                    options=AuthenticationClientOptions(
                        app_id=AUTH_APP_ID,
                        app_host=APP_HOST,
                    )
                )
                
                # 使用用户名密码登录
                user = auth_client.login_by_username(
                    username=username, 
                    password=password
                )
                
                print(f"[工作流管理器] Authing登录成功: {user.get('id')}")
                
                # 返回登录结果
                return web.json_response(user)
            except Exception as auth_error:
                print(f"[工作流管理器] Authing登录失败: {auth_error}")
                return web.json_response({
                    "error": "Login failed",
                    "message": f"登录失败: {str(auth_error)}" 
                }, status=401)
        except Exception as e:
            print(f"[工作流管理器] 处理登录请求时出错: {e}")
            return web.json_response({
                "error": "Internal server error",
                "message": "服务器内部错误，请稍后重试"
            }, status=500)
    except Exception as e:
        print(f"[工作流管理器] 登录API处理失败: {e}")
        return web.json_response({
            "error": str(e),
            "message": "请求处理失败"
        }, status=500)

# 新增: 处理用户注册API
async def handle_auth_register(request):
    try:
        print("[工作流管理器] 收到用户注册请求")
        # 获取用户名和密码
        data = await request.json()
        username = data.get('username')
        password = data.get('password')
        
        if not username or not password:
            return web.json_response({
                "error": "Missing username or password",
                "message": "请提供用户名和密码"
            }, status=400)
        
        # 用户名基本验证
        if len(username) < 3:
            return web.json_response({
                "error": "Invalid username",
                "message": "用户名长度至少为3个字符"
            }, status=400)
        
        # 密码基本验证
        if len(password) < 6:
            return web.json_response({
                "error": "Invalid password",
                "message": "密码长度至少为6个字符"
            }, status=400)
        
        print(f"[工作流管理器] 尝试注册用户: {username}")
        
        try:
            if not AUTH_ENABLED:
                print("[工作流管理器] 认证功能未启用，返回模拟注册结果")
                # 认证功能未启用，返回模拟注册结果
                mock_user = {
                    "id": f"mock_{username}",
                    "username": username,
                    "nickname": username,
                    "photo": f"https://via.placeholder.com/100/3a80d2/ffffff?text={username[0].upper()}",
                    "token": f"mock_token_{username}_{int(time.time())}",
                    "is_mock": True
                }
                return web.json_response(mock_user)
            
            # 初始化Authing客户端
            auth_client = AuthenticationClient(
                options=AuthenticationClientOptions(
                    app_id=AUTH_APP_ID,
                    app_host=APP_HOST,
                )
            )
            
            # 检查用户名是否已存在
            try:
                # 尝试查找用户
                user_exist = auth_client.find_user_by_username(username)
                if user_exist and user_exist.get('id'):
                    print(f"[工作流管理器] 用户名已存在: {username}")
                    return web.json_response({
                        "error": "Username exists",
                        "message": "用户名已存在，请选择其他用户名"
                    }, status=409)
            except Exception as find_error:
                # 如果是因为用户不存在导致的错误，则继续注册流程
                print(f"[工作流管理器] 查找用户时出错: {find_error}")
                # 继续注册流程
            
            # 使用Authing API注册用户
            new_user = auth_client.register_by_username(
                username=username,
                password=password
            )
            
            if not new_user or not new_user.get('id'):
                print(f"[工作流管理器] 注册失败，Authing返回: {new_user}")
                return web.json_response({
                    "error": "Registration failed",
                    "message": "注册失败，请稍后重试"
                }, status=500)
            
            print(f"[工作流管理器] 注册成功: {new_user.get('id')}")
            
            # 注册成功后自动登录
            user = auth_client.login_by_username(
                username=username,
                password=password
            )
            
            # 返回登录结果
            return web.json_response(user)
        except Exception as auth_error:
            print(f"[工作流管理器] Authing注册失败: {auth_error}")
            return web.json_response({
                "error": "Registration failed",
                "message": f"注册失败: {str(auth_error)}"
            }, status=400)
    except Exception as e:
        print(f"[工作流管理器] 注册API处理失败: {e}")
        return web.json_response({
            "error": str(e),
            "message": "请求处理失败"
        }, status=500)

def setup(app):
    try:
        print("="*50)
        print("[工作流管理器] 开始设置工作流管理器...")
        print(f"[工作流管理器] 本地工作流目录: {WORKFLOW_DIR}")
        
        # 创建数据源实例
        local_source = LocalWorkflowSource(WORKFLOW_DIR)
        github_source = GitHubWorkflowSource(github_api, REMOTE_WORKFLOW_BASE_PATH, workflow_cache)
        
        print("[工作流管理器] 已初始化数据源")

        # 注册路由
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

        print("[工作流管理器] 工作流管理器路由已注册")
        print("="*50)
    except Exception as e:
        print(f"[工作流管理器] 设置过程中出错: {e}")
        raise
