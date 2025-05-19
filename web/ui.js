import { app } from "../../scripts/app.js";

app.registerExtension({
    name: "ComfyUI.WorkflowManager",
    async setup() {
        // 创建菜单按钮
        const menuButton = document.createElement("button");
        menuButton.id = "workflow-manager-btn";
        menuButton.innerText = "工作流管理器";
        menuButton.style = "margin: 5px; padding: 5px 10px; background: #4a4a4a; color: white; border: none; border-radius: 4px; cursor: pointer;";
        menuButton.onclick = openPanel;

        // 等待 ComfyUI 完全加载
        const waitForComfy = () => {
            return new Promise((resolve) => {
                const check = () => {
                    const menu = document.querySelector(".comfyui-menu");
                    if (menu) {
                        resolve(menu);
                    } else {
                        setTimeout(check, 100);
                    }
                };
                check();
            });
        };

        // 初始化函数
        async function initialize() {
            try {
                const menu = await waitForComfy();
                
                // 检查是否已经存在按钮
                if (document.querySelector("#workflow-manager-btn")) {
                    return;
                }

                // 添加到菜单
                menu.appendChild(menuButton);
                console.log("工作流管理器按钮已添加到顶部菜单");
            } catch (error) {
                console.error("工作流管理器初始化失败:", error);
            }
        }

        function openPanel() {
            fetch("/workflow_manager/list")
                .then(response => {
                    if (!response.ok) {
                        throw new Error(`HTTP error! status: ${response.status}`);
                    }
                    return response.json();
                })
                .then(data => {
                    showWorkflowPanel(data);
                })
                .catch(error => {
                    console.error("获取工作流列表失败:", error);
                    alert("获取工作流列表失败，请检查控制台获取详细信息");
                });
        }

        function showWorkflowPanel(data) {
            // 移除旧面板（如果有）
            const old = document.getElementById("workflow-panel");
            if (old) old.remove();

            const panel = document.createElement("div");
            panel.id = "workflow-panel";
            panel.style = `
                position: fixed; right: 0; top: 0; width: 320px; height: 100%;
                background: #1e1e1e; color: white; overflow: auto; z-index: 9999;
                border-left: 1px solid #333; font-family: sans-serif;
            `;

            // 面板头部
            const header = document.createElement("div");
            header.style = "padding: 10px; display: flex; align-items: center; justify-content: space-between;";
            header.innerHTML = `
                <h3 style="margin: 0;">工作流管理器</h3>
                <button id="close-panel" style="background: #444; color: white; border: none; padding: 5px 10px; cursor: pointer;">关闭</button>
            `;
            header.querySelector("#close-panel").onclick = () => panel.remove();

            // 搜索框
            const searchInput = document.createElement("input");
            searchInput.placeholder = "搜索工作流...";
            searchInput.style = "width: 90%; margin: 10px auto; display: block; padding: 5px;";
            searchInput.oninput = () => filterResults(searchInput.value.toLowerCase());

            // 内容区域
            const content = document.createElement("div");
            content.id = "workflow-content";
            content.style = "padding: 0 10px 20px";

            // 渲染结构
            renderFolders(data, content);

            // 组合
            panel.appendChild(header);
            panel.appendChild(searchInput);
            panel.appendChild(content);
            document.body.appendChild(panel);
        }

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

        // 启动初始化
        initialize();
    }
});
