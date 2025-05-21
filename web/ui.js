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
                // 创建面板内容
                const panel = document.createElement("div");
                panel.className = "workflow-manager-panel";
                panel.style = `
                    padding: 10px;
                    color: white;
                    font-family: sans-serif;
                `;

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

                    .workflow-manager-content { /* 内容区域样式 */
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
                `;
                el.appendChild(style);

                // 搜索框
                const searchInput = document.createElement("input");
                searchInput.type = "text";
                searchInput.placeholder = "搜索工作流...";
                searchInput.className = "workflow-search-input";
                searchInput.style = "";
                searchInput.oninput = () => filterResults(searchInput.value.toLowerCase());

                // 内容区域
                const content = document.createElement("div");
                content.id = "workflow-content";
                content.className = "workflow-content";
                content.style = "";

                // 加载工作流列表
                try {
                    const response = await fetch("/workflow_manager/list");
                    if (!response.ok) {
                        throw new Error(`HTTP error! status: ${response.status}`);
                    }
                    const data = await response.json();
                    renderFolders(data, content);
                } catch (error) {
                    console.error("获取工作流列表失败:", error);
                    content.innerHTML = `<div style="color: red;">获取工作流列表失败，请检查控制台获取详细信息</div>`;
                }

                // 组合面板
                panel.appendChild(searchInput);
                panel.appendChild(content);
                el.appendChild(panel);
            }
        });
    }
});

function renderFolders(data, container) {
    container.innerHTML = "";

    const favorites = getFavorites();

    // 渲染收藏夹
    const favSection = document.createElement("div");
    favSection.className = "workflow-favorites-section";
    favSection.style = "";
    favSection.innerHTML = "<strong>⭐ 收藏夹</strong>";
    favorites.forEach(path => {
        const favItem = document.createElement("div");
        favItem.className = "workflow-fav-item";
        favItem.style = "";
        favItem.innerText = path;
        favItem.onclick = () => loadWorkflow(path);
        favSection.appendChild(favItem);
    });
    container.prepend(favSection);

    data.forEach(folder => {
        const folderElem = document.createElement("div");
        folderElem.className = "workflow-folder";
        folderElem.style = "";
        folderElem.innerHTML = `📁 ${folder.name}`;

        folder.files.forEach(file => {
            const fullPath = `${folder.name}/${file}`;
            const isFav = favorites.includes(fullPath);

            const fileElem = document.createElement("div");
            fileElem.className = "workflow-file-item";
            fileElem.style = "";

            const title = document.createElement("span");
            title.innerText = file;
            title.className = "workflow-file-title";
            title.style = "";
            title.onclick = () => loadWorkflow(fullPath);

            const favBtn = document.createElement("span");
            favBtn.innerText = isFav ? "★" : "☆";
            favBtn.className = "workflow-fav-btn";
            favBtn.style = "";
            favBtn.onclick = () => toggleFavorite(fullPath, favBtn);

            fileElem.appendChild(title);
            fileElem.appendChild(favBtn);
            folderElem.appendChild(fileElem);
        });

        container.appendChild(folderElem);
    });
}

function filterResults(keyword) {
    const allFolders = document.querySelectorAll("#workflow-content > div");
    allFolders.forEach(folder => {
        const text = folder.innerText.toLowerCase();
        folder.style.display = text.includes(keyword) ? "" : "none";
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

function loadWorkflow(relPath) {
    console.log("[工作流管理器] 开始加载工作流:", relPath);
    fetch(`/workflow_manager/workflows/${relPath}`)
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(json => {
            console.log("[工作流管理器] 工作流加载成功:", json);
            app.loadGraphData(json);
            alert("已加载：" + relPath);
        })
        .catch(err => {
            console.error("[工作流管理器] 加载失败:", err);
            alert("加载失败：" + err);
        });
}
