(function () {
    // 挂载按钮
    const button = document.createElement("button");
    button.innerText = "工作流管理器";
    button.onclick = openPanel;
    document.querySelector("#sidebar").appendChild(button);

    function openPanel() {
        fetch("/workflow_manager/list")
            .then(response => response.json())
            .then(data => {
                showWorkflowPanel(data);
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
        fetch(`/custom_nodes/workflow_manager/workflows/${relPath}`)
            .then(res => res.json())
            .then(json => {
                app.loadGraphData(json);
                alert("已加载：" + relPath);
            })
            .catch(err => {
                alert("加载失败：" + err);
            });
    }
})();
