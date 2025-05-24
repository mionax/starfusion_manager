import { app } from "../../scripts/app.js";
import AuthingConfig from "./authing_config.js";

app.registerExtension({
    name: "ComfyUI.WorkflowManager",
    async setup() {
        // 注册侧边栏标签
        app.extensionManager.registerSidebarTab({
            id: 'workflow-manager',
            icon: 'pi pi-cloud',  // 更换为云朵图标（PrimeIcons）
            title: '工作流管理器',
            tooltip: '加载工作流',
            type: 'custom',
            
            render: async (el) => {
                // 创建面板内容容器
                const panel = document.createElement("div");
                panel.className = "workflow-manager-panel"; // 添加类名
                panel.style = "justify-content: flex-start;"; // 保证内容顶对齐

                // 添加 CSS 样式
                const style = document.createElement("style");
                style.innerHTML = `
                    .workflow-manager-panel {
                        padding: 10px;
                        color: white;
                        font-family: sans-serif;
                        background-color: transparent;
                        border-radius: 5px;
                        height: 100%; /* 填充父容器高度 */
                        overflow-y: hidden; /* 容器本身不滚动，让内部内容区域滚动 */
                        display: flex; /* 使用 flexbox 布局 */
                        flex-direction: column; /* 垂直排列 */
                    }
                    .workflow-manager-tabs {
                        display: flex;
                        margin-bottom: 10px;
                        border-bottom: 1px solid #555;
                         flex-shrink: 0; /* 防止被压缩 */
                    }
                    .workflow-manager-tab-button {
                        flex-grow: 1;
                        padding: 10px 0;
                        text-align: center;
                        cursor: pointer;
                        color: #aaa;
                        border: none;
                        background-color: transparent;
                        font-size: 1em;
                        transition: color 0.3s ease;
                    }
                    .workflow-manager-tab-button:hover {
                        color: #ddd;
                    }
                    .workflow-manager-tab-button.active {
                        color: #8cf;
                        border-bottom: 2px solid #8cf;
                        font-weight: bold;
                    }
                    .workflow-manager-content-container {
                         flex-grow: 1; /* 占据剩余空间 */
                         overflow-y: auto; /* 允许内部内容滚动 */
                         padding-right: 5px; /* Add padding to avoid scrollbar overlapping content */
                    }
                    /* Container for search input and refresh button */
                    .workflow-controls-container {
                        display: flex;
                        align-items: center;
                        margin-bottom: 10px;
                        padding: 0 5px; /* Add some padding */
                         flex-shrink: 0; /* Prevents shrinking */
                    }
                    .workflow-manager-panel input[type="text"].workflow-search-input { /* 搜索框样式 */
                        flex-grow: 1; /* Allow input to take available space */
                        margin: 0; /* Remove margin that might interfere with flex */
                        margin-right: 10px; /* Add space between input and button */
                        display: block; /* Keep block display */
                        padding: 8px;
                        border: 1px solid #555;
                        border-radius: 4px;
                        background-color: #3c3c3c;
                        color: white;
                        font-size: 1em;
                    }
                    .workflow-manager-panel input[type="text"].workflow-search-input::placeholder {
                        color: #aaa;
                    }
                    .workflow-manager-panel input[type="text"].workflow-search-input:focus {
                        outline: none;
                        border-color: #8cf;
                        box-shadow: 0 0 5px rgba(136, 204, 255, 0.5);
                    }
                     .workflow-refresh-button {
                        padding: 8px 12px; /* Adjust padding to match input height */
                        cursor: pointer;
                        background-color: #555; /* Darker background */
                        color: white;
                        border: none;
                        border-radius: 4px;
                        transition: background-color 0.3s ease; /* Smooth transition */
                        flex-shrink: 0; /* Prevents shrinking */
                    }
                    .workflow-refresh-button:hover {
                         background-color: #666; /* Slightly lighter on hover */
                    }

                    .workflow-content { /* Content area within the scrollable container */
                        padding: 0 10px 20px;
                    }

                    .workflow-folder { /* 文件夹样式 */
                        margin-top: 22px;
                        font-weight: bold;
                        font-size: 1.08em;
                        color: #fff;
                        letter-spacing: 1px;
                        padding: 10px 0 10px 18px;
                        background: linear-gradient(90deg, #232c3a 60%, #232c3a00 100%);
                        border-left: 6px solid #4a90e2;
                        margin-bottom: 8px;
                        border-radius: 4px 0 0 4px;
                        box-shadow: 0 2px 8px 0 rgba(40,80,180,0.04);
                    }

                    .workflow-file-item { /* 文件项样式 */
                        margin-left: 38px;
                        display: flex;
                        align-items: center;
                        justify-content: space-between;
                        padding: 4px 0 4px 0;
                        border-bottom: 1px solid #3a3a3a; /* 分隔线 */
                        font-size: 1em;
                        color: #e6f7ff;
                    }
                    .workflow-file-item:last-child {
                         border-bottom: none; /* 最后一个文件项没有分隔线 */
                    }

                    .workflow-file-title { /* 文件名样式 */
                        cursor: pointer;
                        color: #8cf; /* 亮蓝色 */
                        flex-grow: 1; /* 允许占用更多空间 */
                        margin-right: 10px;
                        white-space: nowrap; /* 防止换行 */
                        overflow: hidden; /* 隐藏溢出文本 */
                        text-overflow: ellipsis; /* 显示省略号 */
                    }
                     .workflow-file-title:hover {
                        text-decoration: underline; /* 悬停下划线 */
                    }

                    .workflow-fav-btn { /* 收藏按钮样式 */
                        cursor: pointer;
                        color: gold; /* 金色 */
                        font-size: 1.2em;
                        padding: 0 5px;
                         flex-shrink: 0; /* Prevents shrinking */
                    }
                    .workflow-fav-btn:hover {
                        opacity: 0.8; /* 悬停降低透明度 */
                    }

                    .workflow-favorites-section { /* 收藏夹区域样式 */
                        margin-top: 20px;
                        padding-top: 10px;
                        border-top: 1px solid #4a4a4a; /* 顶部边框 */
                        color: #ddd;
                    }

                    .workflow-fav-item { /* 收藏项样式 */
                        margin-left: 20px;
                        padding: 5px 0;
                        cursor: pointer;
                        color: #ff8; /* 淡黄色 */
                        white-space: nowrap;
                        overflow: hidden;
                        text-overflow: ellipsis;
                    }
                    .workflow-fav-item:hover {
                         text-decoration: underline;
                    }
                     .hidden-content {
                         display: none;
                     }
                    .workflow-manager-header {
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        gap: 10px;
                        padding: 14px 18px 18px 18px;
                        font-size: 1.5em;
                        font-weight: bold;
                        color: #fff;
                        background: linear-gradient(90deg, #3a4a6a 0%, #2a8cff 100%);
                        border-radius: 0;
                        box-shadow: 0 2px 8px 0 rgba(40,80,180,0.10);
                        cursor: pointer;
                        user-select: none;
                        letter-spacing: 2px;
                        margin-bottom: 10px;
                        transition: background 0.3s;
                    }
                    .workflow-manager-header:hover {
                        color: #fff;
                        background: linear-gradient(90deg, #4a5a7a 0%, #3ab0ff 100%);
                        box-shadow: 0 4px 16px 0 rgba(40,120,255,0.15);
                        text-decoration: none;
                    }
                    .workflow-manager-header .header-icon {
                        font-size: 1.2em;
                        margin-right: 6px;
                        color: #ffe066;
                        filter: drop-shadow(0 1px 2px #0008);
                     }
                     
                    /* 登录相关样式 */
                    .user-login-container {
                        display: flex;
                        align-items: center;
                        justify-content: flex-end;
                        padding: 8px 0;
                        margin-bottom: 10px;
                        flex-shrink: 0;
                    }
                    .login-button {
                        background: linear-gradient(90deg, #2a8cff 0%, #3a6cff 100%);
                        color: white;
                        border: none;
                        border-radius: 4px;
                        padding: 8px 16px;
                        cursor: pointer;
                        font-weight: bold;
                        transition: all 0.3s ease;
                    }
                    .login-button:hover {
                        background: linear-gradient(90deg, #3a9cff 0%, #4a7cff 100%);
                        box-shadow: 0 2px 8px rgba(42, 140, 255, 0.4);
                    }
                    .user-info {
                        display: flex;
                        align-items: center;
                        gap: 10px;
                    }
                    .user-avatar {
                        width: 32px;
                        height: 32px;
                        border-radius: 50%;
                        object-fit: cover;
                        border: 2px solid #4a90e2;
                    }
                    .user-name {
                        color: white;
                        font-weight: bold;
                    }
                    .logout-button {
                        color: #ff6b6b;
                        background: transparent;
                        border: 1px solid #ff6b6b;
                        border-radius: 4px;
                        padding: 4px 8px;
                        margin-left: 10px;
                        cursor: pointer;
                        font-size: 0.8em;
                        transition: all 0.3s ease;
                    }
                    .logout-button:hover {
                        background: rgba(255, 107, 107, 0.1);
                    }
                `;
                el.appendChild(style); // 将样式添加到元素中

                // ====== 新增：顶部标题栏 ======
                const header = document.createElement("div");
                header.className = "workflow-manager-header";
                header.title = "点击访问星汇工作流云端仓库";
                header.onclick = () => {
                    window.open("https://github.com/StarFusionLab/comfyui-workflows", "_blank");
                };
                // 只保留文字，无图标
                header.innerText = "✨️星汇工作流管理器";
                panel.appendChild(header);
                // ====== 标题栏结束 ======
                
                // ====== 新增：登录区域 ======
                const loginContainer = document.createElement("div");
                loginContainer.className = "user-login-container";
                
                // 初始状态设为未登录，显示登录按钮
                const showLoginButton = () => {
                    loginContainer.innerHTML = '';
                    const loginButton = document.createElement("button");
                    loginButton.className = "login-button";
                    loginButton.innerText = "登录";
                    loginButton.onclick = handleLogin; // 使用修改后的登录函数
                    loginContainer.appendChild(loginButton);
                };
                
                // 已登录状态，显示用户信息
                const showUserInfo = (userInfo) => {
                    loginContainer.innerHTML = '';
                    const userInfoDiv = document.createElement("div");
                    userInfoDiv.className = "user-info";
                    
                    // 头像 - 从Authing用户信息中获取photo字段
                    const avatarUrl = userInfo.photo || userInfo.picture || userInfo.avatar || "https://files.authing.co/authing-console/default-user-avatar.png";
                    const avatar = document.createElement("img");
                    avatar.className = "user-avatar";
                    avatar.src = avatarUrl;
                    avatar.alt = "用户头像";
                    userInfoDiv.appendChild(avatar);
                    
                    // 用户名 - 优先使用nickname，其次是username
                    const userName = document.createElement("span");
                    userName.className = "user-name";
                    userName.innerText = userInfo.nickname || userInfo.username || userInfo.name || "用户";
                    userInfoDiv.appendChild(userName);
                    
                    // 退出按钮
                    const logoutButton = document.createElement("button");
                    logoutButton.className = "logout-button";
                    logoutButton.innerText = "退出";
                    logoutButton.onclick = handleLogout;
                    userInfoDiv.appendChild(logoutButton);
                    
                    loginContainer.appendChild(userInfoDiv);
                };
                
                panel.appendChild(loginContainer);
                // ====== 登录区域结束 ======

                // Tab 切换区域
                const tabsContainer = document.createElement("div");
                tabsContainer.className = "workflow-manager-tabs";
                panel.appendChild(tabsContainer);

                const localTabBtn = document.createElement("button");
                localTabBtn.className = "workflow-manager-tab-button active";
                localTabBtn.innerText = "📁 本地工作流";
                tabsContainer.appendChild(localTabBtn);

                const cloudTabBtn = document.createElement("button");
                cloudTabBtn.className = "workflow-manager-tab-button";
                cloudTabBtn.innerText = "☁️ 云端工作流";
                tabsContainer.appendChild(cloudTabBtn);
                
                // ====== 新增：会员工作流标签 ======
                const memberTabBtn = document.createElement("button");
                memberTabBtn.className = "workflow-manager-tab-button";
                memberTabBtn.innerText = "✨ 我的工作流";
                tabsContainer.appendChild(memberTabBtn);
                // ====== 会员工作流标签结束 ======

                // 内容区域容器
                const contentContainer = document.createElement("div");
                contentContainer.className = "workflow-manager-content-container";
                panel.appendChild(contentContainer);

                // 本地工作流内容区域
                const localContent = document.createElement("div");
                localContent.id = "workflow-local-content";
                localContent.className = "workflow-content";
                // localContent.style = "padding: 0 10px 20px;"; // Move to CSS class
                contentContainer.appendChild(localContent);

                 // 云端工作流内容区域
                const cloudContent = document.createElement("div");
                cloudContent.id = "workflow-cloud-content";
                cloudContent.className = "workflow-content hidden-content"; // 默认隐藏
                 // cloudContent.style = "padding: 0 10px 20px;"; // Move to CSS class
                contentContainer.appendChild(cloudContent);
                
                // ====== 新增：会员工作流内容区域 ======
                const memberContent = document.createElement("div");
                memberContent.id = "workflow-member-content";
                memberContent.className = "workflow-content hidden-content"; // 默认隐藏
                contentContainer.appendChild(memberContent);
                // ====== 会员工作流内容区域结束 ======

                // --- Controls (Search and Refresh) Container ---
                // Create a container for search and refresh button
                const controlsContainer = document.createElement("div");
                controlsContainer.className = "workflow-controls-container";

                // Search Input
                const searchInput = document.createElement("input"); // Use a single search input for both tabs
                searchInput.type = "text";
                searchInput.className = "workflow-search-input"; // Use the same class
                // placeholder will be set by tab switch logic

                // Refresh Button (initially for cloud, but placed in the common container)
                const refreshButton = document.createElement("button"); // Use a single refresh button
                refreshButton.className = "workflow-refresh-button"; // Use the same class
                refreshButton.innerText = "刷新"; // Generic text
                refreshButton.style.display = 'none'; // Hide initially, show only for cloud
                refreshButton.onclick = () => refreshCloudWorkflows(); // Attach cloud refresh logic

                controlsContainer.appendChild(searchInput);
                controlsContainer.appendChild(refreshButton);

                // Append the controls container before the content container
                panel.insertBefore(controlsContainer, contentContainer);
                // --- End Controls Container ---

                // Tab 切换逻辑
                localTabBtn.onclick = () => {
                    localTabBtn.classList.add('active');
                    cloudTabBtn.classList.remove('active');
                    memberTabBtn.classList.remove('active'); // 新增
                    localContent.classList.remove('hidden-content');
                    cloudContent.classList.add('hidden-content');
                    memberContent.classList.add('hidden-content'); // 新增
                    searchInput.placeholder = "搜索本地工作流..."; // Set placeholder
                    searchInput.oninput = () => filterResults(searchInput.value.toLowerCase(), '#workflow-local-content');
                    refreshButton.style.display = 'none'; // Hide refresh button
                    loadLocalWorkflows(localContent); // Reload local
                };

                cloudTabBtn.onclick = () => {
                    cloudTabBtn.classList.add('active');
                    localTabBtn.classList.remove('active');
                    memberTabBtn.classList.remove('active'); // 新增
                    cloudContent.classList.remove('hidden-content');
                    localContent.classList.add('hidden-content');
                    memberContent.classList.add('hidden-content'); // 新增
                     searchInput.placeholder = "搜索云端工作流..."; // Set placeholder
                    searchInput.oninput = () => filterResults(searchInput.value.toLowerCase(), '#workflow-cloud-content');
                    refreshButton.style.display = ''; // Show refresh button
                    loadCloudWorkflows(cloudContent); // Load cloud
                };

                // ====== 新增：会员工作流标签切换逻辑 ======
                memberTabBtn.onclick = () => {
                    // 检查是否已登录
                    if (!isUserLoggedIn()) {
                        alert("请先登录以访问您的专属工作流");
                        return;
                    }
                    
                    memberTabBtn.classList.add('active');
                    localTabBtn.classList.remove('active');
                    cloudTabBtn.classList.remove('active');
                    memberContent.classList.remove('hidden-content');
                    localContent.classList.add('hidden-content');
                    cloudContent.classList.add('hidden-content');
                    searchInput.placeholder = "搜索我的工作流...";
                    searchInput.oninput = () => filterResults(searchInput.value.toLowerCase(), '#workflow-member-content');
                    refreshButton.style.display = '';
                    refreshButton.onclick = () => loadMemberWorkflows(memberContent);
                    loadMemberWorkflows(memberContent);
                };
                // ====== 会员工作流标签切换逻辑结束 ======

                // 初始加载本地工作流并设置初始状态
                searchInput.placeholder = "搜索本地工作流...";
                searchInput.oninput = () => filterResults(searchInput.value.toLowerCase(), '#workflow-local-content');
                loadLocalWorkflows(localContent);
                
                // ====== 新增：登录相关函数 ======
                // 检查用户是否已登录
                function isUserLoggedIn() {
                    return localStorage.getItem(AuthingConfig.tokenLocalStorageKey) !== null;
                }
                
                // 处理登录操作
                async function handleLogin() {
                    try {
                        console.log("[工作流管理器] 开始Authing登录流程...");
                        
                        // 创建一个模态对话框来显示简化的登录表单
                        const modalContainer = document.createElement('div');
                        modalContainer.className = 'auth-modal-container';
                        modalContainer.style.cssText = `
                            position: fixed;
                            top: 0;
                            left: 0;
                            width: 100%;
                            height: 100%;
                            background-color: rgba(0, 0, 0, 0.7);
                            z-index: 9999;
                            display: flex;
                            align-items: center;
                            justify-content: center;
                        `;
                        
                        // 创建模态内容容器
                        const modalContent = document.createElement('div');
                        modalContent.className = 'auth-modal-content';
                        modalContent.style.cssText = `
                            background-color: #2a2a2a;
                            width: 450px;
                            max-width: 90%;
                            border-radius: 8px;
                            box-shadow: 0 0 20px rgba(0, 0, 0, 0.5);
                            position: relative;
                            padding: 20px;
                            color: white;
                        `;
                        
                        // 添加关闭按钮
                        const closeBtn = document.createElement('div');
                        closeBtn.className = 'auth-modal-close';
                        closeBtn.innerHTML = '&times;';
                        closeBtn.style.cssText = `
                            position: absolute;
                            top: 10px;
                            right: 15px;
                            font-size: 24px;
                            cursor: pointer;
                            color: #aaa;
                        `;
                        closeBtn.onclick = () => {
                            document.body.removeChild(modalContainer);
                        };
                        
                        // 添加标题
                        const title = document.createElement('h2');
                        title.textContent = '✨ 星汇工作流 - 用户登录';
                        title.style.cssText = `
                            margin-top: 5px;
                            margin-bottom: 20px;
                            text-align: center;
                            color: white;
                        `;
                        
                        // 创建一个简化的登录表单，避免使用Authing Guard
                        const loginFormContainer = document.createElement('div');
                        loginFormContainer.style.cssText = `
                            padding: 20px;
                            display: flex;
                            flex-direction: column;
                            gap: 15px;
                        `;
                        
                        loginFormContainer.innerHTML = `
                            <div style="margin-bottom: 10px; text-align: center;">
                                <p>请输入您的用户名和密码登录</p>
                            </div>
                            <div style="margin-bottom: 15px;">
                                <label style="display: block; margin-bottom: 5px; color: #ccc;">用户名</label>
                                <input id="username-input" type="text" style="width: 100%; padding: 8px; border-radius: 4px; background: #333; border: 1px solid #555; color: white;" placeholder="请输入用户名">
                            </div>
                            <div style="margin-bottom: 15px;">
                                <label style="display: block; margin-bottom: 5px; color: #ccc;">密码</label>
                                <input id="password-input" type="password" style="width: 100%; padding: 8px; border-radius: 4px; background: #333; border: 1px solid #555; color: white;" placeholder="请输入密码">
                            </div>
                            <button id="login-btn" style="padding: 10px; background: linear-gradient(90deg, #2a8cff 0%, #3a6cff 100%); border: none; border-radius: 4px; color: white; cursor: pointer; font-weight: bold;">登录</button>
                            <div id="login-error" style="color: #ff6b6b; text-align: center; display: none; margin-top: 10px;"></div>
                            <div style="margin-top: 15px; text-align: center; font-size: 0.9em; color: #aaa;">
                                * 目前使用简化登录表单。如需注册，请联系管理员。
                            </div>
                        `;
                        
                        // 添加所有元素到模态框
                        modalContent.appendChild(closeBtn);
                        modalContent.appendChild(title);
                        modalContent.appendChild(loginFormContainer);
                        modalContainer.appendChild(modalContent);
                        
                        // 添加模态框到body
                        document.body.appendChild(modalContainer);
                        
                        // 为登录按钮添加事件处理
                        const loginBtn = document.getElementById('login-btn');
                        const usernameInput = document.getElementById('username-input');
                        const passwordInput = document.getElementById('password-input');
                        const errorElement = document.getElementById('login-error');
                        
                        loginBtn.onclick = async () => {
                            try {
                                const username = usernameInput.value.trim();
                                const password = passwordInput.value.trim();
                                
                                if (!username) {
                                    showLoginError('请输入用户名');
                                    return;
                                }
                                
                                if (!password) {
                                    showLoginError('请输入密码');
                                    return;
                                }
                                
                                // 显示加载状态
                                loginBtn.textContent = '登录中...';
                                loginBtn.disabled = true;
                                
                                // 调用后端API进行登录验证
                                const response = await fetch('/workflow_manager/auth/login', {
                                    method: 'POST',
                                    headers: {
                                        'Content-Type': 'application/json'
                                    },
                                    body: JSON.stringify({
                                        username,
                                        password
                                    })
                                });
                                
                                if (!response.ok) {
                                    const errorData = await response.json();
                                    throw new Error(errorData.message || '登录失败，请检查用户名和密码');
                                }
                                
                                const user = await response.json();
                                
                                // 保存用户信息到本地存储
                                localStorage.setItem(AuthingConfig.tokenLocalStorageKey, user.token);
                                localStorage.setItem(AuthingConfig.userInfoLocalStorageKey, JSON.stringify(user));
                                
                                // 更新UI显示用户信息
                                showUserInfo(user);
                                
                                // 关闭模态框
                                document.body.removeChild(modalContainer);
                                
                                // 重新加载会员工作流（如果在会员标签页）
                                if (memberTabBtn && memberTabBtn.classList.contains('active')) {
                                    loadMemberWorkflows(memberContent);
                                }
                                
                                console.log('[工作流管理器] 登录成功:', user);
                            } catch (error) {
                                console.error('[工作流管理器] 登录失败:', error);
                                showLoginError('登录失败: ' + (error.message || '未知错误'));
                                loginBtn.textContent = '登录';
                                loginBtn.disabled = false;
                            }
                        };
                        
                        // 显示登录错误信息
                        function showLoginError(message) {
                            errorElement.textContent = message;
                            errorElement.style.display = 'block';
                        }
                    } catch (error) {
                        console.error("[工作流管理器] 创建登录界面失败:", error);
                        alert("创建登录界面失败，请稍后重试");
                    }
                }
                
                // 处理退出登录
                function handleLogout() {
                    // 清除本地存储的用户信息
                    localStorage.removeItem(AuthingConfig.tokenLocalStorageKey);
                    localStorage.removeItem(AuthingConfig.userInfoLocalStorageKey);
                    
                    // 恢复为登录按钮
                    showLoginButton();
                    
                    // 如果当前在会员工作流页面，自动切换回本地工作流
                    if (memberTabBtn.classList.contains('active')) {
                        localTabBtn.click();
                    }
                    
                    console.log("[工作流管理器] 已退出登录");
                }
                
                // 加载会员专属工作流
                async function loadMemberWorkflows(container) {
                    let contentListDiv = container.querySelector('.workflow-content-list');
                    if (!contentListDiv) {
                        contentListDiv = document.createElement("div");
                        contentListDiv.className = "workflow-content-list";
                        container.appendChild(contentListDiv);
                    }
                    contentListDiv.innerHTML = ''; // 清空内容
                    
                    try {
                        const token = localStorage.getItem('userToken');
                        if (!token) {
                            throw new Error("未登录");
                        }
                        
                        const response = await fetch("/workflow_manager/user/workflows", {
                            method: "GET",
                            headers: {
                                "Authorization": `Bearer ${token}`,
                                "Content-Type": "application/json"
                            }
                        });
                        
                        if (!response.ok) {
                            if (response.status === 404) {
                                const messageDiv = document.createElement("div");
                                messageDiv.style = "color: orange;";
                                messageDiv.innerText = "会员工作流功能正在开发中或接口未找到。";
                                contentListDiv.appendChild(messageDiv);
                                return;
                            }
                            throw new Error(`HTTP error! status: ${response.status}`);
                        }
                        
                        const data = await response.json();
                        renderFolders(data, contentListDiv, loadMemberWorkflow);
                    } catch (error) {
                        console.error("[工作流管理器] 获取会员工作流列表失败:", error);
                        const errorDiv = document.createElement("div");
                        errorDiv.style = "color: red;";
                        errorDiv.innerText = "获取会员工作流列表失败: " + error.message;
                        contentListDiv.appendChild(errorDiv);
                    }
                }
                
                // 加载会员工作流
                async function loadMemberWorkflow(relPath) {
                    console.log("[工作流管理器] 开始加载会员工作流:", relPath);
                    try {
                        const token = localStorage.getItem('userToken');
                        if (!token) {
                            throw new Error("未登录");
                        }
                        
                        const response = await fetch(`/workflow_manager/user/workflows/${relPath}`, {
                            method: "GET",
                            headers: {
                                "Authorization": `Bearer ${token}`,
                                "Content-Type": "application/json"
                            }
                        });
                        
                        if (!response.ok) {
                            throw new Error(`HTTP error! status: ${response.status}`);
                        }
                        
                        const json = await response.json();
                        console.log("[工作流管理器] 会员工作流加载成功:", json);
                        app.loadGraphData(json);
                        alert("已加载会员工作流：" + relPath);
                    } catch (error) {
                        console.error("[工作流管理器] 加载会员工作流失败:", error);
                        alert("加载会员工作流失败：" + error.message);
                    }
                }
                
                // 检查并初始化用户登录状态
                function initUserLoginState() {
                    if (isUserLoggedIn()) {
                        // 从本地存储获取用户信息
                        const userInfoStr = localStorage.getItem(AuthingConfig.userInfoLocalStorageKey);
                        if (userInfoStr) {
                            try {
                                const userInfo = JSON.parse(userInfoStr);
                                console.log('[工作流管理器] 从本地存储加载用户信息:', userInfo);
                                showUserInfo(userInfo);
                                
                                // 验证token是否有效
                                fetch('/workflow_manager/user/info', {
                                    headers: {
                                        'Authorization': `Bearer ${localStorage.getItem(AuthingConfig.tokenLocalStorageKey)}`
                                    }
                                })
                                .then(response => {
                                    if (!response.ok) {
                                        console.warn('[工作流管理器] 用户token已失效，需要重新登录');
                                        handleLogout();
                                    }
                                })
                                .catch(err => {
                                    console.error('[工作流管理器] 验证token出错:', err);
                                });
                            } catch (e) {
                                console.error("[工作流管理器] 解析用户信息失败:", e);
                                showLoginButton();
                            }
                        } else {
                            showLoginButton();
                        }
                    } else {
                        showLoginButton();
                    }
                }
                
                // 初始化登录状态
                initUserLoginState();
                // ====== 登录相关函数结束 ======

                el.appendChild(panel);
            }
        });
    }
});

// New function: Load and render local workflows
async function loadLocalWorkflows(container) {
     // container.innerHTML = ''; // Clear container handled by filterResults now?
     // No need to clear container here, filterResults will handle visibility

     // Instead of clearing, ensure only the content list is affected
     // Find the content list div, if it exists. If not, create it.
     let contentListDiv = container.querySelector('.workflow-content-list');
     if (!contentListDiv) {
         contentListDiv = document.createElement("div");
         contentListDiv.className = "workflow-content-list";
         container.appendChild(contentListDiv);
     }
      contentListDiv.innerHTML = ''; // Clear only the list content


    try {
        const response = await fetch("/workflow_manager/list");
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        renderFolders(data, contentListDiv, loadWorkflow); // Render into the list div
    } catch (error) {
        console.error("获取本地工作流列表失败:", error);
         const errorDiv = document.createElement("div");
         errorDiv.style = "color: red;";
         errorDiv.innerText = "获取本地工作流列表失败，请检查控制台获取详细信息";
        contentListDiv.appendChild(errorDiv);
    }
}

// New function: Load and render cloud workflows
async function loadCloudWorkflows(container) {
     // container.innerHTML = ''; // Clear container handled by filterResults now?
     // No need to clear container here, filterResults will handle visibility

      // Find the content list div, if it exists. If not, create it.
     let contentListDiv = container.querySelector('.workflow-content-list');
     if (!contentListDiv) {
         contentListDiv = document.createElement("div");
         contentListDiv.className = "workflow-content-list";
         container.appendChild(contentListDiv);
     }
      contentListDiv.innerHTML = ''; // Clear only the list content

    try {
        // Assuming backend provides /workflow_manager/list_remote interface
        const response = await fetch("/workflow_manager/list_remote");
        if (!response.ok) {
             // If interface does not exist or errors, show friendly message
             if (response.status === 404) {
                  const messageDiv = document.createElement("div");
                  messageDiv.style = "color: orange;";
                  messageDiv.innerText = "云端工作流功能正在开发中或接口未找到。";
                 contentListDiv.appendChild(messageDiv);
                  return;
             }
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        // Render cloud workflow list (assuming structure is similar to local)
        renderFolders(data, contentListDiv, loadRemoteWorkflow); // Render into the list div
    } catch (error) {
        console.error("获取云端工作流列表失败:", error);
         const errorDiv = document.createElement("div");
         errorDiv.style = "color: red;";
         errorDiv.innerText = "获取云端工作流列表失败，请检查控制台获取详细信息";
        contentListDiv.appendChild(errorDiv);
    }
}

// Modify renderFolders function to receive load function as parameter
function renderFolders(data, container, loadFunc) {
    container.innerHTML = ""; // Clear container, search box handled in loadXXXFunctions

    data.forEach(folder => {
        const folderElem = document.createElement("div");
        folderElem.className = "workflow-folder"; // 添加类名
        folderElem.innerText = folder.name; // 只显示文件夹名，无图标

        folder.files.forEach(file => {
            const fullPath = `${folder.name}/${file}`;

            const fileElem = document.createElement("div");
            fileElem.className = "workflow-file-item"; // 添加类名

            const title = document.createElement("span");
            // 只显示文件名（去掉.json后缀）
            let displayName = file.endsWith('.json') ? file.slice(0, -5) : file;
            title.innerText = displayName;
            title.className = "workflow-file-title"; // 添加类名
            title.onclick = () => loadFunc(fullPath); // 使用传入的加载函数

            fileElem.prepend(title); // 文件名放前面
            folderElem.appendChild(fileElem);
        });

        container.appendChild(folderElem);
    });
}

// Modify filterResults function to receive container selector
function filterResults(keyword, containerSelector) {
    const container = document.querySelector(containerSelector);
    if (!container) return;

    // Filter only the content list div within the container
    const contentListDiv = container.querySelector('.workflow-content-list');
    if (!contentListDiv) return;

    const allItems = contentListDiv.querySelectorAll(".workflow-folder, .workflow-fav-item"); // Include folders and favorites
    allItems.forEach(item => {
        const text = item.innerText.toLowerCase();
        item.style.display = text.includes(keyword) ? "" : "none";
    });
}

// 修改 loadWorkflow 函数为加载本地工作流
function loadWorkflow(relPath) {
    console.log("[工作流管理器] 开始加载本地工作流:", relPath);
    fetch(`/workflow_manager/workflows/${relPath}`)
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(json => {
            console.log("[工作流管理器] 本地工作流加载成功:", json);
            app.loadGraphData(json);
            alert("已加载本地工作流：" + relPath);
        })
        .catch(err => {
            console.error("[工作流管理器] 加载本地工作流失败:", err);
            alert("加载本地工作流失败：" + err);
        });
}

// 新增函数：加载云端工作流
function loadRemoteWorkflow(relPath) {
     console.log("[工作流管理器] 开始加载云端工作流:", relPath);
    // 假设后端提供 /workflow_manager/workflows_remote/{path} 接口
    fetch(`/workflow_manager/workflows_remote/${relPath}`)
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(json => {
            console.log("[工作流管理器] 云端工作流加载成功:", json);
            app.loadGraphData(json);
            alert("已加载云端工作流：" + relPath);
        })
        .catch(err => {
            console.error("[工作流管理器] 加载云端工作流失败:", err);
            alert("加载云端工作流失败：" + err);
        });
}

// New function: Refresh cloud workflow list (clear cache and reload)
async function refreshCloudWorkflows() {
    console.log("[工作流管理器] 刷新云端工作流列表...");
    try {
        // Send request to backend to clear cache
        const response = await fetch("/workflow_manager/clear_remote_cache", {
            method: 'POST' // Use POST method to clear cache
        });
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const result = await response.json();
        console.log("[工作流管理器] 清除云端缓存结果:", result);

        // After successful clear, reload cloud workflow list
        const cloudContent = document.getElementById('workflow-cloud-content');
        if (cloudContent) {
            // Before loading, ensure the controls (search/refresh) are visible for this tab
             const controlsContainer = cloudContent.parentElement.previousElementSibling; // Get the controls container (previous sibling of contentContainer)
             if(controlsContainer && controlsContainer.classList.contains('workflow-controls-container')){
                 controlsContainer.querySelector('.workflow-search-input').placeholder = "搜索云端工作流...";
                 controlsContainer.querySelector('.workflow-refresh-button').style.display = '';
             }
            loadCloudWorkflows(cloudContent);
        }

    } catch (error) {
        console.error("[工作流管理器] 刷新云端工作流失败:", error);
        alert("刷新云端工作流失败：" + error);
    }
}
