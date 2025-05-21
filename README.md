# ComfyUI Workflow Manager

一个用于 ComfyUI 的工作流管理插件，提供直观的侧边栏界面来管理和组织您的工作流文件。

## 功能特性

- 📁 工作流文件管理：轻松浏览和组织您的工作流文件
- 🎯 直观的侧边栏界面：集成到 ComfyUI 的侧边栏中，方便访问
- 🔄 实时更新：自动检测工作流目录的变化
- 📂 文件夹支持：支持多级文件夹结构，更好地组织您的工作流

## 安装方法

1. 在 ComfyUI 的 `custom_nodes` 目录下克隆此仓库：
```bash
cd ComfyUI/custom_nodes
git clone https://github.com/mionax/Starfusion_manager.git
```

2. 重启 ComfyUI

## 使用方法

1. 启动 ComfyUI 后，在侧边栏中会出现 "Workflow Manager" 面板
2. 您的工作流文件应该放在插件的 `workflows` 目录下
3. 支持创建子文件夹来更好地组织您的工作流
4. 点击工作流文件即可加载到 ComfyUI 中

## 目录结构

```
ComfyUI-Workflow-Manager/
├── workflows/           # 工作流文件目录
├── web/                # 前端资源
│   └── ui.js          # 用户界面实现
├── workflow_manager.py # 后端实现
└── __init__.py        # 插件入口
```

## 开发计划

- [ ] 工作流导入/导出功能
- [ ] 工作流分类和标签系统
- [ ] 工作流预览功能
- [ ] 搜索功能
- [ ] 收藏夹功能

## 贡献

欢迎提交 Issue 和 Pull Request！

## 许可证

MIT License

## 作者

[Mionax]

## 致谢

感谢 ComfyUI 社区的支持和贡献！ 
