// PM Tool - 顶级交互逻辑

// ==================== 全局状态 ====================
const state = {
    currentView: 'dashboard',
    currentProject: null,
    screenshots: [],
    currentTab: 'download',
    previewIndex: 0,
    browseSource: 'screens' // screens | downloads
};

// ==================== 初始化 ====================
document.addEventListener('DOMContentLoaded', () => {
    loadProjects();
    checkChrome();
    
    // 如果有上次打开的项目，尝试恢复
    const lastProject = localStorage.getItem('lastProject');
    if (lastProject) {
        // openProject(lastProject); // 暂时先不自动打开，回到首页更有掌控感
    }
});

// ==================== 视图管理 ====================
function switchView(viewName) {
    document.querySelectorAll('.view').forEach(el => {
        el.classList.remove('active');
        el.style.opacity = '0';
    });
    
    const target = document.getElementById(`view-${viewName}`);
    setTimeout(() => {
        target.classList.add('active');
        target.style.opacity = '1';
    }, 200);
    
    state.currentView = viewName;
}

function goHome() {
    switchView('dashboard');
    loadProjects();
    state.currentProject = null;
    localStorage.removeItem('lastProject');
}

// ==================== Tab 切换 ====================
function switchTab(tabName) {
    // UI 更新
    document.querySelectorAll('.tab-item').forEach(el => el.classList.remove('active'));
    document.querySelector(`[data-tab="${tabName}"]`).classList.add('active');
    
    document.querySelectorAll('.tab-pane').forEach(el => el.classList.remove('active'));
    document.getElementById(`tab-${tabName}`).classList.add('active');
    
    // 逻辑处理
    state.currentTab = tabName;
    
    if (tabName === 'browse') {
        loadScreenshots();
    } else if (tabName === 'report') {
        // 自动预览报告
        generateReport(true);
    }
}

// ==================== 项目管理 ====================
function loadProjects() {
    fetch('/api/projects').then(r => r.json()).then(data => {
        const grid = document.getElementById('projects-grid');
        grid.innerHTML = data.projects.map(p => `
            <div class="project-card" onclick="openProject('${p.name}')">
                <div class="project-card-header">
                    <div class="project-icon">📱</div>
                    <button class="btn btn-ghost btn-sm" onclick="event.stopPropagation(); deleteProject('${p.name}')">×</button>
                </div>
                <div class="project-title">${p.name}</div>
                <div class="project-info">
                    <span>${p.screen_count} screens</span>
                    <span>${p.created.split(' ')[0]}</span>
                </div>
            </div>
        `).join('');
    });
}

function openProject(name) {
    state.currentProject = name;
    localStorage.setItem('lastProject', name);
    
    document.getElementById('current-project-name').innerText = name;
    switchView('workspace');
    switchTab('download'); // 默认进入采集页
    
    // 获取项目详情更新 Badge
    fetch(`/api/screenshots/${name}`).then(r => r.json()).then(data => {
        const count = data.screens.length || data.downloads.length;
        document.getElementById('current-project-count').innerText = `${count} screens`;
    });
}

function createProject() {
    const name = document.getElementById('new-project-name').value.trim();
    if (!name) return showToast('请输入项目名称');
    
    fetch('/api/projects', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({name})
    }).then(r => r.json()).then(data => {
        if (data.success) {
            closeModal();
            openProject(name);
            showToast('项目创建成功');
        } else {
            showToast(data.error);
        }
    });
}

function deleteProject(name) {
    if(!confirm(`确定删除项目 ${name}?`)) return;
    fetch(`/api/projects/${name}`, {method: 'DELETE'}).then(() => loadProjects());
}

// ==================== 采集功能 ====================
function startChrome() {
    showToast('正在启动 Chrome...', 2000);
    fetch('/api/start-chrome', {method: 'POST'}).then(() => {
        setTimeout(checkChrome, 3000);
    });
}

function checkChrome() {
    fetch('/api/check-chrome').then(r => r.json()).then(data => {
        const statusText = document.getElementById('chrome-status-text');
        if (statusText) statusText.innerText = data.available ? '已连接 (Ready)' : '未连接';
    });
}

function startDownload() {
    const url = document.getElementById('download-url').value;
    if (!url) return showToast('请输入 URL');
    
    const btn = document.getElementById('btn-download');
    const log = document.getElementById('download-progress');
    
    btn.disabled = true;
    btn.innerText = '采集进行中...';
    log.style.display = 'block';
    log.innerHTML = '<div>[INFO] 连接 Chrome...</div><div>[INFO] 开始滚动页面...</div>';
    
    fetch('/api/download', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({project_name: state.currentProject, url})
    }).then(r => r.json()).then(data => {
        btn.disabled = false;
        btn.innerText = '开始采集';
        
        if (data.success) {
            log.innerHTML += `<div>[SUCCESS] 成功采集 ${data.count} 张截图</div>`;
            showToast(`采集完成: ${data.count} 张`);
            // 自动跳转到整理 Tab
            setTimeout(() => switchTab('classify'), 1500);
        } else {
            log.innerHTML += `<div style="color:red">[ERROR] ${data.error}</div>`;
        }
    });
}

// ==================== 整理功能 ====================
function startClassify() {
    const module = document.getElementById('classify-module').value;
    
    fetch('/api/classify', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({project_name: state.currentProject, focus_module: module})
    }).then(r => r.json()).then(data => {
        if (data.success) {
            showToast(`整理完成: ${data.count} 张`);
            // 自动跳转到浏览 Tab
            setTimeout(() => switchTab('browse'), 1000);
        }
    });
}

// ==================== 浏览功能 ====================
function loadScreenshots() {
    fetch(`/api/screenshots/${state.currentProject}`).then(r => r.json()).then(data => {
        state.screenshots = state.browseSource === 'screens' ? data.screens : data.downloads;
        renderGrid();
    });
}

function switchBrowseSource(source) {
    state.browseSource = source;
    document.querySelectorAll('.toggle-btn').forEach(el => el.classList.remove('active'));
    event.target.classList.add('active');
    loadScreenshots();
}

function updateGridSize(size) {
    document.getElementById('screenshots-grid').style.gridTemplateColumns = `repeat(auto-fill, minmax(${size}px, 1fr))`;
}

function renderGrid() {
    const grid = document.getElementById('screenshots-grid');
    if (state.screenshots.length === 0) {
        grid.innerHTML = '<div class="empty-state-small">暂无截图</div>';
        return;
    }
    
    grid.innerHTML = state.screenshots.map((file, i) => `
        <div class="screenshot-card" onclick="openPreview(${i})">
            <img src="/api/screenshot/${state.currentProject}/${state.browseSource}/${file}" loading="lazy">
            <div class="screenshot-caption">${file}</div>
        </div>
    `).join('');
}

// ==================== 报告功能 ====================
function generateReport(previewOnly = false) {
    fetch('/api/generate-report', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({project_name: state.currentProject})
    }).then(r => r.json()).then(data => {
        if (data.success) {
            // 简单的 Markdown 渲染
            let html = `<h1>${state.currentProject} 分析报告</h1>`;
            html += '<table><thead><tr><th>模块</th><th>数量</th></tr></thead><tbody>';
            for(let [k,v] of Object.entries(data.categories)) {
                html += `<tr><td>${k}</td><td>${v}</td></tr>`;
            }
            html += '</tbody></table>';
            
            document.getElementById('report-preview').innerHTML = html;
            if (!previewOnly) showToast('报告已生成');
        }
    });
}

function openProjectFolder() {
    fetch('/api/open-folder', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({project_name: state.currentProject})
    });
}

// ==================== 预览弹窗 ====================
function openPreview(index) {
    state.previewIndex = index;
    updatePreviewImage();
    document.getElementById('modal-preview').classList.add('active');
    document.addEventListener('keydown', handleKey);
}

function closePreview() {
    document.getElementById('modal-preview').classList.remove('active');
    document.removeEventListener('keydown', handleKey);
}

function updatePreviewImage() {
    const file = state.screenshots[state.previewIndex];
    document.getElementById('preview-image').src = `/api/screenshot/${state.currentProject}/${state.browseSource}/${file}`;
    document.getElementById('preview-counter').innerText = `${state.previewIndex + 1} / ${state.screenshots.length}`;
}

function prevImage() {
    if (state.previewIndex > 0) {
        state.previewIndex--;
        updatePreviewImage();
    }
}

function nextImage() {
    if (state.previewIndex < state.screenshots.length - 1) {
        state.previewIndex++;
        updatePreviewImage();
    }
}

function handleKey(e) {
    if (e.key === 'ArrowLeft') prevImage();
    if (e.key === 'ArrowRight') nextImage();
    if (e.key === 'Escape') closePreview();
}

// ==================== 通用 ====================
function showCreateProject() { document.getElementById('modal-create').classList.add('active'); }
function closeModal() { document.querySelectorAll('.modal').forEach(el => el.classList.remove('active')); }

function showToast(msg, duration=3000) {
    const toast = document.getElementById('toast');
    toast.innerText = msg;
    toast.classList.add('show');
    setTimeout(() => toast.classList.remove('show'), duration);
}

// ==================== 全局状态 ====================
const state = {
    currentView: 'dashboard',
    currentProject: null,
    screenshots: [],
    currentTab: 'download',
    previewIndex: 0,
    browseSource: 'screens' // screens | downloads
};

// ==================== 初始化 ====================
document.addEventListener('DOMContentLoaded', () => {
    loadProjects();
    checkChrome();
    
    // 如果有上次打开的项目，尝试恢复
    const lastProject = localStorage.getItem('lastProject');
    if (lastProject) {
        // openProject(lastProject); // 暂时先不自动打开，回到首页更有掌控感
    }
});

// ==================== 视图管理 ====================
function switchView(viewName) {
    document.querySelectorAll('.view').forEach(el => {
        el.classList.remove('active');
        el.style.opacity = '0';
    });
    
    const target = document.getElementById(`view-${viewName}`);
    setTimeout(() => {
        target.classList.add('active');
        target.style.opacity = '1';
    }, 200);
    
    state.currentView = viewName;
}

function goHome() {
    switchView('dashboard');
    loadProjects();
    state.currentProject = null;
    localStorage.removeItem('lastProject');
}

// ==================== Tab 切换 ====================
function switchTab(tabName) {
    // UI 更新
    document.querySelectorAll('.tab-item').forEach(el => el.classList.remove('active'));
    document.querySelector(`[data-tab="${tabName}"]`).classList.add('active');
    
    document.querySelectorAll('.tab-pane').forEach(el => el.classList.remove('active'));
    document.getElementById(`tab-${tabName}`).classList.add('active');
    
    // 逻辑处理
    state.currentTab = tabName;
    
    if (tabName === 'browse') {
        loadScreenshots();
    } else if (tabName === 'report') {
        // 自动预览报告
        generateReport(true);
    }
}

// ==================== 项目管理 ====================
function loadProjects() {
    fetch('/api/projects').then(r => r.json()).then(data => {
        const grid = document.getElementById('projects-grid');
        grid.innerHTML = data.projects.map(p => `
            <div class="project-card" onclick="openProject('${p.name}')">
                <div class="project-card-header">
                    <div class="project-icon">📱</div>
                    <button class="btn btn-ghost btn-sm" onclick="event.stopPropagation(); deleteProject('${p.name}')">×</button>
                </div>
                <div class="project-title">${p.name}</div>
                <div class="project-info">
                    <span>${p.screen_count} screens</span>
                    <span>${p.created.split(' ')[0]}</span>
                </div>
            </div>
        `).join('');
    });
}

function openProject(name) {
    state.currentProject = name;
    localStorage.setItem('lastProject', name);
    
    document.getElementById('current-project-name').innerText = name;
    switchView('workspace');
    switchTab('download'); // 默认进入采集页
    
    // 获取项目详情更新 Badge
    fetch(`/api/screenshots/${name}`).then(r => r.json()).then(data => {
        const count = data.screens.length || data.downloads.length;
        document.getElementById('current-project-count').innerText = `${count} screens`;
    });
}

function createProject() {
    const name = document.getElementById('new-project-name').value.trim();
    if (!name) return showToast('请输入项目名称');
    
    fetch('/api/projects', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({name})
    }).then(r => r.json()).then(data => {
        if (data.success) {
            closeModal();
            openProject(name);
            showToast('项目创建成功');
        } else {
            showToast(data.error);
        }
    });
}

function deleteProject(name) {
    if(!confirm(`确定删除项目 ${name}?`)) return;
    fetch(`/api/projects/${name}`, {method: 'DELETE'}).then(() => loadProjects());
}

// ==================== 采集功能 ====================
function startChrome() {
    showToast('正在启动 Chrome...', 2000);
    fetch('/api/start-chrome', {method: 'POST'}).then(() => {
        setTimeout(checkChrome, 3000);
    });
}

function checkChrome() {
    fetch('/api/check-chrome').then(r => r.json()).then(data => {
        const statusText = document.getElementById('chrome-status-text');
        if (statusText) statusText.innerText = data.available ? '已连接 (Ready)' : '未连接';
    });
}

function startDownload() {
    const url = document.getElementById('download-url').value;
    if (!url) return showToast('请输入 URL');
    
    const btn = document.getElementById('btn-download');
    const log = document.getElementById('download-progress');
    
    btn.disabled = true;
    btn.innerText = '采集进行中...';
    log.style.display = 'block';
    log.innerHTML = '<div>[INFO] 连接 Chrome...</div><div>[INFO] 开始滚动页面...</div>';
    
    fetch('/api/download', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({project_name: state.currentProject, url})
    }).then(r => r.json()).then(data => {
        btn.disabled = false;
        btn.innerText = '开始采集';
        
        if (data.success) {
            log.innerHTML += `<div>[SUCCESS] 成功采集 ${data.count} 张截图</div>`;
            showToast(`采集完成: ${data.count} 张`);
            // 自动跳转到整理 Tab
            setTimeout(() => switchTab('classify'), 1500);
        } else {
            log.innerHTML += `<div style="color:red">[ERROR] ${data.error}</div>`;
        }
    });
}

// ==================== 整理功能 ====================
function startClassify() {
    const module = document.getElementById('classify-module').value;
    
    fetch('/api/classify', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({project_name: state.currentProject, focus_module: module})
    }).then(r => r.json()).then(data => {
        if (data.success) {
            showToast(`整理完成: ${data.count} 张`);
            // 自动跳转到浏览 Tab
            setTimeout(() => switchTab('browse'), 1000);
        }
    });
}

// ==================== 浏览功能 ====================
function loadScreenshots() {
    fetch(`/api/screenshots/${state.currentProject}`).then(r => r.json()).then(data => {
        state.screenshots = state.browseSource === 'screens' ? data.screens : data.downloads;
        renderGrid();
    });
}

function switchBrowseSource(source) {
    state.browseSource = source;
    document.querySelectorAll('.toggle-btn').forEach(el => el.classList.remove('active'));
    event.target.classList.add('active');
    loadScreenshots();
}

function updateGridSize(size) {
    document.getElementById('screenshots-grid').style.gridTemplateColumns = `repeat(auto-fill, minmax(${size}px, 1fr))`;
}

function renderGrid() {
    const grid = document.getElementById('screenshots-grid');
    if (state.screenshots.length === 0) {
        grid.innerHTML = '<div class="empty-state-small">暂无截图</div>';
        return;
    }
    
    grid.innerHTML = state.screenshots.map((file, i) => `
        <div class="screenshot-card" onclick="openPreview(${i})">
            <img src="/api/screenshot/${state.currentProject}/${state.browseSource}/${file}" loading="lazy">
            <div class="screenshot-caption">${file}</div>
        </div>
    `).join('');
}

// ==================== 报告功能 ====================
function generateReport(previewOnly = false) {
    fetch('/api/generate-report', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({project_name: state.currentProject})
    }).then(r => r.json()).then(data => {
        if (data.success) {
            // 简单的 Markdown 渲染
            let html = `<h1>${state.currentProject} 分析报告</h1>`;
            html += '<table><thead><tr><th>模块</th><th>数量</th></tr></thead><tbody>';
            for(let [k,v] of Object.entries(data.categories)) {
                html += `<tr><td>${k}</td><td>${v}</td></tr>`;
            }
            html += '</tbody></table>';
            
            document.getElementById('report-preview').innerHTML = html;
            if (!previewOnly) showToast('报告已生成');
        }
    });
}

function openProjectFolder() {
    fetch('/api/open-folder', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({project_name: state.currentProject})
    });
}

// ==================== 预览弹窗 ====================
function openPreview(index) {
    state.previewIndex = index;
    updatePreviewImage();
    document.getElementById('modal-preview').classList.add('active');
    document.addEventListener('keydown', handleKey);
}

function closePreview() {
    document.getElementById('modal-preview').classList.remove('active');
    document.removeEventListener('keydown', handleKey);
}

function updatePreviewImage() {
    const file = state.screenshots[state.previewIndex];
    document.getElementById('preview-image').src = `/api/screenshot/${state.currentProject}/${state.browseSource}/${file}`;
    document.getElementById('preview-counter').innerText = `${state.previewIndex + 1} / ${state.screenshots.length}`;
}

function prevImage() {
    if (state.previewIndex > 0) {
        state.previewIndex--;
        updatePreviewImage();
    }
}

function nextImage() {
    if (state.previewIndex < state.screenshots.length - 1) {
        state.previewIndex++;
        updatePreviewImage();
    }
}

function handleKey(e) {
    if (e.key === 'ArrowLeft') prevImage();
    if (e.key === 'ArrowRight') nextImage();
    if (e.key === 'Escape') closePreview();
}

// ==================== 通用 ====================
function showCreateProject() { document.getElementById('modal-create').classList.add('active'); }
function closeModal() { document.querySelectorAll('.modal').forEach(el => el.classList.remove('active')); }

function showToast(msg, duration=3000) {
    const toast = document.getElementById('toast');
    toast.innerText = msg;
    toast.classList.add('show');
    setTimeout(() => toast.classList.remove('show'), duration);
}

// ==================== 全局状态 ====================
const state = {
    currentView: 'dashboard',
    currentProject: null,
    screenshots: [],
    currentTab: 'download',
    previewIndex: 0,
    browseSource: 'screens' // screens | downloads
};

// ==================== 初始化 ====================
document.addEventListener('DOMContentLoaded', () => {
    loadProjects();
    checkChrome();
    
    // 如果有上次打开的项目，尝试恢复
    const lastProject = localStorage.getItem('lastProject');
    if (lastProject) {
        // openProject(lastProject); // 暂时先不自动打开，回到首页更有掌控感
    }
});

// ==================== 视图管理 ====================
function switchView(viewName) {
    document.querySelectorAll('.view').forEach(el => {
        el.classList.remove('active');
        el.style.opacity = '0';
    });
    
    const target = document.getElementById(`view-${viewName}`);
    setTimeout(() => {
        target.classList.add('active');
        target.style.opacity = '1';
    }, 200);
    
    state.currentView = viewName;
}

function goHome() {
    switchView('dashboard');
    loadProjects();
    state.currentProject = null;
    localStorage.removeItem('lastProject');
}

// ==================== Tab 切换 ====================
function switchTab(tabName) {
    // UI 更新
    document.querySelectorAll('.tab-item').forEach(el => el.classList.remove('active'));
    document.querySelector(`[data-tab="${tabName}"]`).classList.add('active');
    
    document.querySelectorAll('.tab-pane').forEach(el => el.classList.remove('active'));
    document.getElementById(`tab-${tabName}`).classList.add('active');
    
    // 逻辑处理
    state.currentTab = tabName;
    
    if (tabName === 'browse') {
        loadScreenshots();
    } else if (tabName === 'report') {
        // 自动预览报告
        generateReport(true);
    }
}

// ==================== 项目管理 ====================
function loadProjects() {
    fetch('/api/projects').then(r => r.json()).then(data => {
        const grid = document.getElementById('projects-grid');
        grid.innerHTML = data.projects.map(p => `
            <div class="project-card" onclick="openProject('${p.name}')">
                <div class="project-card-header">
                    <div class="project-icon">📱</div>
                    <button class="btn btn-ghost btn-sm" onclick="event.stopPropagation(); deleteProject('${p.name}')">×</button>
                </div>
                <div class="project-title">${p.name}</div>
                <div class="project-info">
                    <span>${p.screen_count} screens</span>
                    <span>${p.created.split(' ')[0]}</span>
                </div>
            </div>
        `).join('');
    });
}

function openProject(name) {
    state.currentProject = name;
    localStorage.setItem('lastProject', name);
    
    document.getElementById('current-project-name').innerText = name;
    switchView('workspace');
    switchTab('download'); // 默认进入采集页
    
    // 获取项目详情更新 Badge
    fetch(`/api/screenshots/${name}`).then(r => r.json()).then(data => {
        const count = data.screens.length || data.downloads.length;
        document.getElementById('current-project-count').innerText = `${count} screens`;
    });
}

function createProject() {
    const name = document.getElementById('new-project-name').value.trim();
    if (!name) return showToast('请输入项目名称');
    
    fetch('/api/projects', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({name})
    }).then(r => r.json()).then(data => {
        if (data.success) {
            closeModal();
            openProject(name);
            showToast('项目创建成功');
        } else {
            showToast(data.error);
        }
    });
}

function deleteProject(name) {
    if(!confirm(`确定删除项目 ${name}?`)) return;
    fetch(`/api/projects/${name}`, {method: 'DELETE'}).then(() => loadProjects());
}

// ==================== 采集功能 ====================
function startChrome() {
    showToast('正在启动 Chrome...', 2000);
    fetch('/api/start-chrome', {method: 'POST'}).then(() => {
        setTimeout(checkChrome, 3000);
    });
}

function checkChrome() {
    fetch('/api/check-chrome').then(r => r.json()).then(data => {
        const statusText = document.getElementById('chrome-status-text');
        if (statusText) statusText.innerText = data.available ? '已连接 (Ready)' : '未连接';
    });
}

function startDownload() {
    const url = document.getElementById('download-url').value;
    if (!url) return showToast('请输入 URL');
    
    const btn = document.getElementById('btn-download');
    const log = document.getElementById('download-progress');
    
    btn.disabled = true;
    btn.innerText = '采集进行中...';
    log.style.display = 'block';
    log.innerHTML = '<div>[INFO] 连接 Chrome...</div><div>[INFO] 开始滚动页面...</div>';
    
    fetch('/api/download', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({project_name: state.currentProject, url})
    }).then(r => r.json()).then(data => {
        btn.disabled = false;
        btn.innerText = '开始采集';
        
        if (data.success) {
            log.innerHTML += `<div>[SUCCESS] 成功采集 ${data.count} 张截图</div>`;
            showToast(`采集完成: ${data.count} 张`);
            // 自动跳转到整理 Tab
            setTimeout(() => switchTab('classify'), 1500);
        } else {
            log.innerHTML += `<div style="color:red">[ERROR] ${data.error}</div>`;
        }
    });
}

// ==================== 整理功能 ====================
function startClassify() {
    const module = document.getElementById('classify-module').value;
    
    fetch('/api/classify', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({project_name: state.currentProject, focus_module: module})
    }).then(r => r.json()).then(data => {
        if (data.success) {
            showToast(`整理完成: ${data.count} 张`);
            // 自动跳转到浏览 Tab
            setTimeout(() => switchTab('browse'), 1000);
        }
    });
}

// ==================== 浏览功能 ====================
function loadScreenshots() {
    fetch(`/api/screenshots/${state.currentProject}`).then(r => r.json()).then(data => {
        state.screenshots = state.browseSource === 'screens' ? data.screens : data.downloads;
        renderGrid();
    });
}

function switchBrowseSource(source) {
    state.browseSource = source;
    document.querySelectorAll('.toggle-btn').forEach(el => el.classList.remove('active'));
    event.target.classList.add('active');
    loadScreenshots();
}

function updateGridSize(size) {
    document.getElementById('screenshots-grid').style.gridTemplateColumns = `repeat(auto-fill, minmax(${size}px, 1fr))`;
}

function renderGrid() {
    const grid = document.getElementById('screenshots-grid');
    if (state.screenshots.length === 0) {
        grid.innerHTML = '<div class="empty-state-small">暂无截图</div>';
        return;
    }
    
    grid.innerHTML = state.screenshots.map((file, i) => `
        <div class="screenshot-card" onclick="openPreview(${i})">
            <img src="/api/screenshot/${state.currentProject}/${state.browseSource}/${file}" loading="lazy">
            <div class="screenshot-caption">${file}</div>
        </div>
    `).join('');
}

// ==================== 报告功能 ====================
function generateReport(previewOnly = false) {
    fetch('/api/generate-report', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({project_name: state.currentProject})
    }).then(r => r.json()).then(data => {
        if (data.success) {
            // 简单的 Markdown 渲染
            let html = `<h1>${state.currentProject} 分析报告</h1>`;
            html += '<table><thead><tr><th>模块</th><th>数量</th></tr></thead><tbody>';
            for(let [k,v] of Object.entries(data.categories)) {
                html += `<tr><td>${k}</td><td>${v}</td></tr>`;
            }
            html += '</tbody></table>';
            
            document.getElementById('report-preview').innerHTML = html;
            if (!previewOnly) showToast('报告已生成');
        }
    });
}

function openProjectFolder() {
    fetch('/api/open-folder', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({project_name: state.currentProject})
    });
}

// ==================== 预览弹窗 ====================
function openPreview(index) {
    state.previewIndex = index;
    updatePreviewImage();
    document.getElementById('modal-preview').classList.add('active');
    document.addEventListener('keydown', handleKey);
}

function closePreview() {
    document.getElementById('modal-preview').classList.remove('active');
    document.removeEventListener('keydown', handleKey);
}

function updatePreviewImage() {
    const file = state.screenshots[state.previewIndex];
    document.getElementById('preview-image').src = `/api/screenshot/${state.currentProject}/${state.browseSource}/${file}`;
    document.getElementById('preview-counter').innerText = `${state.previewIndex + 1} / ${state.screenshots.length}`;
}

function prevImage() {
    if (state.previewIndex > 0) {
        state.previewIndex--;
        updatePreviewImage();
    }
}

function nextImage() {
    if (state.previewIndex < state.screenshots.length - 1) {
        state.previewIndex++;
        updatePreviewImage();
    }
}

function handleKey(e) {
    if (e.key === 'ArrowLeft') prevImage();
    if (e.key === 'ArrowRight') nextImage();
    if (e.key === 'Escape') closePreview();
}

// ==================== 通用 ====================
function showCreateProject() { document.getElementById('modal-create').classList.add('active'); }
function closeModal() { document.querySelectorAll('.modal').forEach(el => el.classList.remove('active')); }

function showToast(msg, duration=3000) {
    const toast = document.getElementById('toast');
    toast.innerText = msg;
    toast.classList.add('show');
    setTimeout(() => toast.classList.remove('show'), duration);
}

// ==================== 全局状态 ====================
const state = {
    currentView: 'dashboard',
    currentProject: null,
    screenshots: [],
    currentTab: 'download',
    previewIndex: 0,
    browseSource: 'screens' // screens | downloads
};

// ==================== 初始化 ====================
document.addEventListener('DOMContentLoaded', () => {
    loadProjects();
    checkChrome();
    
    // 如果有上次打开的项目，尝试恢复
    const lastProject = localStorage.getItem('lastProject');
    if (lastProject) {
        // openProject(lastProject); // 暂时先不自动打开，回到首页更有掌控感
    }
});

// ==================== 视图管理 ====================
function switchView(viewName) {
    document.querySelectorAll('.view').forEach(el => {
        el.classList.remove('active');
        el.style.opacity = '0';
    });
    
    const target = document.getElementById(`view-${viewName}`);
    setTimeout(() => {
        target.classList.add('active');
        target.style.opacity = '1';
    }, 200);
    
    state.currentView = viewName;
}

function goHome() {
    switchView('dashboard');
    loadProjects();
    state.currentProject = null;
    localStorage.removeItem('lastProject');
}

// ==================== Tab 切换 ====================
function switchTab(tabName) {
    // UI 更新
    document.querySelectorAll('.tab-item').forEach(el => el.classList.remove('active'));
    document.querySelector(`[data-tab="${tabName}"]`).classList.add('active');
    
    document.querySelectorAll('.tab-pane').forEach(el => el.classList.remove('active'));
    document.getElementById(`tab-${tabName}`).classList.add('active');
    
    // 逻辑处理
    state.currentTab = tabName;
    
    if (tabName === 'browse') {
        loadScreenshots();
    } else if (tabName === 'report') {
        // 自动预览报告
        generateReport(true);
    }
}

// ==================== 项目管理 ====================
function loadProjects() {
    fetch('/api/projects').then(r => r.json()).then(data => {
        const grid = document.getElementById('projects-grid');
        grid.innerHTML = data.projects.map(p => `
            <div class="project-card" onclick="openProject('${p.name}')">
                <div class="project-card-header">
                    <div class="project-icon">📱</div>
                    <button class="btn btn-ghost btn-sm" onclick="event.stopPropagation(); deleteProject('${p.name}')">×</button>
                </div>
                <div class="project-title">${p.name}</div>
                <div class="project-info">
                    <span>${p.screen_count} screens</span>
                    <span>${p.created.split(' ')[0]}</span>
                </div>
            </div>
        `).join('');
    });
}

function openProject(name) {
    state.currentProject = name;
    localStorage.setItem('lastProject', name);
    
    document.getElementById('current-project-name').innerText = name;
    switchView('workspace');
    switchTab('download'); // 默认进入采集页
    
    // 获取项目详情更新 Badge
    fetch(`/api/screenshots/${name}`).then(r => r.json()).then(data => {
        const count = data.screens.length || data.downloads.length;
        document.getElementById('current-project-count').innerText = `${count} screens`;
    });
}

function createProject() {
    const name = document.getElementById('new-project-name').value.trim();
    if (!name) return showToast('请输入项目名称');
    
    fetch('/api/projects', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({name})
    }).then(r => r.json()).then(data => {
        if (data.success) {
            closeModal();
            openProject(name);
            showToast('项目创建成功');
        } else {
            showToast(data.error);
        }
    });
}

function deleteProject(name) {
    if(!confirm(`确定删除项目 ${name}?`)) return;
    fetch(`/api/projects/${name}`, {method: 'DELETE'}).then(() => loadProjects());
}

// ==================== 采集功能 ====================
function startChrome() {
    showToast('正在启动 Chrome...', 2000);
    fetch('/api/start-chrome', {method: 'POST'}).then(() => {
        setTimeout(checkChrome, 3000);
    });
}

function checkChrome() {
    fetch('/api/check-chrome').then(r => r.json()).then(data => {
        const statusText = document.getElementById('chrome-status-text');
        if (statusText) statusText.innerText = data.available ? '已连接 (Ready)' : '未连接';
    });
}

function startDownload() {
    const url = document.getElementById('download-url').value;
    if (!url) return showToast('请输入 URL');
    
    const btn = document.getElementById('btn-download');
    const log = document.getElementById('download-progress');
    
    btn.disabled = true;
    btn.innerText = '采集进行中...';
    log.style.display = 'block';
    log.innerHTML = '<div>[INFO] 连接 Chrome...</div><div>[INFO] 开始滚动页面...</div>';
    
    fetch('/api/download', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({project_name: state.currentProject, url})
    }).then(r => r.json()).then(data => {
        btn.disabled = false;
        btn.innerText = '开始采集';
        
        if (data.success) {
            log.innerHTML += `<div>[SUCCESS] 成功采集 ${data.count} 张截图</div>`;
            showToast(`采集完成: ${data.count} 张`);
            // 自动跳转到整理 Tab
            setTimeout(() => switchTab('classify'), 1500);
        } else {
            log.innerHTML += `<div style="color:red">[ERROR] ${data.error}</div>`;
        }
    });
}

// ==================== 整理功能 ====================
function startClassify() {
    const module = document.getElementById('classify-module').value;
    
    fetch('/api/classify', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({project_name: state.currentProject, focus_module: module})
    }).then(r => r.json()).then(data => {
        if (data.success) {
            showToast(`整理完成: ${data.count} 张`);
            // 自动跳转到浏览 Tab
            setTimeout(() => switchTab('browse'), 1000);
        }
    });
}

// ==================== 浏览功能 ====================
function loadScreenshots() {
    fetch(`/api/screenshots/${state.currentProject}`).then(r => r.json()).then(data => {
        state.screenshots = state.browseSource === 'screens' ? data.screens : data.downloads;
        renderGrid();
    });
}

function switchBrowseSource(source) {
    state.browseSource = source;
    document.querySelectorAll('.toggle-btn').forEach(el => el.classList.remove('active'));
    event.target.classList.add('active');
    loadScreenshots();
}

function updateGridSize(size) {
    document.getElementById('screenshots-grid').style.gridTemplateColumns = `repeat(auto-fill, minmax(${size}px, 1fr))`;
}

function renderGrid() {
    const grid = document.getElementById('screenshots-grid');
    if (state.screenshots.length === 0) {
        grid.innerHTML = '<div class="empty-state-small">暂无截图</div>';
        return;
    }
    
    grid.innerHTML = state.screenshots.map((file, i) => `
        <div class="screenshot-card" onclick="openPreview(${i})">
            <img src="/api/screenshot/${state.currentProject}/${state.browseSource}/${file}" loading="lazy">
            <div class="screenshot-caption">${file}</div>
        </div>
    `).join('');
}

// ==================== 报告功能 ====================
function generateReport(previewOnly = false) {
    fetch('/api/generate-report', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({project_name: state.currentProject})
    }).then(r => r.json()).then(data => {
        if (data.success) {
            // 简单的 Markdown 渲染
            let html = `<h1>${state.currentProject} 分析报告</h1>`;
            html += '<table><thead><tr><th>模块</th><th>数量</th></tr></thead><tbody>';
            for(let [k,v] of Object.entries(data.categories)) {
                html += `<tr><td>${k}</td><td>${v}</td></tr>`;
            }
            html += '</tbody></table>';
            
            document.getElementById('report-preview').innerHTML = html;
            if (!previewOnly) showToast('报告已生成');
        }
    });
}

function openProjectFolder() {
    fetch('/api/open-folder', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({project_name: state.currentProject})
    });
}

// ==================== 预览弹窗 ====================
function openPreview(index) {
    state.previewIndex = index;
    updatePreviewImage();
    document.getElementById('modal-preview').classList.add('active');
    document.addEventListener('keydown', handleKey);
}

function closePreview() {
    document.getElementById('modal-preview').classList.remove('active');
    document.removeEventListener('keydown', handleKey);
}

function updatePreviewImage() {
    const file = state.screenshots[state.previewIndex];
    document.getElementById('preview-image').src = `/api/screenshot/${state.currentProject}/${state.browseSource}/${file}`;
    document.getElementById('preview-counter').innerText = `${state.previewIndex + 1} / ${state.screenshots.length}`;
}

function prevImage() {
    if (state.previewIndex > 0) {
        state.previewIndex--;
        updatePreviewImage();
    }
}

function nextImage() {
    if (state.previewIndex < state.screenshots.length - 1) {
        state.previewIndex++;
        updatePreviewImage();
    }
}

function handleKey(e) {
    if (e.key === 'ArrowLeft') prevImage();
    if (e.key === 'ArrowRight') nextImage();
    if (e.key === 'Escape') closePreview();
}

// ==================== 通用 ====================
function showCreateProject() { document.getElementById('modal-create').classList.add('active'); }
function closeModal() { document.querySelectorAll('.modal').forEach(el => el.classList.remove('active')); }

function showToast(msg, duration=3000) {
    const toast = document.getElementById('toast');
    toast.innerText = msg;
    toast.classList.add('show');
    setTimeout(() => toast.classList.remove('show'), duration);
}

// ==================== 全局状态 ====================
const state = {
    currentView: 'dashboard',
    currentProject: null,
    screenshots: [],
    currentTab: 'download',
    previewIndex: 0,
    browseSource: 'screens' // screens | downloads
};

// ==================== 初始化 ====================
document.addEventListener('DOMContentLoaded', () => {
    loadProjects();
    checkChrome();
    
    // 如果有上次打开的项目，尝试恢复
    const lastProject = localStorage.getItem('lastProject');
    if (lastProject) {
        // openProject(lastProject); // 暂时先不自动打开，回到首页更有掌控感
    }
});

// ==================== 视图管理 ====================
function switchView(viewName) {
    document.querySelectorAll('.view').forEach(el => {
        el.classList.remove('active');
        el.style.opacity = '0';
    });
    
    const target = document.getElementById(`view-${viewName}`);
    setTimeout(() => {
        target.classList.add('active');
        target.style.opacity = '1';
    }, 200);
    
    state.currentView = viewName;
}

function goHome() {
    switchView('dashboard');
    loadProjects();
    state.currentProject = null;
    localStorage.removeItem('lastProject');
}

// ==================== Tab 切换 ====================
function switchTab(tabName) {
    // UI 更新
    document.querySelectorAll('.tab-item').forEach(el => el.classList.remove('active'));
    document.querySelector(`[data-tab="${tabName}"]`).classList.add('active');
    
    document.querySelectorAll('.tab-pane').forEach(el => el.classList.remove('active'));
    document.getElementById(`tab-${tabName}`).classList.add('active');
    
    // 逻辑处理
    state.currentTab = tabName;
    
    if (tabName === 'browse') {
        loadScreenshots();
    } else if (tabName === 'report') {
        // 自动预览报告
        generateReport(true);
    }
}

// ==================== 项目管理 ====================
function loadProjects() {
    fetch('/api/projects').then(r => r.json()).then(data => {
        const grid = document.getElementById('projects-grid');
        grid.innerHTML = data.projects.map(p => `
            <div class="project-card" onclick="openProject('${p.name}')">
                <div class="project-card-header">
                    <div class="project-icon">📱</div>
                    <button class="btn btn-ghost btn-sm" onclick="event.stopPropagation(); deleteProject('${p.name}')">×</button>
                </div>
                <div class="project-title">${p.name}</div>
                <div class="project-info">
                    <span>${p.screen_count} screens</span>
                    <span>${p.created.split(' ')[0]}</span>
                </div>
            </div>
        `).join('');
    });
}

function openProject(name) {
    state.currentProject = name;
    localStorage.setItem('lastProject', name);
    
    document.getElementById('current-project-name').innerText = name;
    switchView('workspace');
    switchTab('download'); // 默认进入采集页
    
    // 获取项目详情更新 Badge
    fetch(`/api/screenshots/${name}`).then(r => r.json()).then(data => {
        const count = data.screens.length || data.downloads.length;
        document.getElementById('current-project-count').innerText = `${count} screens`;
    });
}

function createProject() {
    const name = document.getElementById('new-project-name').value.trim();
    if (!name) return showToast('请输入项目名称');
    
    fetch('/api/projects', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({name})
    }).then(r => r.json()).then(data => {
        if (data.success) {
            closeModal();
            openProject(name);
            showToast('项目创建成功');
        } else {
            showToast(data.error);
        }
    });
}

function deleteProject(name) {
    if(!confirm(`确定删除项目 ${name}?`)) return;
    fetch(`/api/projects/${name}`, {method: 'DELETE'}).then(() => loadProjects());
}

// ==================== 采集功能 ====================
function startChrome() {
    showToast('正在启动 Chrome...', 2000);
    fetch('/api/start-chrome', {method: 'POST'}).then(() => {
        setTimeout(checkChrome, 3000);
    });
}

function checkChrome() {
    fetch('/api/check-chrome').then(r => r.json()).then(data => {
        const statusText = document.getElementById('chrome-status-text');
        if (statusText) statusText.innerText = data.available ? '已连接 (Ready)' : '未连接';
    });
}

function startDownload() {
    const url = document.getElementById('download-url').value;
    if (!url) return showToast('请输入 URL');
    
    const btn = document.getElementById('btn-download');
    const log = document.getElementById('download-progress');
    
    btn.disabled = true;
    btn.innerText = '采集进行中...';
    log.style.display = 'block';
    log.innerHTML = '<div>[INFO] 连接 Chrome...</div><div>[INFO] 开始滚动页面...</div>';
    
    fetch('/api/download', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({project_name: state.currentProject, url})
    }).then(r => r.json()).then(data => {
        btn.disabled = false;
        btn.innerText = '开始采集';
        
        if (data.success) {
            log.innerHTML += `<div>[SUCCESS] 成功采集 ${data.count} 张截图</div>`;
            showToast(`采集完成: ${data.count} 张`);
            // 自动跳转到整理 Tab
            setTimeout(() => switchTab('classify'), 1500);
        } else {
            log.innerHTML += `<div style="color:red">[ERROR] ${data.error}</div>`;
        }
    });
}

// ==================== 整理功能 ====================
function startClassify() {
    const module = document.getElementById('classify-module').value;
    
    fetch('/api/classify', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({project_name: state.currentProject, focus_module: module})
    }).then(r => r.json()).then(data => {
        if (data.success) {
            showToast(`整理完成: ${data.count} 张`);
            // 自动跳转到浏览 Tab
            setTimeout(() => switchTab('browse'), 1000);
        }
    });
}

// ==================== 浏览功能 ====================
function loadScreenshots() {
    fetch(`/api/screenshots/${state.currentProject}`).then(r => r.json()).then(data => {
        state.screenshots = state.browseSource === 'screens' ? data.screens : data.downloads;
        renderGrid();
    });
}

function switchBrowseSource(source) {
    state.browseSource = source;
    document.querySelectorAll('.toggle-btn').forEach(el => el.classList.remove('active'));
    event.target.classList.add('active');
    loadScreenshots();
}

function updateGridSize(size) {
    document.getElementById('screenshots-grid').style.gridTemplateColumns = `repeat(auto-fill, minmax(${size}px, 1fr))`;
}

function renderGrid() {
    const grid = document.getElementById('screenshots-grid');
    if (state.screenshots.length === 0) {
        grid.innerHTML = '<div class="empty-state-small">暂无截图</div>';
        return;
    }
    
    grid.innerHTML = state.screenshots.map((file, i) => `
        <div class="screenshot-card" onclick="openPreview(${i})">
            <img src="/api/screenshot/${state.currentProject}/${state.browseSource}/${file}" loading="lazy">
            <div class="screenshot-caption">${file}</div>
        </div>
    `).join('');
}

// ==================== 报告功能 ====================
function generateReport(previewOnly = false) {
    fetch('/api/generate-report', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({project_name: state.currentProject})
    }).then(r => r.json()).then(data => {
        if (data.success) {
            // 简单的 Markdown 渲染
            let html = `<h1>${state.currentProject} 分析报告</h1>`;
            html += '<table><thead><tr><th>模块</th><th>数量</th></tr></thead><tbody>';
            for(let [k,v] of Object.entries(data.categories)) {
                html += `<tr><td>${k}</td><td>${v}</td></tr>`;
            }
            html += '</tbody></table>';
            
            document.getElementById('report-preview').innerHTML = html;
            if (!previewOnly) showToast('报告已生成');
        }
    });
}

function openProjectFolder() {
    fetch('/api/open-folder', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({project_name: state.currentProject})
    });
}

// ==================== 预览弹窗 ====================
function openPreview(index) {
    state.previewIndex = index;
    updatePreviewImage();
    document.getElementById('modal-preview').classList.add('active');
    document.addEventListener('keydown', handleKey);
}

function closePreview() {
    document.getElementById('modal-preview').classList.remove('active');
    document.removeEventListener('keydown', handleKey);
}

function updatePreviewImage() {
    const file = state.screenshots[state.previewIndex];
    document.getElementById('preview-image').src = `/api/screenshot/${state.currentProject}/${state.browseSource}/${file}`;
    document.getElementById('preview-counter').innerText = `${state.previewIndex + 1} / ${state.screenshots.length}`;
}

function prevImage() {
    if (state.previewIndex > 0) {
        state.previewIndex--;
        updatePreviewImage();
    }
}

function nextImage() {
    if (state.previewIndex < state.screenshots.length - 1) {
        state.previewIndex++;
        updatePreviewImage();
    }
}

function handleKey(e) {
    if (e.key === 'ArrowLeft') prevImage();
    if (e.key === 'ArrowRight') nextImage();
    if (e.key === 'Escape') closePreview();
}

// ==================== 通用 ====================
function showCreateProject() { document.getElementById('modal-create').classList.add('active'); }
function closeModal() { document.querySelectorAll('.modal').forEach(el => el.classList.remove('active')); }

function showToast(msg, duration=3000) {
    const toast = document.getElementById('toast');
    toast.innerText = msg;
    toast.classList.add('show');
    setTimeout(() => toast.classList.remove('show'), duration);
}

// ==================== 全局状态 ====================
const state = {
    currentView: 'dashboard',
    currentProject: null,
    screenshots: [],
    currentTab: 'download',
    previewIndex: 0,
    browseSource: 'screens' // screens | downloads
};

// ==================== 初始化 ====================
document.addEventListener('DOMContentLoaded', () => {
    loadProjects();
    checkChrome();
    
    // 如果有上次打开的项目，尝试恢复
    const lastProject = localStorage.getItem('lastProject');
    if (lastProject) {
        // openProject(lastProject); // 暂时先不自动打开，回到首页更有掌控感
    }
});

// ==================== 视图管理 ====================
function switchView(viewName) {
    document.querySelectorAll('.view').forEach(el => {
        el.classList.remove('active');
        el.style.opacity = '0';
    });
    
    const target = document.getElementById(`view-${viewName}`);
    setTimeout(() => {
        target.classList.add('active');
        target.style.opacity = '1';
    }, 200);
    
    state.currentView = viewName;
}

function goHome() {
    switchView('dashboard');
    loadProjects();
    state.currentProject = null;
    localStorage.removeItem('lastProject');
}

// ==================== Tab 切换 ====================
function switchTab(tabName) {
    // UI 更新
    document.querySelectorAll('.tab-item').forEach(el => el.classList.remove('active'));
    document.querySelector(`[data-tab="${tabName}"]`).classList.add('active');
    
    document.querySelectorAll('.tab-pane').forEach(el => el.classList.remove('active'));
    document.getElementById(`tab-${tabName}`).classList.add('active');
    
    // 逻辑处理
    state.currentTab = tabName;
    
    if (tabName === 'browse') {
        loadScreenshots();
    } else if (tabName === 'report') {
        // 自动预览报告
        generateReport(true);
    }
}

// ==================== 项目管理 ====================
function loadProjects() {
    fetch('/api/projects').then(r => r.json()).then(data => {
        const grid = document.getElementById('projects-grid');
        grid.innerHTML = data.projects.map(p => `
            <div class="project-card" onclick="openProject('${p.name}')">
                <div class="project-card-header">
                    <div class="project-icon">📱</div>
                    <button class="btn btn-ghost btn-sm" onclick="event.stopPropagation(); deleteProject('${p.name}')">×</button>
                </div>
                <div class="project-title">${p.name}</div>
                <div class="project-info">
                    <span>${p.screen_count} screens</span>
                    <span>${p.created.split(' ')[0]}</span>
                </div>
            </div>
        `).join('');
    });
}

function openProject(name) {
    state.currentProject = name;
    localStorage.setItem('lastProject', name);
    
    document.getElementById('current-project-name').innerText = name;
    switchView('workspace');
    switchTab('download'); // 默认进入采集页
    
    // 获取项目详情更新 Badge
    fetch(`/api/screenshots/${name}`).then(r => r.json()).then(data => {
        const count = data.screens.length || data.downloads.length;
        document.getElementById('current-project-count').innerText = `${count} screens`;
    });
}

function createProject() {
    const name = document.getElementById('new-project-name').value.trim();
    if (!name) return showToast('请输入项目名称');
    
    fetch('/api/projects', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({name})
    }).then(r => r.json()).then(data => {
        if (data.success) {
            closeModal();
            openProject(name);
            showToast('项目创建成功');
        } else {
            showToast(data.error);
        }
    });
}

function deleteProject(name) {
    if(!confirm(`确定删除项目 ${name}?`)) return;
    fetch(`/api/projects/${name}`, {method: 'DELETE'}).then(() => loadProjects());
}

// ==================== 采集功能 ====================
function startChrome() {
    showToast('正在启动 Chrome...', 2000);
    fetch('/api/start-chrome', {method: 'POST'}).then(() => {
        setTimeout(checkChrome, 3000);
    });
}

function checkChrome() {
    fetch('/api/check-chrome').then(r => r.json()).then(data => {
        const statusText = document.getElementById('chrome-status-text');
        if (statusText) statusText.innerText = data.available ? '已连接 (Ready)' : '未连接';
    });
}

function startDownload() {
    const url = document.getElementById('download-url').value;
    if (!url) return showToast('请输入 URL');
    
    const btn = document.getElementById('btn-download');
    const log = document.getElementById('download-progress');
    
    btn.disabled = true;
    btn.innerText = '采集进行中...';
    log.style.display = 'block';
    log.innerHTML = '<div>[INFO] 连接 Chrome...</div><div>[INFO] 开始滚动页面...</div>';
    
    fetch('/api/download', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({project_name: state.currentProject, url})
    }).then(r => r.json()).then(data => {
        btn.disabled = false;
        btn.innerText = '开始采集';
        
        if (data.success) {
            log.innerHTML += `<div>[SUCCESS] 成功采集 ${data.count} 张截图</div>`;
            showToast(`采集完成: ${data.count} 张`);
            // 自动跳转到整理 Tab
            setTimeout(() => switchTab('classify'), 1500);
        } else {
            log.innerHTML += `<div style="color:red">[ERROR] ${data.error}</div>`;
        }
    });
}

// ==================== 整理功能 ====================
function startClassify() {
    const module = document.getElementById('classify-module').value;
    
    fetch('/api/classify', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({project_name: state.currentProject, focus_module: module})
    }).then(r => r.json()).then(data => {
        if (data.success) {
            showToast(`整理完成: ${data.count} 张`);
            // 自动跳转到浏览 Tab
            setTimeout(() => switchTab('browse'), 1000);
        }
    });
}

// ==================== 浏览功能 ====================
function loadScreenshots() {
    fetch(`/api/screenshots/${state.currentProject}`).then(r => r.json()).then(data => {
        state.screenshots = state.browseSource === 'screens' ? data.screens : data.downloads;
        renderGrid();
    });
}

function switchBrowseSource(source) {
    state.browseSource = source;
    document.querySelectorAll('.toggle-btn').forEach(el => el.classList.remove('active'));
    event.target.classList.add('active');
    loadScreenshots();
}

function updateGridSize(size) {
    document.getElementById('screenshots-grid').style.gridTemplateColumns = `repeat(auto-fill, minmax(${size}px, 1fr))`;
}

function renderGrid() {
    const grid = document.getElementById('screenshots-grid');
    if (state.screenshots.length === 0) {
        grid.innerHTML = '<div class="empty-state-small">暂无截图</div>';
        return;
    }
    
    grid.innerHTML = state.screenshots.map((file, i) => `
        <div class="screenshot-card" onclick="openPreview(${i})">
            <img src="/api/screenshot/${state.currentProject}/${state.browseSource}/${file}" loading="lazy">
            <div class="screenshot-caption">${file}</div>
        </div>
    `).join('');
}

// ==================== 报告功能 ====================
function generateReport(previewOnly = false) {
    fetch('/api/generate-report', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({project_name: state.currentProject})
    }).then(r => r.json()).then(data => {
        if (data.success) {
            // 简单的 Markdown 渲染
            let html = `<h1>${state.currentProject} 分析报告</h1>`;
            html += '<table><thead><tr><th>模块</th><th>数量</th></tr></thead><tbody>';
            for(let [k,v] of Object.entries(data.categories)) {
                html += `<tr><td>${k}</td><td>${v}</td></tr>`;
            }
            html += '</tbody></table>';
            
            document.getElementById('report-preview').innerHTML = html;
            if (!previewOnly) showToast('报告已生成');
        }
    });
}

function openProjectFolder() {
    fetch('/api/open-folder', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({project_name: state.currentProject})
    });
}

// ==================== 预览弹窗 ====================
function openPreview(index) {
    state.previewIndex = index;
    updatePreviewImage();
    document.getElementById('modal-preview').classList.add('active');
    document.addEventListener('keydown', handleKey);
}

function closePreview() {
    document.getElementById('modal-preview').classList.remove('active');
    document.removeEventListener('keydown', handleKey);
}

function updatePreviewImage() {
    const file = state.screenshots[state.previewIndex];
    document.getElementById('preview-image').src = `/api/screenshot/${state.currentProject}/${state.browseSource}/${file}`;
    document.getElementById('preview-counter').innerText = `${state.previewIndex + 1} / ${state.screenshots.length}`;
}

function prevImage() {
    if (state.previewIndex > 0) {
        state.previewIndex--;
        updatePreviewImage();
    }
}

function nextImage() {
    if (state.previewIndex < state.screenshots.length - 1) {
        state.previewIndex++;
        updatePreviewImage();
    }
}

function handleKey(e) {
    if (e.key === 'ArrowLeft') prevImage();
    if (e.key === 'ArrowRight') nextImage();
    if (e.key === 'Escape') closePreview();
}

// ==================== 通用 ====================
function showCreateProject() { document.getElementById('modal-create').classList.add('active'); }
function closeModal() { document.querySelectorAll('.modal').forEach(el => el.classList.remove('active')); }

function showToast(msg, duration=3000) {
    const toast = document.getElementById('toast');
    toast.innerText = msg;
    toast.classList.add('show');
    setTimeout(() => toast.classList.remove('show'), duration);
}
