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

# 使用新的Authing验证函数
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

def scan_workflow_dir(base_dir):
    data = []
    try:
        print(f"[工作流管理器] 开始扫描目录: {base_dir}")
        if not os.path.exists(base_dir):
            print(f"[工作流管理器] 警告: 目录不存在: {base_dir}")
            return data

        for root, dirs, files in os.walk(base_dir):
            rel_root = os.path.relpath(root, base_dir)
            if rel_root == ".":
                rel_root = ""
            # Exclude the base directory itself unless it contains files
            if rel_root != ".":
                 # Filter out files that are not .json
                json_files = [f for f in files if f.endswith(".json")]
                if json_files:
                    data.append({
                        "name": rel_root if rel_root != "" else "/", # Use "/" for the root
                        "files": json_files
                    })
                    print(f"[工作流管理器] 添加本地文件夹: {rel_root}")
                    print(f"[工作流管理器] 发现本地文件: {json_files}")

    except Exception as e:
        print(f"[工作流管理器] 扫描本地工作流目录时出错: {e}")
    return data

# New function to scan remote workflow directory
def scan_remote_workflow_dir(github_api_instance, base_path):
    data = []
    try:
        print(f"[工作流管理器] 开始扫描云端目录: {base_path} in {GITHUB_REPO_OWNER}/{GITHUB_REPO_NAME}")
        
        # Check cache first for directory contents
        cache_key = f"dir_list:{base_path}"
        cached_contents = workflow_cache.get(cache_key)

        if cached_contents is not None:
            contents = cached_contents
        else:
            contents = github_api_instance.get_contents(base_path)
            if contents is not None:
                workflow_cache.set(cache_key, contents)


        if contents is None:
             print(f"[工作流管理器] 获取云端目录内容失败或目录不存在: {base_path}")
             return data
             
        # Separate files and directories
        files = [item for item in contents if item['type'] == 'file' and item['name'].endswith('.json')]
        dirs = [item for item in contents if item['type'] == 'dir']

        # Add files in the current directory (if any)
        if files:
             # For the root path '', name should be '/'
             folder_name = base_path if base_path != '' else '/'
             data.append({
                 "name": folder_name,
                 "files": [f['name'] for f in files]
             })
             print(f"[工作流管理器] 添加云端文件夹: {folder_name}")
             print(f"[工作流管理器] 发现云端文件: {[f['name'] for f in files]}")

        # Recursively scan subdirectories
        for d in dirs:
            sub_path = os.path.join(base_path, d['name']).replace('\\', '/') # Use / for github paths
            # Pass the github_api_instance recursively
            data.extend(scan_remote_workflow_dir(github_api_instance, sub_path))

    except Exception as e:
        print(f"[工作流管理器] 扫描云端工作流目录时出错: {e}")
    return data

# 新增: 获取用户专属工作流目录
def get_user_workflows(user_id):
    """获取用户可访问的工作流列表"""
    # 这里应该根据用户ID查询数据库或权限系统
    # 返回用户有权限访问的工作流列表
    # 目前为演示，返回一些模拟数据
    
    # 模拟数据: 用户专属工作流
    return [
        {
            "name": "我的工作流",
            "files": ["个人工作流1.json", "个人工作流2.json"]
        },
        {
            "name": "共享工作流",
            "files": ["团队共享工作流.json", "高级工作流.json"]
        }
    ]

async def handle_get_workflows(request):
    try:
        print("[工作流管理器] 收到获取本地工作流列表请求")
        print(f"[工作流管理器] 请求URL: {request.url}")
        print(f"[工作流管理器] 请求方法: {request.method}")
        
        structure = scan_workflow_dir(WORKFLOW_DIR)
        print(f"[工作流管理器] 本地工作流列表: {json.dumps(structure, ensure_ascii=False)}")
        
        response = web.json_response(structure)
        print(f"[工作流管理器] 本地响应状态: {response.status}")
        return response
    except Exception as e:
        print(f"[工作流管理器] 获取本地工作流列表时出错: {e}")
        return web.json_response({"error": str(e)}, status=500)

# New handler for remote workflow list
async def handle_get_remote_workflows(request):
    try:
        print("[工作流管理器] 收到获取云端工作流列表请求")
        if not GITHUB_TOKEN:
             return web.json_response({"error": "GitHub Token not configured"}, status=500)

        # 使用配置文件中的base_path
        remote_workflow_base_path = REMOTE_WORKFLOW_BASE_PATH
        structure = scan_remote_workflow_dir(github_api, remote_workflow_base_path) # Pass the instance

        # If the base path itself contains files, they won't be added under a folder named after the path itself
        # We need to handle the root of the remote_workflow_base_path if it contains files.
        base_contents = github_api.get_contents(remote_workflow_base_path)
        base_files = [item for item in base_contents if item['type'] == 'file' and item['name'].endswith('.json')]
        if base_files:
            structure.insert(0, {
                "name": remote_workflow_base_path if remote_workflow_base_path != '' else '/',
                "files": [f['name'] for f in base_files]
            })
            print(f"[工作流管理器] 添加云端根文件夹: {remote_workflow_base_path}")
            print(f"[工作流管理器] 发现云端根文件: {[f['name'] for f in base_files]}")

        print(f"[工作流管理器] 云端工作流列表: {json.dumps(structure, ensure_ascii=False)}")

        response = web.json_response(structure)
        print(f"[工作流管理器] 云端响应状态: {response.status}")
        return response
    except Exception as e:
        print(f"[工作流管理器] 获取云端工作流列表时出错: {e}")
        return web.json_response({"error": str(e)}, status=500)

async def handle_get_workflow(request):
    try:
        print("[工作流管理器] 收到获取本地工作流请求")
        rel_path = request.match_info['path']
        file_path = os.path.join(WORKFLOW_DIR, rel_path)
        print(f"[工作流管理器] 请求本地工作流文件: {file_path}")
        
        if not os.path.exists(file_path):
            print(f"[工作流管理器] 本地文件不存在: {file_path}")
            return web.json_response({"error": "File not found"}, status=404)
            
        with open(file_path, 'r', encoding='utf-8') as f:
            content = json.load(f)
            print(f"[工作流管理器] 成功加载本地工作流文件: {file_path}")
            return web.json_response(content)
    except Exception as e:
        print(f"[工作流管理器] 加载本地工作流文件时出错: {e}")
        return web.json_response({"error": str(e)}, status=500)

# New handler for remote workflow content
async def handle_get_remote_workflow(request):
    try:
        rel_path = request.match_info['path']
        print(f"[工作流管理器] 请求云端工作流文件: {rel_path}")

        if not GITHUB_TOKEN:
             return web.json_response({"error": "GitHub Token not configured"}, status=500)

        # Construct the full path within the GitHub repository
        # If rel_path is '/filename.json', we need to remove the leading slash
        github_path = rel_path.lstrip('/') # Remove leading slash if exists

        # Check cache first for file content
        cache_key = f"file_content:{github_path}"
        cached_content = workflow_cache.get(cache_key)

        if cached_content is not None:
             content = cached_content
        else:
            content = github_api.get_file_content(github_path)
            if content is not None:
                workflow_cache.set(cache_key, content)

        if content is None:
            print(f"[工作流管理器] 云端文件不存在或获取失败: {github_path}")
            return web.json_response({"error": "Remote file not found or access denied"}, status=404)

        # Parse the JSON content
        workflow_json = json.loads(content)

        print(f"[工作流管理器] 成功加载云端工作流文件: {github_path}")
        return web.json_response(workflow_json)
    except json.JSONDecodeError:
         print(f"[工作流管理器] 解析云端工作流 JSON 失败: {rel_path}")
         return web.json_response({"error": "Invalid JSON content"}, status=500)
    except Exception as e:
        print(f"[工作流管理器] 加载云端工作流文件时出错: {e}")
        return web.json_response({"error": str(e)}, status=500)

# New handler to clear remote workflow cache
async def handle_clear_remote_cache(request):
    try:
        print("[工作流管理器] 收到清除云端缓存请求")
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
    try:
        print("[工作流管理器] 收到获取用户工作流列表请求")
        
        # 从请求头获取token
        auth_header = request.headers.get('Authorization', '')
        token = auth_header.replace('Bearer ', '') if auth_header.startswith('Bearer ') else ''
        
        if not token:
            print("[工作流管理器] 未提供token")
            return web.json_response({"error": "Token required"}, status=401)
            
        # 验证token
        user_info = validate_user_token(token)
        if not user_info:
            print("[工作流管理器] token验证失败")
            return web.json_response({"error": "Invalid token"}, status=401)
            
        # 获取用户可访问的工作流列表
        workflows = get_user_workflows(user_info.get('id'))
        
        print(f"[工作流管理器] 成功获取用户工作流列表: {json.dumps(workflows, ensure_ascii=False)}")
        return web.json_response(workflows)
    except Exception as e:
        print(f"[工作流管理器] 获取用户工作流列表时出错: {e}")
        return web.json_response({"error": str(e)}, status=500)

# 3. 获取用户特定工作流
async def handle_get_user_workflow(request):
    try:
        print("[工作流管理器] 收到获取用户特定工作流请求")
        rel_path = request.match_info['path']
        
        # 从请求头获取token
        auth_header = request.headers.get('Authorization', '')
        token = auth_header.replace('Bearer ', '') if auth_header.startswith('Bearer ') else ''
        
        if not token:
            print("[工作流管理器] 未提供token")
            return web.json_response({"error": "Token required"}, status=401)
            
        # 验证token
        user_info = validate_user_token(token)
        if not user_info:
            print("[工作流管理器] token验证失败")
            return web.json_response({"error": "Invalid token"}, status=401)
            
        print(f"[工作流管理器] 请求用户工作流: {rel_path}")
        
        # 这里应该根据用户ID和路径查询数据库或权限系统
        # 检查用户是否有权限访问该工作流
        # 目前为演示，返回一个模拟的工作流
        
        mock_workflow = {
            "nodes": [
                {
                    "id": 1,
                    "type": "MockNode",
                    "name": "模拟节点",
                    "inputs": {},
                    "outputs": {}
                }
            ],
            "connections": [],
            "meta": {
                "name": rel_path.split('/')[-1].replace('.json', ''),
                "description": "这是一个模拟的用户工作流"
            }
        }
        
        print(f"[工作流管理器] 成功返回用户工作流: {rel_path}")
        return web.json_response(mock_workflow)
    except Exception as e:
        print(f"[工作流管理器] 获取用户工作流时出错: {e}")
        return web.json_response({"error": str(e)}, status=500)

# 新增: 处理Authing登录回调
async def handle_authing_callback(request):
    try:
        print("[工作流管理器] 收到Authing回调请求")
        # 这里处理回调，如果需要在服务端处理的话
        # 实际上大部分处理都在前端authing_callback.html中完成了
        return web.json_response({
            "status": "success",
            "message": "登录回调成功"
        })
    except Exception as e:
        print(f"[工作流管理器] 处理Authing回调时出错: {e}")
        return web.json_response({"error": str(e)}, status=500)

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

def setup(app):
    try:
        print("="*50)
        print("[工作流管理器] 开始设置工作流管理器...")
        print(f"[工作流管理器] 本地工作流目录: {WORKFLOW_DIR}")

        # 使用正确的方式注册路由
        app.router.add_get("/workflow_manager/list", handle_get_workflows)
        app.router.add_get("/workflow_manager/workflows/{path:.*}", handle_get_workflow)

        # Register new routes for remote workflows
        app.router.add_get("/workflow_manager/list_remote", handle_get_remote_workflows)
        app.router.add_get("/workflow_manager/workflows_remote/{path:.*}", handle_get_remote_workflow)

        # Register new route for clearing remote cache
        app.router.add_post("/workflow_manager/clear_remote_cache", handle_clear_remote_cache)
        
        # 注册用户相关API路由
        app.router.add_get("/workflow_manager/user/info", handle_get_user_info)
        app.router.add_get("/workflow_manager/user/workflows", handle_get_user_workflows)
        app.router.add_get("/workflow_manager/user/workflows/{path:.*}", handle_get_user_workflow)
        
        # 注册Authing回调处理路由
        app.router.add_get("/workflow_manager/auth/callback", handle_authing_callback)
        app.router.add_post("/workflow_manager/auth/callback", handle_authing_callback)
        
        # 注册登录API路由
        app.router.add_post("/workflow_manager/auth/login", handle_auth_login)

        print("[工作流管理器] 工作流管理器路由已注册")
        print("="*50)
    except Exception as e:
        print(f"[工作流管理器] 设置过程中出错: {e}")
        raise
