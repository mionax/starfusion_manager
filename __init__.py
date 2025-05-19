from .workflow_manager import setup

NODE_CLASS_MAPPINGS = {}
NODE_DISPLAY_NAME_MAPPINGS = {}

WEB_DIRECTORY = "./web"

__all__ = ['NODE_CLASS_MAPPINGS', 'NODE_DISPLAY_NAME_MAPPINGS', 'WEB_DIRECTORY', 'setup']

def init():
    print("[工作流管理器] 初始化插件...")
    from server import PromptServer
    setup(PromptServer.instance.app)

init()
