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
                panel.style = `
                    padding: 10px;
                    color: white;
                    font-family: sans-serif;
                `;

                // 搜索框
                const searchInput = document.createElement("input");
                searchInput.placeholder = "搜索工作流...";
                searchInput.style = "width: 90%; margin: 10px auto; display: block; padding: 5px;";
                searchInput.oninput = () => filterResults(searchInput.value.toLowerCase());

                // 内容区域
                const content = document.createElement("div");
                content.id = "workflow-content";
                content.style = "padding: 0 10px 20px";

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

    data.forEach(folder => {
        const folderElem = document.createElement("div");
        folderElem.innerHTML = `<div style="margin-top: 15px; font-weight: bold;">📁 ${folder.name}</div>`;

        folder.files.forEach(file => {
            const fullPath = `${folder.name}/${file}`;
            const isFav = favorites.includes(fullPath);

            const fileElem = document.createElement("div");
            fileElem.style = "margin-left: 20px; display: flex; align-items: center; justify-content: space-between;";

            const title = document.createElement("span");
            title.innerText = file;
            title.style = "cursor: pointer; color: #8cf;";
            title.onclick = () => loadWorkflow(fullPath);

            const favBtn = document.createElement("span");
            favBtn.innerText = isFav ? "★" : "☆";
            favBtn.style = "cursor: pointer; color: gold;";
            favBtn.onclick = () => toggleFavorite(fullPath, favBtn);

            fileElem.appendChild(title);
            fileElem.appendChild(favBtn);
            folderElem.appendChild(fileElem);
        });

        container.appendChild(folderElem);
    });

    // 渲染收藏夹
    const favSection = document.createElement("div");
    favSection.style = "margin-top: 20px;";
    favSection.innerHTML = "<strong>⭐ 收藏夹</strong>";
    favorites.forEach(path => {
        const favItem = document.createElement("div");
        favItem.style = "margin-left: 20px; cursor: pointer; color: #ff8;";
        favItem.innerText = path;
        favItem.onclick = () => loadWorkflow(path);
        favSection.appendChild(favItem);
    });
    container.prepend(favSection);
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
