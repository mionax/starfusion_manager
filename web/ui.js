(function () {
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
        const panel = document.createElement("div");
        panel.style.position = "fixed";
        panel.style.right = "0";
        panel.style.top = "0";
        panel.style.width = "300px";
        panel.style.height = "100%";
        panel.style.background = "#1e1e1e";
        panel.style.color = "white";
        panel.style.overflow = "auto";
        panel.style.zIndex = 9999;
        panel.innerHTML = "<h3 style='padding:10px;'>工作流管理器</h3>";

        data.forEach(folder => {
            const folderElem = document.createElement("div");
            folderElem.style.padding = "10px";
            folderElem.innerHTML = `<strong>${folder.name}</strong>`;
            folder.files.forEach(file => {
                const fileElem = document.createElement("div");
                fileElem.style.marginLeft = "20px";
                fileElem.innerText = file;
                fileElem.style.cursor = "pointer";
                fileElem.onclick = () => {
                    alert("点击了：" + file);
                    // 可拓展加载逻辑
                };
                folderElem.appendChild(fileElem);
            });
            panel.appendChild(folderElem);
        });

        const closeBtn = document.createElement("button");
        closeBtn.innerText = "关闭";
        closeBtn.style.position = "absolute";
        closeBtn.style.top = "10px";
        closeBtn.style.right = "10px";
        closeBtn.onclick = () => panel.remove();
        panel.appendChild(closeBtn);

        document.body.appendChild(panel);
    }
})();
