import os
import json
from aiohttp import web
from server import PromptServer

print("="*50)
print("工作流管理器插件开始加载...")
print("="*50)

WORKFLOW_DIR = os.path.join(os.path.dirname(__file__), "workflows")

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
            print(f"[工作流管理器] 扫描目录: {rel_root}")
            print(f"[工作流管理器] 发现文件: {files}")
            
            folder = {
                "name": rel_root,
                "files": [f for f in files if f.endswith(".json")]
            }
            if folder["files"]:  # 只添加包含文件的文件夹
                data.append(folder)
                print(f"[工作流管理器] 添加文件夹: {folder}")
    except Exception as e:
        print(f"[工作流管理器] 扫描工作流目录时出错: {e}")
    return data

async def handle_get_workflows(request):
    try:
        print("[工作流管理器] 收到获取工作流列表请求")
        print(f"[工作流管理器] 请求URL: {request.url}")
        print(f"[工作流管理器] 请求方法: {request.method}")
        
        structure = scan_workflow_dir(WORKFLOW_DIR)
        print(f"[工作流管理器] 工作流列表: {json.dumps(structure, ensure_ascii=False)}")
        
        response = web.json_response(structure)
        print(f"[工作流管理器] 响应状态: {response.status}")
        return response
    except Exception as e:
        print(f"[工作流管理器] 获取工作流列表时出错: {e}")
        return web.json_response({"error": str(e)}, status=500)

async def handle_get_workflow(request):
    try:
        rel_path = request.match_info['path']
        file_path = os.path.join(WORKFLOW_DIR, rel_path)
        print(f"[工作流管理器] 请求工作流文件: {file_path}")
        
        if not os.path.exists(file_path):
            print(f"[工作流管理器] 文件不存在: {file_path}")
            return web.json_response({"error": "File not found"}, status=404)
            
        with open(file_path, 'r', encoding='utf-8') as f:
            content = json.load(f)
            print(f"[工作流管理器] 成功加载工作流文件: {file_path}")
            return web.json_response(content)
    except Exception as e:
        print(f"[工作流管理器] 加载工作流文件时出错: {e}")
        return web.json_response({"error": str(e)}, status=500)

def setup(app):
    try:
        print("="*50)
        print("[工作流管理器] 开始设置工作流管理器...")
        print(f"[工作流管理器] 工作流目录: {WORKFLOW_DIR}")
        
        # 使用正确的方式注册路由
        app.router.add_get("/workflow_manager/list", handle_get_workflows)
        app.router.add_get("/workflow_manager/workflows/{path:.*}", handle_get_workflow)
        
        print("[工作流管理器] 工作流管理器路由已注册")
        print("="*50)
    except Exception as e:
        print(f"[工作流管理器] 设置过程中出错: {e}")
        raise
