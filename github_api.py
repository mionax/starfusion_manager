import requests
import os
import base64

class GitHubAPI:
    def __init__(self, owner, repo, token=None):
        self.owner = owner
        self.repo = repo
        self.token = token
        self.base_url = f"https://api.github.com/repos/{owner}/{repo}"
        self.headers = {}
        if self.token:
            self.headers['Authorization'] = f'token {self.token}'
        self.headers['Accept'] = 'application/vnd.github.v3+json'

    def _request(self, method, url, params=None):
        try:
            response = requests.request(method, url, headers=self.headers, params=params)
            response.raise_for_status()  # Raise an HTTPError for bad responses (4xx or 5xx)
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"[GitHubAPI] 请求出错: {e}")
            return None

    def get_contents(self, path):
        """获取指定路径下的文件列表"""
        url = f"{self.base_url}/contents/{path}"
        print(f"[GitHubAPI] 获取目录内容: {url}")
        return self._request('GET', url)

    def get_file_content(self, path):
        """获取指定文件的内容"""
        url = f"{self.base_url}/contents/{path}"
        print(f"[GitHubAPI] 获取文件内容: {url}")
        data = self._request('GET', url)
        if data and 'content' in data:
            # GitHub returns content as base64 encoded string
            return base64.b64decode(data['content']).decode('utf-8')
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