import requests
import base64
import logging

# 设置日志
logger = logging.getLogger('github_api')

class GitHubAPI:
    """处理与GitHub API的交互"""
    
    def __init__(self, owner, repo, token=None):
        """
        初始化GitHub API客户端
        
        Args:
            owner: GitHub仓库所有者（用户名或组织名）
            repo: 仓库名称
            token: GitHub个人访问令牌（可选，但推荐提供以避免API速率限制）
        """
        self.owner = owner
        self.repo = repo
        self.token = token
        self.base_url = f"https://api.github.com/repos/{owner}/{repo}/contents"
        self.headers = {
            "Accept": "application/vnd.github.v3+json"
        }
        if token:
            self.headers["Authorization"] = f"token {token}"
        
        logger.info(f"初始化GitHub API客户端: {owner}/{repo}")

    def get_contents(self, path=""):
        """
        获取指定路径的内容（文件或目录）
        
        Args:
            path: 仓库中的路径（默认为根目录）
            
        Returns:
            内容列表（目录）或文件内容（文件）
        """
        url = f"{self.base_url}/{path}" if path else self.base_url
        logger.info(f"获取GitHub内容: {url}")
        
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()  # 如果请求失败，抛出异常
            
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"获取GitHub内容时出错: {e}")
            if hasattr(e.response, 'status_code'):
                if e.response.status_code == 404:
                    logger.warning(f"GitHub路径不存在: {path}")
                else:
                    logger.error(f"GitHub API响应状态码: {e.response.status_code}")
            return None

    def get_file_content(self, path):
        """
        获取文件内容
        
        Args:
            path: 文件路径
            
        Returns:
            文件内容（字符串）
        """
        url = f"{self.base_url}/{path}"
        logger.info(f"获取GitHub文件: {url}")
        
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            
            content = response.json()
            
            # 确保是文件而不是目录
            if isinstance(content, list):
                logger.warning(f"获取的路径是目录，不是文件: {path}")
                return None
                
            # GitHub API返回的文件内容是Base64编码的
            if content.get('type') == 'file':
                encoded_content = content.get('content', '')
                decoded_content = base64.b64decode(encoded_content).decode('utf-8')
                return decoded_content
            else:
                logger.warning(f"内容类型不是文件: {content.get('type')}")
                return None
        except requests.exceptions.RequestException as e:
            logger.error(f"获取GitHub文件内容时出错: {e}")
            return None
        except ValueError as e:
            logger.error(f"解析GitHub API响应时出错: {e}")
            return None
        except Exception as e:
            logger.error(f"获取文件内容时出现未知错误: {e}")
            return None

# Example Usage (for testing purposes)
# if __name__ == "__main__":
#     # Make sure to set your GitHub Token as an environment variable
#     # export GITHUB_TOKEN='your_token_here'
#     github_token = os.environ.get('GITHUB_TOKEN')
#     if not github_token:
#         print("请设置环境变量 GITHUB_TOKEN")
#     else:
#         api = GitHubAPI('mionax', 'starfusion-workflows', token=github_token)

#         # Get contents of the root directory
#         contents = api.get_contents('')
#         if contents:
#             print("Root Contents:")
#             for item in contents:
#                 print(f" - {item['name']} ({item['type']})")

#         # Get contents of a specific directory (replace with an actual directory in your repo)
#         # dir_contents = api.get_contents('workflows')
#         # if dir_contents:
#         #     print("\nWorkflows Directory Contents:")
#         #     for item in dir_contents:
#         #         print(f" - {item['name']} ({item['type']})")

#         # Get content of a specific file (replace with an actual file in your repo)
#         # file_content = api.get_file_content('README.md')
#         # if file_content:
#         #     print("\nREADME.md Content:")
#         #     print(file_content[:200] + '...') # Print first 200 chars 