import { app } from "../../scripts/app.js";

app.registerExtension({
    name: "ComfyUI.WorkflowManager",
    async setup() {
        // 注册侧边栏标签
        app.extensionManager.registerSidebarTab({
            id: 'workflow-manager',
            icon: 'pi pi-folder',  // 使用 PrimeIcons 图标
            title: '工作流管理器',
            tooltip: '✨️星汇工作流管理器',
            type: 'custom',
            
            render: async (el) => {
                // 创建面板内容容器
                const panel = document.createElement("div");
                panel.className = "workflow-manager-panel"; // 添加类名
                // panel.style = ` ... `; // 样式移到 CSS 中

                // 添加 CSS 样式
                const style = document.createElement("style");
                style.innerHTML = `
                    .workflow-manager-panel {
                        padding: 10px;
                        color: white;
                        font-family: sans-serif;
                        background-color: #2a2a2a; /* 微深的背景 */
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
                        margin-top: 15px;
                        font-weight: bold;
                        color: #ddd;
                    }

                    .workflow-file-item { /* 文件项样式 */
                        margin-left: 20px;
                        display: flex;
                        align-items: center;
                        justify-content: space-between;
                        padding: 5px 0;
                        border-bottom: 1px solid #3a3a3a; /* 分隔线 */
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
                `;
                el.appendChild(style); // 将样式添加到元素中

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
                    localContent.classList.remove('hidden-content');
                    cloudContent.classList.add('hidden-content');
                    searchInput.placeholder = "搜索本地工作流..."; // Set placeholder
                    searchInput.oninput = () => filterResults(searchInput.value.toLowerCase(), '#workflow-local-content');
                    refreshButton.style.display = 'none'; // Hide refresh button
                    loadLocalWorkflows(localContent); // Reload local
                };

                cloudTabBtn.onclick = () => {
                    cloudTabBtn.classList.add('active');
                    localTabBtn.classList.remove('active');
                    cloudContent.classList.remove('hidden-content');
                    localContent.classList.add('hidden-content');
                     searchInput.placeholder = "搜索云端工作流..."; // Set placeholder
                    searchInput.oninput = () => filterResults(searchInput.value.toLowerCase(), '#workflow-cloud-content');
                    refreshButton.style.display = ''; // Show refresh button
                    loadCloudWorkflows(cloudContent); // Load cloud
                };


                // 初始加载本地工作流并设置初始状态
                searchInput.placeholder = "搜索本地工作流...";
                searchInput.oninput = () => filterResults(searchInput.value.toLowerCase(), '#workflow-local-content');
                loadLocalWorkflows(localContent);

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

    const favorites = getFavorites(); // 收藏夹仍然是本地的

    // 渲染收藏夹 - 仅在本地工作流 Tab 显示
    if (loadFunc === loadWorkflow) { // 判断是否是本地加载函数
        const favSection = document.createElement("div");
        favSection.className = "workflow-favorites-section"; // 添加类名
        // favSection.style = ""; // 清除旧的inline样式
        favSection.innerHTML = "<strong>⭐ 收藏夹</strong>";
        favorites.forEach(path => {
            const favItem = document.createElement("div");
            favItem.className = "workflow-fav-item"; // 添加类名
            // favItem.style = ""; // 清除旧的inline样式
            favItem.innerText = path;
            favItem.onclick = () => loadFunc(path); // 使用传入的加载函数
            favSection.appendChild(favItem);
        });
        container.prepend(favSection); // 将收藏夹放到最前面
    }

    data.forEach(folder => {
        const folderElem = document.createElement("div");
        folderElem.className = "workflow-folder"; // 添加类名
        // folderElem.style = ""; // 清除旧的inline样式
        folderElem.innerHTML = `📁 ${folder.name}`; // 直接设置文本，避免嵌套div

        folder.files.forEach(file => {
            const fullPath = `${folder.name}/${file}`;
            const isFav = favorites.includes(fullPath);

            const fileElem = document.createElement("div");
            fileElem.className = "workflow-file-item"; // 添加类名
            // fileElem.style = ""; // 清除旧的inline样式

            const title = document.createElement("span");
            title.innerText = file;
            title.className = "workflow-file-title"; // 添加类名
            // title.style = ""; // 清除旧的inline样式
            title.onclick = () => loadFunc(fullPath); // 使用传入的加载函数

            // 收藏按钮 - 仅在本地工作流 Tab 显示
             if (loadFunc === loadWorkflow) {
                const favBtn = document.createElement("span");
                favBtn.innerText = isFav ? "★" : "☆";
                favBtn.className = "workflow-fav-btn"; // 添加类名
                // favBtn.style = ""; // 清除旧的inline样式
                favBtn.onclick = () => toggleFavorite(fullPath, favBtn);
                fileElem.appendChild(favBtn);
             }

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

function getFavorites() {
    try {
        return JSON.parse(localStorage.getItem("workflow_favorites") || "[]");
    } catch (e) {
        return [];
    }
}

function toggleFavorite(path, btnElem) {
    let favs = getFavorites();
    if (favs.includes(path)) {
        favs = favs.filter(p => p !== path);
        btnElem.innerText = "☆";
    } else {
        favs.push(path);
        btnElem.innerText = "★";
    }
    localStorage.setItem("workflow_favorites", JSON.stringify(favs));
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
