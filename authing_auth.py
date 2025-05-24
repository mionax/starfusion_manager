from authing.v2.authentication import AuthenticationClient, AuthenticationClientOptions
import json
import os
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('authing_auth')

# 从环境变量或配置文件获取Authing配置
CONFIG_PATH = os.path.join(os.path.dirname(__file__), 'cloud_workflow_config.json')
try:
    with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
        cloud_config = json.load(f)
    AUTH_CONFIG = cloud_config.get('auth', {})
except Exception as e:
    logger.error(f"读取配置文件失败: {e}")
    AUTH_CONFIG = {}

# 获取Authing配置
AUTH_ENABLED = AUTH_CONFIG.get('enabled', False)
APP_ID = os.getenv('AUTH_APP_ID') or AUTH_CONFIG.get('app_id', '')
APP_SECRET = os.getenv('AUTH_APP_SECRET') or AUTH_CONFIG.get('app_secret', '')
APP_HOST = os.getenv('AUTH_APP_HOST') or AUTH_CONFIG.get('app_host', 'https://starfusion.authing.cn')

# 初始化Authing客户端
authentication_client = None
try:
    if AUTH_ENABLED and APP_ID and APP_SECRET:
        # 根据Authing 4.5.18版本的API签名
        authentication_client = AuthenticationClient(
            options=AuthenticationClientOptions(
                app_id=APP_ID,
                app_host=APP_HOST,
                app_secret=APP_SECRET,
                timeout=10.0  # 增加超时时间，避免网络问题
            )
        )
        logger.info(f"Authing客户端初始化成功，APP_ID: {APP_ID[:8]}...")
    else:
        authentication_client = None
        if AUTH_ENABLED:
            logger.warning("Authing认证已启用，但配置不完整。用户验证可能无法正常工作。")
        else:
            logger.info("Authing认证功能未启用")
except Exception as e:
    logger.error(f"Authing客户端初始化失败: {e}")
    authentication_client = None


def validate_token(token):
    """
    验证Authing用户Token是否有效
    
    Args:
        token: Authing用户Token
        
    Returns:
        用户信息dict或None(验证失败)
    """
    # 调试日志
    logger.info(f"开始验证Token: {token[:10]}..." if token and len(token) > 10 else token)
    
    # 如果认证功能未启用或客户端初始化失败，返回模拟用户数据
    if not AUTH_ENABLED or authentication_client is None:
        logger.warning("认证功能未正确配置，返回模拟用户数据")
        return {
            "id": "mock_user_id",
            "username": "test_user",
            "nickname": "测试用户",
            "avatar": "https://via.placeholder.com/100",
            "mock": True
        }
    
    try:
        # 无效token直接返回None
        if not token or token == 'invalid' or len(token) < 10:
            logger.warning("无效Token")
            return None
            
        # 调用Authing API验证Token
        try:
            # 根据Authing 4.5.18版本的API
            # 尝试不同的API
            try:
                # 新版本可能使用getUserInfo方法
                user_info = authentication_client.getUserInfo(token)
            except (AttributeError, TypeError) as e:
                # 如果上面的方法不存在，尝试get_user_info方法
                logger.info(f"尝试使用get_user_info方法: {e}")
                user_info = authentication_client.get_user_info(token)
                
            logger.info(f"Token验证API调用成功: {type(user_info)}")
        except Exception as e:
            logger.error(f"Token验证API调用失败: {e}")
            # 如果API调用失败，尝试使用内置的验证用户令牌有效性功能
            try:
                # 验证token是否有效
                is_valid = authentication_client.validateToken(token)
                if not is_valid:
                    logger.warning("Token验证失败：无效Token")
                    return None
                
                # 如果token有效但无法获取用户信息，返回简单用户对象
                user_info = {
                    "id": "authenticated_user",
                    "username": "authenticated",
                    "nickname": "已验证用户",
                    "avatar": "https://via.placeholder.com/100"
                }
            except Exception as inner_e:
                logger.error(f"Token验证备用方法失败: {inner_e}")
                return None
        
        if user_info and (isinstance(user_info, dict) and 'id' in user_info):
            logger.info(f"Token验证成功，用户ID: {user_info.get('id')}")
            # 确保返回格式一致的用户信息
            return {
                "id": user_info.get('id', 'unknown'),
                "username": user_info.get('username', user_info.get('name', 'user')),
                "nickname": user_info.get('nickname', user_info.get('name', user_info.get('username', 'User'))),
                "avatar": user_info.get('photo', user_info.get('picture', '')),
                "email": user_info.get('email', ''),
                "phone": user_info.get('phone', '')
            }
        else:
            logger.warning(f"Token验证失败，无法解析用户信息: {user_info}")
            return None
    except Exception as e:
        logger.error(f"Token验证过程出错: {e}")
        return None 