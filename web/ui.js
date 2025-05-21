import { app } from "../../scripts/app.js";

app.registerExtension({
    name: "ComfyUI.WorkflowManager",
    async setup() {
        // 注册侧边栏标签
        app.extensionManager.registerSidebarTab({
            id: 'workflow-manager',
            icon: 'pi pi-folder',  // 使用 PrimeIcons 图标
            title: '工作流管理器',
            tooltip: '管理工作流文件',
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
                        overflow-y: auto; /* 允许滚动 */
                        display: flex; /* 使用 flexbox 布局 */
                        flex-direction: column; /* 垂直排列 */
                    }
                    .workflow-manager-tabs {
                        display: flex;
                        margin-bottom: 10px;
                        border-bottom: 1px solid #555;
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
                    }
                    .workflow-manager-panel input[type="text"] { /* 搜索框样式 */
                        width: 95%;
                        margin: 10px auto;
                        display: block;
                        padding: 8px;
                        border: 1px solid #555;
                        border-radius: 4px;
                        background-color: #3c3c3c;
                        color: white;
                        font-size: 1em;
                    }
                    .workflow-manager-panel input[type="text"]::placeholder {
                        color: #aaa;
                    }
                    .workflow-manager-panel input[type="text"]:focus {
                        outline: none;
                        border-color: #8cf;
                        box-shadow: 0 0 5px rgba(136, 204, 255, 0.5);
                    }

                    .workflow-content { /* 内容区域样式 */
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
                contentContainer.appendChild(localContent);

                 // 云端工作流内容区域
                const cloudContent = document.createElement("div");
                cloudContent.id = "workflow-cloud-content";
                cloudContent.className = "workflow-content hidden-content"; // 默认隐藏
                contentContainer.appendChild(cloudContent);


                // 搜索框 - 现在放在每个内容区域内部或者根据需要调整位置
                // 为了简单起见，先将其放在本地内容区域顶部
                const localSearchInput = document.createElement("input");
                localSearchInput.type = "text";
                localSearchInput.placeholder = "搜索本地工作流...";
                localSearchInput.className = "workflow-search-input";
                localSearchInput.oninput = () => filterResults(localSearchInput.value.toLowerCase(), '#workflow-local-content'); // 传递内容区域选择器
                localContent.appendChild(localSearchInput);

                 const cloudSearchInput = document.createElement("input");
                cloudSearchInput.type = "text";
                cloudSearchInput.placeholder = "搜索云端工作流...";
                cloudSearchInput.className = "workflow-search-input";
                cloudSearchInput.oninput = () => filterResults(cloudSearchInput.value.toLowerCase(), '#workflow-cloud-content'); // 传递内容区域选择器
                cloudContent.appendChild(cloudSearchInput);


                // Tab 切换逻辑
                localTabBtn.onclick = () => {
                    localTabBtn.classList.add('active');
                    cloudTabBtn.classList.remove('active');
                    localContent.classList.remove('hidden-content');
                    cloudContent.classList.add('hidden-content');
                    // 加载本地工作流（如果需要刷新）
                    loadLocalWorkflows(localContent);
                };

                cloudTabBtn.onclick = () => {
                    cloudTabBtn.classList.add('active');
                    localTabBtn.classList.remove('active');
                    cloudContent.classList.remove('hidden-content');
                    localContent.classList.add('hidden-content');
                    // 加载云端工作流
                    loadCloudWorkflows(cloudContent);
                };


                // 初始加载本地工作流
                loadLocalWorkflows(localContent);

                el.appendChild(panel);
            }
        });
    }
});

// 新增函数：加载并渲染本地工作流
async function loadLocalWorkflows(container) {
    container.innerHTML = ''; // 清空容器
     // 为了简单，将搜索框重新添加到加载内容之前
     const searchInput = container.querySelector('.workflow-search-input');
     if(searchInput) container.appendChild(searchInput);

    const contentDiv = document.createElement("div"); // 创建一个div来存放文件/文件夹列表，以便搜索框一直在顶部
    container.appendChild(contentDiv);

    try {
        const response = await fetch("/workflow_manager/list");
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        renderFolders(data, contentDiv, loadWorkflow); // 传递加载函数
    } catch (error) {
        console.error("获取本地工作流列表失败:", error);
        contentDiv.innerHTML = `<div style="color: red;">获取本地工作流列表失败，请检查控制台获取详细信息</div>`;
    }
}

// 新增函数：加载并渲染云端工作流
async function loadCloudWorkflows(container) {
     container.innerHTML = ''; // 清空容器
     // 为了简单，将搜索框重新添加到加载内容之前
     const searchInput = container.querySelector('.workflow-search-input');
     if(searchInput) container.appendChild(searchInput);

    const contentDiv = document.createElement("div"); // 创建一个div来存放文件/文件夹列表，以便搜索框一直在顶部
    container.appendChild(contentDiv);

    try {
        // 假设后端提供 /workflow_manager/list_remote 接口
        const response = await fetch("/workflow_manager/list_remote");
        if (!response.ok) {
             // 如果接口不存在或出错，显示友好信息
             if (response.status === 404) {
                  contentDiv.innerHTML = `<div style="color: orange;">云端工作流功能正在开发中或接口未找到。</div>`;
                  return;
             }
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        // 渲染云端工作流列表 (假设结构与本地类似)
        renderFolders(data, contentDiv, loadRemoteWorkflow); // 传递加载函数
    } catch (error) {
        console.error("获取云端工作流列表失败:", error);
        contentDiv.innerHTML = `<div style="color: red;">获取云端工作流列表失败，请检查控制台获取详细信息</div>`;
    }
}

// 修改 renderFolders 函数，使其接收加载函数作为参数
function renderFolders(data, container, loadFunc) {
    container.innerHTML = ""; // 清空容器，搜索框已在 loadXXXFunctions 中处理

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

// 修改 filterResults 函数，使其接收容器选择器
function filterResults(keyword, containerSelector) {
    const container = document.querySelector(containerSelector);
    if (!container) return;

    const allItems = container.querySelectorAll(".workflow-folder, .workflow-fav-item"); // 包括文件夹和收藏项
    allItems.forEach(item => {
        const text = item.innerText.toLowerCase();
        // 只有当item不是搜索框时才进行过滤
        if (!item.classList.contains('workflow-search-input')) {
             item.style.display = text.includes(keyword) ? "" : "none";
        }
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
