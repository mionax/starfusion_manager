import json
import os
import datetime
import logging
from typing import List, Dict, Any, Optional
try:
    import dateutil.parser
except ImportError:
    logger = logging.getLogger('auth_manager')
    logger.warning("未找到dateutil库，将无法解析复杂日期格式。请安装: pip install python-dateutil")

# 尝试使用相对导入（当作为包导入时）
try:
    from auth_service import get_user_custom_data
except ImportError:
    # 如果作为独立脚本运行，则使用绝对导入
    try:
        from .auth_service import get_user_custom_data
    except ImportError:
        # 如果两种方式都不行，提供一个模拟函数
        def get_user_custom_data(token=None):
            logging.warning("使用模拟的get_user_custom_data函数")
            return {
                "user_authing_info": json.dumps({
                    "basic_access": {"type": "temp", "expired_at": "2025-06-02T08:00:00.000Z"},
                    "packages": [{"id": "基础工具类", "type": "lifetime", "expired_at": None}],
                    "workflows": []
                })
            }

# 设置日志
logger = logging.getLogger('auth_manager')

class AuthManager:
    def __init__(self, package_config_path: str = 'config/package.json'):
        """
        初始化认证管理器
        
        Args:
            package_config_path: 包配置文件路径
        """
        # 尝试多个可能的包配置路径
        self.package_config_path = package_config_path
        self.package_config = None
        
        # 从auth_service获取用户数据并解析
        udf_data = get_user_custom_data()
        self.user_data = self._parse_user_data(udf_data)
        
        # 加载包配置
        self._load_package_config()
    
    def _parse_user_data(self, udf_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        解析从get_user_custom_data获取的用户数据
        
        Args:
            udf_data: 用户自定义字段数据
            
        Returns:
            Dict[str, Any]: 解析后的用户数据
        """
        try:
            if not udf_data or 'user_authing_info' not in udf_data:
                logger.warning("UDF数据为空或未找到user_authing_info字段")
                return {"basic_access": {}, "packages": [], "workflows": []}
                
            # 将JSON字符串解析为Python对象
            user_authing_info_str = udf_data['user_authing_info']
            logger.debug(f"原始user_authing_info: {user_authing_info_str[:100]}")
            
            # 检查是否是Python字典字符串格式(使用单引号)
            if isinstance(user_authing_info_str, str) and user_authing_info_str.startswith("'"):
                logger.info("检测到Python字典字符串格式，使用ast模块解析")
                import ast
                try:
                    user_authing_info = ast.literal_eval(user_authing_info_str)
                except (SyntaxError, ValueError) as e:
                    logger.error(f"解析Python字典字符串失败: {e}")
                    return {"basic_access": {}, "packages": [], "workflows": []}
            else:
                # 尝试标准JSON解析
                try:
                    user_authing_info = json.loads(user_authing_info_str)
                except json.JSONDecodeError:
                    # 如果标准解析失败，尝试处理单引号格式（旧数据可能是Python字典字符串）
                    logger.warning("标准JSON解析失败，尝试处理单引号格式")
                    import ast
                    try:
                        # 使用ast.literal_eval安全地解析Python字面量
                        user_authing_info = ast.literal_eval(user_authing_info_str)
                    except (SyntaxError, ValueError) as e:
                        logger.error(f"解析用户数据失败: {e}")
                        return {"basic_access": {}, "packages": [], "workflows": []}
            
            logger.info(f"成功解析user_authing_info，包含字段: {list(user_authing_info.keys())}")
            
            # 创建格式化数据结构
            return {
                'basic_access': user_authing_info.get('basic_access', {}),
                'packages': user_authing_info.get('packages', []),
                'workflows': user_authing_info.get('workflows', [])
            }
        except Exception as e:
            logger.error(f"解析用户数据出错: {e}")
            return {"basic_access": {}, "packages": [], "workflows": []}
    
    def _load_package_config(self) -> None:
        """加载包配置数据"""
        try:
            # 尝试多种可能的配置文件路径
            possible_config_paths = [
                self.package_config_path,  # 使用传入的路径
                os.path.join(os.path.dirname(__file__), self.package_config_path),  # 相对于当前文件
                os.path.join(os.path.dirname(__file__), '..', 'config', 'package.json'),  # 上一级目录
                os.path.abspath(os.path.join('custom_nodes', 'starfusion_manager', 'config', 'package.json'))  # 可能的全局路径
            ]
            
            config_file_path = None
            for path in possible_config_paths:
                logger.debug(f"尝试查找包配置文件: {path}")
                if os.path.exists(path):
                    config_file_path = path
                    break
            
            if config_file_path:
                with open(config_file_path, 'r', encoding='utf-8') as f:
                    self.package_config = json.load(f)
                logger.info(f"成功加载包配置文件: {config_file_path}")
            else:
                logger.warning(f"包配置文件不存在: {self.package_config_path}")
                self.package_config = {}
        except Exception as e:
            logger.error(f"加载包配置出错: {e}")
            self.package_config = {}
    
    def _is_authorization_valid(self, auth_type: str, expired_at: Optional[str]) -> bool:
        """
        检查授权是否有效
        
        Args:
            auth_type: 授权类型 ('lifetime', 'monthly', 'temp' 等)
            expired_at: 过期时间字符串
            
        Returns:
            bool: 授权是否有效
        """
        # 永久授权
        if auth_type == "lifetime":
            logger.debug(f"授权类型为永久(lifetime)，有效")
            return True
        
        # 跟踪我们正在检查什么类型的授权，便于调试
        logger.debug(f"检查授权类型: {auth_type}, 过期时间: {expired_at}")
        
        # 处理临时授权(temp)和其他类型的授权
        if auth_type in ["temp", "monthly", "yearly"] and expired_at:
            try:
                # 将字符串转换为datetime对象，处理不同的时间格式
                try:
                    # 尝试ISO格式解析
                    expiry_date = datetime.datetime.fromisoformat(expired_at.replace('Z', '+00:00'))
                except ValueError:
                    # 尝试其他常见格式
                    import dateutil.parser
                    expiry_date = dateutil.parser.parse(expired_at)
                
                # 获取当前UTC时间进行比较
                now = datetime.datetime.now(datetime.timezone.utc)
                
                # 检查是否已过期
                is_valid = now < expiry_date
                
                logger.info(f"授权类型: {auth_type}, 过期时间: {expired_at}, 当前时间: {now.isoformat()}, 是否有效: {is_valid}")
                return is_valid
            except Exception as e:
                logger.error(f"解析过期时间出错: {e}, 原始值: {expired_at}")
                return False
        
        logger.warning(f"授权无效: 类型={auth_type}, 过期时间={expired_at}")
        return False
    
    def _get_package_workflows(self, package_id: str) -> List[str]:
        """
        获取指定包中的所有工作流
        
        Args:
            package_id: 包ID
            
        Returns:
            List[str]: 工作流ID列表
        """
        if self.package_config and package_id in self.package_config:
            return self.package_config[package_id].get("workflows", [])
        return []
    
    def get_authorized_workflows(self) -> Dict[str, Any]:
        """
        获取用户被授权的所有工作流及其授权信息
        
        Returns:
            Dict[str, Any]: 工作流ID到授权信息的映射
        """
        # 确保user_data不为None
        if not self.user_data:
            logger.warning("用户数据为空，尝试重新获取")
            # 尝试重新获取用户数据
            udf_data = get_user_custom_data()
            self.user_data = self._parse_user_data(udf_data)
            
            # 如果仍然为空，则返回空字典
            if not self.user_data:
                logger.error("无法获取用户数据，无法计算授权工作流")
                return {}
        
        # 检查基本访问权限
        basic_access = self.user_data.get("basic_access", {})
        basic_access_valid = self._is_authorization_valid(
            basic_access.get("type", ""), 
            basic_access.get("expired_at")
        )
        
        if not basic_access_valid:
            logger.warning("基本访问权限已过期或无效")
            return {}
        
        # 收集授权工作流
        authorized_workflows = {}
        
        # 添加通过包授权的工作流
        for package in self.user_data.get("packages", []):
            package_id = package.get("id")
            if not package_id:
                continue
                
            # 检查包授权是否有效
            if not self._is_authorization_valid(package.get("type", ""), package.get("expired_at")):
                logger.info(f"包授权已过期: {package_id}")
                continue
                
            # 获取包中的工作流
            workflows = self._get_package_workflows(package_id)
            for workflow in workflows:
                authorized_workflows[workflow] = {
                    "source": "package",
                    "package_id": package_id,
                    "type": package.get("type"),
                    "expired_at": package.get("expired_at")
                }
            
            logger.info(f"通过包 '{package_id}' 授权的工作流: {len(workflows)}个")
        
        # 添加直接授权的工作流
        for workflow in self.user_data.get("workflows", []):
            workflow_id = workflow.get("id")
            if not workflow_id:
                continue
                
            # 检查工作流授权是否有效
            if not self._is_authorization_valid(workflow.get("type", ""), workflow.get("expired_at")):
                logger.info(f"工作流授权已过期: {workflow_id}")
                continue
                
            # 如果工作流已通过包授权，则使用更优的授权类型
            if workflow_id in authorized_workflows:
                # 如果直接授权是永久的，但包授权不是，则使用直接授权
                if workflow.get("type") == "lifetime" and authorized_workflows[workflow_id]["type"] != "lifetime":
                    authorized_workflows[workflow_id] = {
                        "source": "direct",
                        "type": workflow.get("type"),
                        "expired_at": workflow.get("expired_at")
                    }
            else:
                authorized_workflows[workflow_id] = {
                    "source": "direct",
                    "type": workflow.get("type"),
                    "expired_at": workflow.get("expired_at")
                }
            
            logger.info(f"直接授权的工作流: {workflow_id}")
        
        logger.info(f"用户总授权工作流数: {len(authorized_workflows)}")
        return authorized_workflows
    
    def get_workflow_list(self) -> List[str]:
        """
        获取用户可访问的工作流ID列表
        
        Returns:
            List[str]: 工作流ID列表
        """
        return list(self.get_authorized_workflows().keys())
    
    def is_workflow_authorized(self, workflow_id: str) -> bool:
        """
        检查用户是否有权限访问指定工作流
        
        Args:
            workflow_id: 工作流ID
            
        Returns:
            bool: 是否有权限
        """
        return workflow_id in self.get_authorized_workflows()
    
    def get_workflow_expiry(self, workflow_id: str) -> Optional[str]:
        """
        获取工作流的过期时间
        
        Args:
            workflow_id: 工作流ID
            
        Returns:
            Optional[str]: 过期时间，如果是永久授权则返回None
        """
        workflows = self.get_authorized_workflows()
        if workflow_id in workflows:
            if workflows[workflow_id]["type"] == "lifetime":
                return None
            return workflows[workflow_id].get("expired_at")
        return None
    
    def load_user_udf_data(self, udf_data: Dict[str, Any]) -> None:
        """
        直接加载用户UDF数据（从Authing API获取）
        
        Args:
            udf_data: 用户自定义字段数据
        """
        # 直接使用已实现的解析方法处理UDF数据
        self.user_data = self._parse_user_data(udf_data)
        if self.user_data:
            logger.info("成功从UDF数据加载用户授权信息")
    
    def save_user_udf_data(self, target_path: str = 'user_udf.json') -> None:
        """
        保存用户UDF数据到文件
        
        Args:
            target_path: 目标文件路径，默认为'user_udf.json'
        """
        if not self.user_data:
            logger.warning("没有用户数据可保存")
            return
        
        try:
            with open(target_path, 'w', encoding='utf-8') as f:
                json.dump(self.user_data, f, ensure_ascii=False, indent=4)
            logger.info(f"用户授权数据保存成功: {target_path}")
        except Exception as e:
            logger.error(f"保存用户授权数据出错: {e}")
            
    @staticmethod
    def from_authing_udf(udf_data: Dict[str, Any], package_config_path: str = 'config/package.json') -> 'AuthManager':
        """
        从Authing用户UDF数据创建AuthManager实例
        
        Args:
            udf_data: Authing UDF数据
            package_config_path: 包配置文件路径
            
        Returns:
            AuthManager实例
        """
        logger.info("从UDF数据创建AuthManager实例")
        
        # 如果UDF数据为空，返回空的授权管理器
        if not udf_data:
            logger.warning("UDF数据为空，创建默认授权管理器")
            auth_manager = AuthManager(package_config_path=package_config_path)
            auth_manager.user_data = {"basic_access": {}, "packages": [], "workflows": []}
            return auth_manager
            
        # 创建实例并解析UDF数据
        auth_manager = AuthManager(package_config_path=package_config_path)
        
        # 如果存在user_authing_info字段，尝试检查并纠正格式
        if 'user_authing_info' in udf_data and isinstance(udf_data['user_authing_info'], str):
            raw_info = udf_data['user_authing_info']
            logger.debug(f"原始user_authing_info: {raw_info[:100]}")
            
            # 尝试处理格式问题
            if raw_info.startswith("'") or (raw_info.startswith("{") and not raw_info.startswith('{')):
                try:
                    # 如果不是有效JSON，尝试解析Python字典
                    import ast
                    parsed = ast.literal_eval(raw_info)
                    # 转换为标准JSON
                    udf_data['user_authing_info'] = json.dumps(parsed)
                    logger.info("已将UDF数据转换为标准JSON格式")
                except Exception as e:
                    logger.error(f"处理UDF数据格式失败: {e}")
        
        # 使用修复后的数据解析
        auth_manager.user_data = auth_manager._parse_user_data(udf_data)
        if not auth_manager.user_data or not auth_manager.user_data.get('basic_access'):
            logger.warning("解析UDF数据未产生有效的用户数据结构")
        else:
            logger.info("成功从UDF数据创建AuthManager实例")
        return auth_manager

# 使用示例
if __name__ == "__main__":
    # 设置日志级别
    logging.basicConfig(level=logging.INFO)
    
    # 在直接运行该文件时，使用模拟数据
    mock_udf_data = {
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
                    "id": "✂️智能抠图",
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
    
    # 创建AuthManager实例（当直接运行时）
    try:
        # 尝试使用常规方式创建
        auth_manager = AuthManager()
    except ImportError:
        # 如果失败，使用模拟数据
        print("使用模拟数据创建AuthManager实例")
        
        # 创建一个临时类，覆盖导入问题
        class MockAuthManager(AuthManager):
            def __init__(self):
                self.package_config_path = 'config/package.json'
                self.package_config = {}
                # 直接使用模拟数据
                self.user_data = self._parse_user_data(mock_udf_data)
        
        auth_manager = MockAuthManager()
    
    # 获取所有授权的工作流
    authorized_workflows = auth_manager.get_authorized_workflows()
    print("\n授权的工作流及详情:")
    for workflow_id, info in authorized_workflows.items():
        if info["source"] == "package":
            print(f"- {workflow_id} (通过包 '{info['package_id']}' 授权)")
        else:
            print(f"- {workflow_id} (直接授权)")
        
        if info["type"] == "lifetime":
            print("  永久授权")
        else:
            print(f"  到期时间: {info['expired_at']}")
    
    # 获取工作流ID列表
    workflow_list = auth_manager.get_workflow_list()
    print("\n可访问的工作流列表:")
    for workflow in workflow_list:
        print(f"- {workflow}")
    
    # 检查特定工作流授权
    test_workflow = "✂️智能抠图"
    is_authorized = auth_manager.is_workflow_authorized(test_workflow)
    print(f"\n工作流 '{test_workflow}' 授权状态: {'有权限' if is_authorized else '无权限'}") 