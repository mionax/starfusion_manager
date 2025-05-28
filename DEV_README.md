# StarFusion Manager 开发文档

## 项目简介

StarFusion Manager 是 ComfyUI 的一个工作流管理插件，提供了工作流文件的管理、云端同步以及基于用户授权的工作流访问控制功能。该插件主要包括以下核心功能：

1. 本地工作流文件管理
2. GitHub 云端工作流同步
3. Authing 用户认证系统
4. 基于用户权限的工作流访问控制
5. 直观的侧边栏界面

## 系统架构

整个系统由以下几个部分组成：

1. **后端**：Python 模块，处理 API 请求、文件操作和授权验证
2. **前端**：JavaScript 模块，实现用户界面和交互
3. **数据源**：本地文件系统和 GitHub 远程仓库
4. **授权服务**：Authing 第三方授权服务集成

## 文件结构与功能

### 核心文件

| 文件名 | 功能描述 |
|-------|---------|
| `__init__.py` | 插件入口点，初始化并挂载插件到 ComfyUI |
| `workflow_manager.py` | 主要业务逻辑实现，包括初始化配置和路由设置 |
| `api_handlers.py` | API 请求处理程序，包含各个端点的处理逻辑 |
| `auth_manager.py` | 工作流授权管理器，负责权限验证和用户授权检查 |
| `auth_service.py` | 授权服务，与 Authing 进行交互 |
| `github_api.py` | GitHub API 客户端，处理与 GitHub 仓库的交互 |
| `data_sources.py` | 数据源抽象和实现，包括本地和 GitHub 工作流来源 |
| `utils.py` | 通用工具函数 |

### 前端文件

| 文件名 | 功能描述 |
|-------|---------|
| `web/ui.js` | 前端 UI 实现，包含侧边栏交互和工作流展示逻辑 |
| `web/authing_config.js` | Authing 配置参数 |
| `web/authing_login.html` | Authing 登录页面 |
| `web/authing_callback.html` | Authing 回调处理页面 |

### 配置文件

| 文件名 | 功能描述 |
|-------|---------|
| `cloud_workflow_config.json` | 云工作流配置文件 |
| `user_udf.json` | 用户自定义字段配置格式示例 |
| `user.json` | 用户登录返回信息格式示例 |
| `config/package.json` | 包定义配置，包含工作流的分类信息 |
| `config/user_authing_config.json` | 用户自定义 Authing 配置 |
| `config/deafault_authing_config.json` | 默认 Authing 配置 |

## 核心模块详解

### 1. 工作流管理器 (workflow_manager.py)

这是插件的核心模块，负责初始化配置、设置路由和提供主要业务逻辑。主要功能包括：

- 加载环境变量和配置
- 初始化本地和远程工作流目录
- 设置 GitHub API 客户端
- 注册各种 API 路由
- 提供工作流访问控制逻辑

关键函数：
- `setup(app)`: 初始化插件并注册路由
- `get_auth_manager_for_user(user_id, token)`: 为用户创建授权管理器
- `get_user_workflows(user_id, token)`: 获取用户有权限访问的工作流列表

### 2. API 处理程序 (api_handlers.py)

处理所有 API 请求的模块，提供各种端点处理函数：

- 获取本地/远程工作流列表
- 获取特定工作流文件内容
- 用户认证（登录/注册）
- 检查工作流授权
- 缓存管理

关键函数：
- `handle_get_workflows`: 获取本地工作流列表
- `handle_get_remote_workflows`: 获取远程工作流列表
- `handle_auth_login`: 处理用户登录
- `handle_auth_register`: 处理用户注册
- `handle_check_workflow_auth`: 检查用户是否有权限访问特定工作流

### 3. 授权管理器 (auth_manager.py)

负责管理用户授权和权限验证的模块：

- 加载用户自定义数据(UDF)
- 验证授权有效性
- 提供工作流访问权限控制

关键函数：
- `get_authorized_workflows()`: 获取用户被授权的所有工作流
- `is_workflow_authorized(workflow_id)`: 检查用户是否有权限访问指定工作流
- `from_authing_udf(udf_data)`: 从 Authing 用户自定义数据创建授权管理器

### 4. 数据源 (data_sources.py)

定义了统一的数据源接口和两种实现：本地文件系统和 GitHub 仓库：

- `WorkflowDataSource`: 抽象基类，定义统一接口
- `LocalWorkflowSource`: 本地文件系统工作流数据源
- `GitHubWorkflowSource`: GitHub 仓库工作流数据源

关键方法：
- `scan_directory()`: 扫描目录并获取工作流列表
- `get_workflow(path)`: 获取特定工作流文件内容

### 5. GitHub API (github_api.py)

处理与 GitHub API 交互的客户端：

- 获取仓库目录内容
- 获取文件内容
- 处理认证和错误

关键方法：
- `get_contents(path)`: 获取指定路径的内容
- `get_file_content(path)`: 获取特定文件的内容

### 6. 前端界面 (web/ui.js)

实现用户界面和交互逻辑：

- ComfyUI 侧边栏集成
- 工作流列表展示与过滤
- 本地/远程工作流加载
- 用户登录与授权状态管理

关键功能：
- 标签页切换（本地/云端/用户工作流）
- 工作流搜索过滤
- 加载工作流到 ComfyUI
- 用户登录/注册界面

## 系统流程

### 初始化流程

1. ComfyUI 加载插件时调用 `__init__.py` 中的 `init()` 函数
2. 调用 `workflow_manager.py` 的 `setup()` 注册路由和初始化配置
3. 创建本地和远程数据源实例
4. 初始化缓存系统

### 工作流加载流程

1. 用户在 UI 中选择工作流文件
2. 前端调用相应的 API 端点（本地或远程）
3. 后端验证用户权限（仅远程工作流）
4. 数据源获取工作流内容并返回
5. 前端接收数据并加载到 ComfyUI 画布

### 用户授权流程

1. 用户通过前端界面登录
2. 调用 `auth_service.py` 进行身份验证
3. 生成用户 Token 并返回给前端
4. 前端保存 Token 并在后续请求中使用
5. 用户请求工作流时，后端验证 Token 并检查权限

## 关键配置项

### GitHub 配置

- `GITHUB_REPO_OWNER`: GitHub 仓库所有者
- `GITHUB_REPO_NAME`: 仓库名称
- `GITHUB_TOKEN`: 访问令牌，用于 API 验证
- `REMOTE_WORKFLOW_BASE_PATH`: 远程工作流基础路径

### 授权配置

- `user_udf.json`: 用户自定义字段，定义授权信息
- `config/package.json`: 定义工作流包和分类

## 开发注意事项

1. **GitHub Token 管理**：确保 GitHub Token 正确配置，否则云端功能将不可用
2. **授权逻辑**：授权验证分为基本访问权限和特定工作流权限两层
3. **缓存机制**：系统使用缓存减少 API 调用，更改后需要清除缓存
4. **路径处理**：注意本地路径和 GitHub 路径的差异处理
5. **错误处理**：API 调用中有完善的错误处理和日志记录

## 扩展开发指南

### 添加新数据源

1. 在 `data_sources.py` 中继承 `WorkflowDataSource` 类
2. 实现 `scan_directory()` 和 `get_workflow()` 方法
3. 在 `workflow_manager.py` 中初始化新数据源
4. 添加相应的 API 处理程序和路由

### 修改授权逻辑

1. 编辑 `auth_manager.py` 中的权限检查逻辑
2. 更新 `user_udf.json` 结构定义
3. 修改 `api_handlers.py` 中的相关授权验证代码

### 前端界面定制

1. 编辑 `web/ui.js` 中的 UI 渲染代码
2. 修改 CSS 样式定义
3. 添加新的交互功能和事件处理程序

## 故障排除

### 常见问题

1. **无法加载云端工作流**
   - 检查 `GITHUB_TOKEN` 是否正确配置
   - 检查网络连接和 GitHub API 限制

2. **授权验证失败**
   - 检查 Authing 配置是否正确
   - 验证用户 Token 是否有效
   - 检查用户 UDF 数据格式

3. **UI 显示异常**
   - 检查 ComfyUI 版本兼容性
   - 查看浏览器控制台错误信息

## 开发路线图

1. **工作流版本控制**：添加工作流版本管理功能
2. **用户分享功能**：允许用户分享工作流给其他用户
3. **工作流预览**：添加工作流缩略图预览
4. **批量操作**：支持批量导入/导出工作流
5. **高级搜索**：添加基于标签和元数据的高级搜索功能 