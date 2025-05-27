import json
import logging
from aiohttp import web
from .auth_service import validate_token, login_user, register_user, get_user_custom_data
from .utils import WorkflowCache
from .auth_manager import AuthManager

# 设置日志
logger = logging.getLogger('api_handlers')

# 缓存实例，在workflow_manager.py中初始化
workflow_cache = None

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
        logger.warning("未提供token")
        return None, web.json_response({"error": "Token required"}, status=401)
        
    # 验证token
    user_info = validate_token(token)
    if not user_info:
        logger.warning("token验证失败")
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
        logger.info(f"收到获取{source_name}工作流列表请求")
        
        structure = data_source.scan_directory()
        logger.info(f"{source_name}工作流列表: {json.dumps(structure, ensure_ascii=False)}")
        
        response = web.json_response(structure)
        logger.info(f"{source_name}响应状态: {response.status}")
        return response
    except Exception as e:
        logger.error(f"获取{source_name}工作流列表时出错: {e}")
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
        logger.info(f"收到获取{source_name}工作流请求: {rel_path}")
        
        content, error = data_source.get_workflow(rel_path)
        if error:
            status = 404 if "not found" in error.lower() else 500
            return web.json_response({"error": error}, status=status)
        
        logger.info(f"成功加载{source_name}工作流: {rel_path}")
        return web.json_response(content)
    except Exception as e:
        logger.error(f"加载{source_name}工作流时出错: {e}")
        return web.json_response({"error": str(e)}, status=500)

# 本地工作流处理函数
async def handle_get_workflows(request):
    """获取本地工作流列表"""
    from .workflow_manager import local_source
    return await handle_get_workflows_generic(request, local_source, "本地")

async def handle_get_workflow(request):
    """获取本地工作流文件"""
    from .workflow_manager import local_source
    return await handle_get_workflow_generic(request, local_source, "本地")

# 云端工作流处理函数
async def handle_get_remote_workflows(request):
    """获取云端工作流列表"""
    try:
        logger.info("收到获取云端工作流列表请求")
        
        # 验证用户Token
        user_info, error_response = await get_and_validate_token(request)
        if error_response:
            return error_response
            
        from .workflow_manager import github_source, GITHUB_TOKEN
        if not GITHUB_TOKEN:
            return web.json_response({"error": "GitHub Token not configured"}, status=500)
        
        return await handle_get_workflows_generic(request, github_source, "云端")
    except Exception as e:
        logger.error(f"获取云端工作流列表时出错: {e}")
        return web.json_response({"error": str(e)}, status=500)

async def handle_get_remote_workflow(request):
    """获取云端工作流文件"""
    try:
        logger.info("收到获取云端工作流请求")
        
        # 验证用户Token
        user_info, error_response = await get_and_validate_token(request)
        if error_response:
            return error_response
        
        from .workflow_manager import github_source, GITHUB_TOKEN
        if not GITHUB_TOKEN:
            return web.json_response({"error": "GitHub Token not configured"}, status=500)
        
        return await handle_get_workflow_generic(request, github_source, "云端")
    except Exception as e:
        logger.error(f"获取云端工作流时出错: {e}")
        return web.json_response({"error": str(e)}, status=500)

# 清除缓存处理函数
async def handle_clear_remote_cache(request):
    """清除远程缓存"""
    try:
        logger.info("收到清除云端缓存请求")
        
        # 验证用户Token
        user_info, error_response = await get_and_validate_token(request)
        if error_response:
            return error_response
            
        global workflow_cache
        if workflow_cache:
            workflow_cache.clear()
            logger.info("云端缓存已清除")
        return web.json_response({"status": "success", "message": "云端缓存已清除"})
    except Exception as e:
        logger.error(f"清除云端缓存时出错: {e}")
        return web.json_response({"error": str(e)}, status=500)

# 用户相关API处理函数
async def handle_get_user_info(request):
    """获取用户信息"""
    try:
        logger.info("收到获取用户信息请求")
        
        # 从请求头获取token
        auth_header = request.headers.get('Authorization', '')
        token = auth_header.replace('Bearer ', '') if auth_header.startswith('Bearer ') else ''
        
        # 如果没有提供token，则返回匿名用户状态
        if not token:
            logger.info("未提供token，返回匿名用户状态")
            return web.json_response({
                "authenticated": False,
                "message": "未登录状态"
            })
            
        # 验证token
        user_info = validate_token(token)
        if not user_info:
            logger.warning("token验证失败")
            return web.json_response({"error": "Invalid token"}, status=401)
            
        # 添加认证状态到返回结果
        user_info['authenticated'] = True
        user_info['token'] = token
        
        logger.info(f"成功获取用户信息: {json.dumps(user_info, ensure_ascii=False)}")
        return web.json_response(user_info)
    except Exception as e:
        logger.error(f"获取用户信息时出错: {e}")
        return web.json_response({"error": str(e)}, status=500)

# 用户工作流相关处理函数
async def handle_get_user_workflows(request):
    """获取用户工作流列表"""
    try:
        logger.info("收到获取用户工作流列表请求")
        
        # 验证用户Token
        user_info, error_response = await get_and_validate_token(request)
        if error_response:
            return error_response
        
        # 获取用户ID和token
        user_id = user_info.get('id')
        auth_header = request.headers.get('Authorization', '')
        token = auth_header.replace('Bearer ', '') if auth_header.startswith('Bearer ') else ''
        
        # 获取用户工作流列表
        from .workflow_manager import get_user_workflows
        user_workflows = get_user_workflows(user_id, token)
        
        logger.info(f"用户工作流列表: {json.dumps(user_workflows, ensure_ascii=False)}")
        return web.json_response(user_workflows)
    except Exception as e:
        logger.error(f"获取用户工作流列表时出错: {e}")
        return web.json_response({"error": str(e)}, status=500)

async def handle_get_user_workflow(request):
    """获取用户特定工作流"""
    try:
        logger.info("收到获取用户特定工作流请求")
        rel_path = request.match_info['path']
        
        # 验证用户Token
        user_info, error_response = await get_and_validate_token(request)
        if error_response:
            return error_response
        
        # 获取用户ID
        user_id = user_info.get('id')
        
        logger.info(f"用户 {user_id} 请求工作流: {rel_path}")
        
        from .workflow_manager import github_api, REMOTE_WORKFLOW_BASE_PATH, GITHUB_TOKEN
        # 检查GitHub Token是否配置
        if not GITHUB_TOKEN:
            return web.json_response({"error": "GitHub Token not configured"}, status=500)
        
        # 创建用户工作流数据源
        from .data_sources import GitHubWorkflowSource
        user_source = GitHubWorkflowSource(github_api, "", workflow_cache)
        
        # 构建在GitHub仓库中的完整路径 - 首先尝试用户专属目录
        user_path = f"{REMOTE_WORKFLOW_BASE_PATH}/user_workflows/{rel_path}"
        
        # 尝试获取用户专属工作流
        content, error = user_source.get_workflow(user_path)
        
        # 如果找不到，尝试从公共目录获取
        if error and "not found" in error.lower():
            logger.info(f"用户工作流不存在，尝试从公共目录获取: {rel_path}")
            public_path = f"{REMOTE_WORKFLOW_BASE_PATH}/{rel_path}"
            content, error = user_source.get_workflow(public_path)
        
        # 如果仍然有错误，返回错误响应
        if error:
            status = 404 if "not found" in error.lower() else 500
            return web.json_response({"error": error}, status=status)
        
        logger.info(f"成功获取用户工作流: {rel_path}")
        return web.json_response(content)
    except Exception as e:
        logger.error(f"获取用户工作流时出错: {e}")
        return web.json_response({"error": str(e)}, status=500)

# 认证相关处理函数
async def handle_auth_login(request):
    """处理用户登录请求"""
    try:
        logger.info("收到用户登录请求")
        # 获取用户名和密码
        data = await request.json()
        username = data.get('username')
        password = data.get('password')
        
        if not username or not password:
            return web.json_response({
                "error": "Missing username or password",
                "message": "请提供用户名和密码"
            }, status=400)
        
        # 使用认证服务登录
        user, error = login_user(username, password)
        if error:
            logger.warning(f"登录失败: {error}")
            return web.json_response({
                "error": "Login failed",
                "message": f"登录失败: {error}"
            }, status=401)
        
        # 返回登录结果
        return web.json_response(user)
    except Exception as e:
        logger.error(f"处理登录请求时出错: {e}")
        return web.json_response({
            "error": "Internal server error",
            "message": "服务器内部错误，请稍后重试"
        }, status=500)

async def handle_auth_register(request):
    """处理用户注册请求"""
    try:
        logger.info("收到用户注册请求")
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
        
        # 使用认证服务注册
        user, error = register_user(username, password)
        if error:
            # 用户名已存在的特殊处理
            if "已存在" in error:
                logger.warning(f"注册失败，用户名已存在: {username}")
                return web.json_response({
                    "error": "Username exists",
                    "message": "用户名已存在，请选择其他用户名"
                }, status=409)
            
            logger.warning(f"注册失败: {error}")
            return web.json_response({
                "error": "Registration failed",
                "message": f"注册失败: {error}"
            }, status=400)
        
        # 返回注册结果
        return web.json_response(user)
    except Exception as e:
        logger.error(f"处理注册请求时出错: {e}")
        return web.json_response({
            "error": "Internal server error",
            "message": "服务器内部错误，请稍后重试"
        }, status=500)

# 授权管理相关处理函数
async def handle_get_authorized_workflows(request):
    """获取用户授权的工作流列表"""
    try:
        logger.info("收到获取用户授权工作流列表请求")
        
        # 验证用户Token
        user_info, error_response = await get_and_validate_token(request)
        if error_response:
            return error_response
            
        # 获取token
        auth_header = request.headers.get('Authorization', '')
        token = auth_header.replace('Bearer ', '') if auth_header.startswith('Bearer ') else ''
        
        # 获取用户自定义数据（包含授权信息）
        udf_data = get_user_custom_data(token)
        if not udf_data:
            logger.warning("获取用户授权数据失败")
            return web.json_response({
                "error": "Failed to get authorization data",
                "message": "获取授权数据失败"
            }, status=500)
            
        # 创建授权管理器
        auth_manager = AuthManager.from_authing_udf(udf_data)
        
        # 获取授权工作流
        authorized_workflows = auth_manager.get_authorized_workflows()
        
        # 获取工作流ID列表
        workflow_list = list(authorized_workflows.keys())
        
        # 添加详细授权信息
        result = {
            "workflow_list": workflow_list,
            "workflow_details": authorized_workflows
        }
        
        logger.info(f"获取到用户授权工作流: {len(workflow_list)}个")
        return web.json_response(result)
    except Exception as e:
        logger.error(f"获取授权工作流列表时出错: {e}")
        return web.json_response({"error": str(e)}, status=500)
        
async def handle_check_workflow_auth(request):
    """检查特定工作流的授权状态"""
    try:
        logger.info("收到检查工作流授权状态请求")
        
        # 验证用户Token
        user_info, error_response = await get_and_validate_token(request)
        if error_response:
            return error_response
            
        # 获取请求参数
        data = await request.json()
        workflow_id = data.get('workflow_id')
        
        if not workflow_id:
            return web.json_response({
                "error": "Missing workflow_id",
                "message": "请提供工作流ID"
            }, status=400)
            
        # 获取token
        auth_header = request.headers.get('Authorization', '')
        token = auth_header.replace('Bearer ', '') if auth_header.startswith('Bearer ') else ''
        
        # 获取用户自定义数据
        udf_data = get_user_custom_data(token)
        
        # 创建授权管理器
        auth_manager = AuthManager.from_authing_udf(udf_data)
        
        # 检查授权状态
        is_authorized = auth_manager.is_workflow_authorized(workflow_id)
        
        # 获取过期时间
        expiry = auth_manager.get_workflow_expiry(workflow_id)
        
        result = {
            "workflow_id": workflow_id,
            "authorized": is_authorized,
            "expires_at": expiry,
            "permanent": is_authorized and expiry is None
        }
        
        logger.info(f"工作流 {workflow_id} 授权状态: {is_authorized}")
        return web.json_response(result)
    except Exception as e:
        logger.error(f"检查工作流授权状态时出错: {e}")
        return web.json_response({"error": str(e)}, status=500) 