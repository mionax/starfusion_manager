import os
import json
from aiohttp import web
from server import PromptServer

import requests # Added for completeness, though github_api uses it
from dotenv import load_dotenv # Import load_dotenv
from .github_api import GitHubAPI # Import GitHubAPI from the new file

# Load environment variables from a .env file
load_dotenv()

print("="*50)
print("工作流管理器插件开始加载...")
print("="*50)

WORKFLOW_DIR = os.path.join(os.path.dirname(__file__), "workflows")

# Configure GitHub API
GITHUB_REPO_OWNER = 'mionax'
GITHUB_REPO_NAME = 'starfusion-workflows'
GITHUB_TOKEN = os.getenv('GITHUB_TOKEN') # Get token from environment variable

if not GITHUB_TOKEN:
    print("[工作流管理器] 警告: 未设置 GITHUB_TOKEN 环境变量，云端工作流功能将无法使用。")

github_api = GitHubAPI(GITHUB_REPO_OWNER, GITHUB_REPO_NAME, token=GITHUB_TOKEN)

# Define a simple cache for workflow data
import time

class WorkflowCache:
    def __init__(self, expire_time=300): # Cache expires after 300 seconds (5 minutes)
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

        # Assuming workflows are in the root directory of the repo
        remote_workflow_base_path = '' # Changed to empty string for root
        structure = scan_remote_workflow_dir(github_api, remote_workflow_base_path) # Pass the instance

        # If the base path itself contains files, they won't be added under a folder named after the path itself
        # We need to handle the root of the remote_workflow_base_path if it contains files.
        # Let's rescan the base_path only to get files directly in it.
        base_contents = github_api.get_contents(remote_workflow_base_path)
        base_files = [item for item in base_contents if item['type'] == 'file' and item['name'].endswith('.json')]
        if base_files:
            # Add files at the root of the remote workflow path under a folder named after the path itself (which is '/ ')
             structure.insert(0, { # Insert at the beginning
                 "name": remote_workflow_base_path if remote_workflow_base_path != '' else '/', # Use '/' for root
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

        print("[工作流管理器] 工作流管理器路由已注册")
        print("="*50)
    except Exception as e:
        print(f"[工作流管理器] 设置过程中出错: {e}")
        raise
