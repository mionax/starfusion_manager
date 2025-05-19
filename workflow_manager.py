import os
import json
from aiohttp import web

WORKFLOW_DIR = os.path.join(os.path.dirname(__file__), "workflows")

def scan_workflow_dir(base_dir):
    data = []
    for root, dirs, files in os.walk(base_dir):
        rel_root = os.path.relpath(root, base_dir)
        folder = {
            "name": rel_root,
            "files": [f for f in files if f.endswith(".json")]
        }
        data.append(folder)
    return data

async def handle_get_workflows(request):
    structure = scan_workflow_dir(WORKFLOW_DIR)
    return web.json_response(structure)

def setup(app):
    app.router.add_get("/workflow_manager/list", handle_get_workflows)
    app.router.add_static("/custom_nodes/workflow_manager/workflows", WORKFLOW_DIR)
