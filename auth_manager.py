import json
import os
import datetime
from typing import List, Dict, Any, Optional

class AuthManager:
    def __init__(self, user_udf_path: str = 'user_udf.json', package_config_path: str = 'config/package.json'):
        """
        初始化认证管理器
        
        Args:
            user_udf_path: 用户UDF数据文件路径
            package_config_path: 包配置文件路径
        """
        self.user_udf_path = user_udf_path
        self.package_config_path = package_config_path
        self.user_data = None
        self.package_config = None
        
        # 加载用户数据
        self._load_user_data()
        # 加载包配置
        self._load_package_config()
    
    def _load_user_data(self) -> None:
        """加载用户UDF数据"""
        try:
            if os.path.exists(self.user_udf_path):
                with open(self.user_udf_path, 'r', encoding='utf-8') as f:
                    self.user_data = json.load(f)
            else:
                print(f"用户数据文件不存在: {self.user_udf_path}")
                self.user_data = {"basic_access": {}, "packages": [], "workflows": []}
        except Exception as e:
            print(f"加载用户数据出错: {e}")
            self.user_data = {"basic_access": {}, "packages": [], "workflows": []}
    
    def _load_package_config(self) -> None:
        """加载包配置数据"""
        try:
            if os.path.exists(self.package_config_path):
                with open(self.package_config_path, 'r', encoding='utf-8') as f:
                    self.package_config = json.load(f)
            else:
                print(f"包配置文件不存在: {self.package_config_path}")
                self.package_config = {}
        except Exception as e:
            print(f"加载包配置出错: {e}")
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
            return True
        
        # 有过期时间的授权
        if expired_at:
            try:
                # 将字符串转换为datetime对象
                expiry_date = datetime.datetime.fromisoformat(expired_at.replace('Z', '+00:00'))
                # 检查是否已过期
                return datetime.datetime.now(datetime.timezone.utc) < expiry_date
            except Exception as e:
                print(f"解析过期时间出错: {e}")
                return False
        
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
        if not self.user_data:
            return {}
        
        # 检查基本访问权限
        basic_access = self.user_data.get("basic_access", {})
        basic_access_valid = self._is_authorization_valid(
            basic_access.get("type", ""), 
            basic_access.get("expired_at")
        )
        
        if not basic_access_valid:
            print("基本访问权限已过期或无效")
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
        
        # 添加直接授权的工作流
        for workflow in self.user_data.get("workflows", []):
            workflow_id = workflow.get("id")
            if not workflow_id:
                continue
                
            # 检查工作流授权是否有效
            if not self._is_authorization_valid(workflow.get("type", ""), workflow.get("expired_at")):
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

# 使用示例
if __name__ == "__main__":
    auth_manager = AuthManager()
    
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