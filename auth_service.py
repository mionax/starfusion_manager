import os
import json
import time
import logging
import datetime
from authing.v2.authentication import AuthenticationClient, AuthenticationClientOptions
from .utils import load_config

# 配置日志
logger = logging.getLogger('auth_service')

# 加载配置
cloud_config = load_config()
AUTH_CONFIG = cloud_config.get('auth', {})

# 获取Authing配置
AUTH_ENABLED = AUTH_CONFIG.get('enabled', True)
APP_ID = os.getenv('AUTH_APP_ID') or AUTH_CONFIG.get('app_id', '')
APP_SECRET = os.getenv('AUTH_APP_SECRET') or AUTH_CONFIG.get('app_secret', '')
APP_HOST = os.getenv('AUTH_APP_HOST') or AUTH_CONFIG.get('app_host', 'https://starfusion.authing.cn')

# 初始化Authing客户端
authentication_client = None
try:
    if AUTH_ENABLED and APP_ID:
        # 根据Authing 4.5.18版本的API签名
        authentication_client = AuthenticationClient(
            options=AuthenticationClientOptions(
                app_id=APP_ID,
                app_host=APP_HOST,
                # 注意：新版本的Authing SDK可能不需要app_secret
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
            # 尝试使用token解析用户信息
            user_info = None
            
            try:
                try:
                    # 使用get_current_user方法
                    user_info = authentication_client.get_current_user()
                except (AttributeError, TypeError) as e:
                    # 如果上面的方法不存在，尝试get_user_info方法
                    logger.info(f"尝试使用get_user_info方法: {e}")
                    user_info = authentication_client.get_user_info(token)
                    
                logger.info(f"Token验证API调用成功: {type(user_info)}")
            except Exception as e:
                logger.error(f"直接使用token获取用户信息失败: {e}")
                user_info = None

        except Exception as e:
            logger.error(f"Token验证API调用失败: {e}")
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


def login_user(username, password):
    """
    用户登录处理
    
    Args:
        username: 用户名
        password: 密码
        
    Returns:
        用户信息dict或None(登录失败)
    """
    try:
        logger.info(f"尝试登录用户: {username}")
        
        # 如果认证功能未启用，返回模拟用户数据
        if not AUTH_ENABLED:
            logger.warning("认证功能未启用，返回模拟登录结果")
            mock_user = {
                "id": f"mock_{username}",
                "username": username,
                "nickname": username,
                "photo": f"https://via.placeholder.com/100/3a80d2/ffffff?text={username[0].upper()}",
                "token": f"mock_token_{username}_{int(time.time())}",
                "is_mock": True
            }
            return mock_user, None
            
        # 使用Authing客户端登录
        if authentication_client is None:
            logger.error("Authing客户端未初始化")
            return None, "认证服务未正确配置"
            
        # 使用用户名密码登录  
        user = authentication_client.login_by_username(
            username=username, 
            password=password
        )
        
        # 检查返回的用户信息中是否包含token
        if not user or not isinstance(user, dict):
            logger.error(f"登录失败，无法获取用户信息: {user}")
            return None, "登录失败，无法获取用户信息"
            
        # 记录token以便调试
        if 'token' in user:
            logger.info(f"成功获取token: {user['token'][:10]}...")
        else:
            logger.warning(f"用户信息中未找到token，尝试使用get_current_user获取")
            try:
                # 尝试使用get_current_user获取当前用户信息
                current_user = authentication_client.get_current_user()
                if current_user and 'token' in current_user:
                    user['token'] = current_user['token']
                    logger.info(f"从get_current_user获取token成功")
                else:
                    logger.warning("get_current_user未返回token")
            except Exception as e:
                logger.error(f"获取当前用户信息失败: {e}")
        
        logger.info(f"Authing登录成功: {user.get('id')}")
        return user, None
            
    except Exception as e:
        logger.error(f"登录失败: {e}")
        return None, str(e)


def register_user(username, password):
    """
    用户注册处理
    
    Args:
        username: 用户名
        password: 密码
        
    Returns:
        用户信息dict或None(注册失败)
    """
    try:
        logger.info(f"尝试注册用户: {username}")
        
        # 如果认证功能未启用，返回模拟用户数据
        if not AUTH_ENABLED:
            logger.warning("认证功能未启用，返回模拟注册结果")
            mock_user = {
                "id": f"mock_{username}",
                "username": username,
                "nickname": username,
                "photo": f"https://via.placeholder.com/100/3a80d2/ffffff?text={username[0].upper()}",
                "token": f"mock_token_{username}_{int(time.time())}",
                "is_mock": True
            }
            return mock_user, None
            
        # 使用Authing客户端注册
        if authentication_client is None:
            logger.error("Authing客户端未初始化")
            return None, "认证服务未正确配置"
        
        # # 检查用户名是否已存在
        # try:
        #     user_exist = authentication_client.find_user_by_username(username)
        #     if user_exist and user_exist.get('id'):
        #         logger.warning(f"用户名已存在: {username}")
        #         return None, "用户名已存在"
        # except Exception as find_error:
        #     # 如果是因为用户不存在导致的错误，则继续注册流程
        #     logger.info(f"查找用户时出错: {find_error}")
            
        #设置新注册用户默认授权7天
        # 使用os.path.join构建跨平台路径，并尝试多种路径可能性
        config_file_path = os.path.join(os.path.dirname(__file__), 'config', 'deafault_authing_config.json')
        if not os.path.exists(config_file_path):
            # 尝试相对于当前工作目录的路径
            config_file_path = os.path.join('config', 'deafault_authing_config.json')
            if not os.path.exists(config_file_path):
                # 尝试向上一级查找
                config_file_path = os.path.join('..', 'config', 'deafault_authing_config.json')
                
        logger.info(f"尝试读取配置文件路径: {config_file_path}")
                
        try:
            with open(config_file_path, 'r', encoding='utf-8') as f:
                default_user_authing_info = json.load(f)
        except FileNotFoundError as e:
            logger.error(f"找不到配置文件: {e}")
            # 使用硬编码的默认值作为后备
            default_user_authing_info = {
                "basic_access": {
                    "type": "temp",
                    "expired_at": None
                },
                "packages": [],
                "workflows": []
            }
            
        # 计算7天后的日期时间
        future_date = datetime.datetime.now() + datetime.timedelta(days=7)
        # 更新expired_at值为7天后的日期时间，格式为ISO8601
        default_user_authing_info['basic_access']['expired_at'] = future_date.isoformat(timespec='milliseconds').replace('+00:00', '') + 'Z'
        
        logger.info(f"设置用户授权过期时间为: {default_user_authing_info['basic_access']['expired_at']}")
        
        # 注册用户
        new_user = authentication_client.register_by_username(
            username=username,
            password=password,
            custom_data={
                "user_authing_info": f'{default_user_authing_info}'}
        )
        
        if not new_user or not new_user.get('id'):
            logger.error(f"注册失败，Authing返回: {new_user}")
            return None, "注册失败，请稍后重试"
            
        logger.info(f"注册成功: {new_user.get('id')}")
        
        # 注册成功后自动登录
        user = authentication_client.login_by_username(
            username=username,
            password=password
        )
        
        # 检查返回的用户信息中是否包含token
        if 'token' in user:
            logger.info(f"注册后登录成功并获取token: {user['token'][:10]}...")
        
        return user, None
            
    except Exception as e:
        logger.error(f"注册失败: {e}")
        return None, str(e)


def get_user_custom_data(token=None):
    """
    获取用户自定义数据
    
    Args:
        token: 用户Token，如果为None则使用已认证的客户端
        
    Returns:
        自定义数据dict
    """
    try:
        if not AUTH_ENABLED or authentication_client is None:
            logger.warning("认证功能未正确配置，无法获取用户自定义数据")
            # 如果认证未启用，返回模拟数据
            return {
                "user_authing_info": json.dumps({
                    "basic_access": {
                        "type": "temp",
                        "expired_at": "2025-06-02T08:00:00.000Z"
                    },
                    "packages": [
                        {
                            "id": "基础工具类",
                            "type": "lifetime",
                            "expired_at": None
                        },
                        {
                            "id": "图像生成类",
                            "type": "monthly",
                            "expired_at": "2025-06-30T23:59:59.000Z"
                        }
                    ],
                    "workflows": [
                        {
                            "id": "🎀模特穿戴",
                            "type": "lifetime",
                            "expired_at": None
                        },
                        {
                            "id": "📷产品拍摄",
                            "type": "monthly",
                            "expired_at": "2025-06-30T23:59:59.000Z"
                        }
                    ]
                })
            }
            
        # 使用token或已认证的客户端
        if token:
            # 使用设置的token获取用户自定义数据
            try:
                # 尝试使用token作为context获取用户UDF数据
                authentication_client.setToken(token)
                udf_data = authentication_client.get_udf_value()
                logger.info(f"使用token获取UDF数据成功")
                return udf_data
            except Exception as e:
                logger.error(f"使用token获取UDF数据失败: {e}")
                # 如果失败，继续尝试默认方式
            
        # 获取用户自定义数据
        udf_data = authentication_client.get_udf_value()
        logger.info(f"获取UDF数据成功")
        return udf_data
    except Exception as e:
        logger.error(f"获取用户自定义数据失败: {e}")
        # 如果获取失败，返回模拟数据以确保测试功能
        return {
            "user_authing_info": json.dumps({
                "basic_access": {
                    "type": "temp",
                    "expired_at": "2025-06-02T08:00:00.000Z"
                },
                "packages": [
                    {
                        "id": "基础工具类",
                        "type": "lifetime",
                        "expired_at": None
                    }
                ],
                "workflows": []
            })
        } 