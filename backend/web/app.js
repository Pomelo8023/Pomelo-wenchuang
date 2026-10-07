
// ===== 自定义弹窗 =====
let _modalResolve = null;
function _openModal({ title, body, input = false, placeholder = '', defaultValue = '', okText = '确定', cancelText = '取消' }) {
  return new Promise((resolve) => {
    _modalResolve = resolve;
    document.getElementById('modalTitle').textContent = title;
    document.getElementById('modalBody').textContent = body || '';
    const inp = document.getElementById('modalInput');
    if (input) {
      inp.style.display = 'block';
      inp.placeholder = placeholder;
      inp.value = defaultValue;
      setTimeout(() => inp.focus(), 50);
    } else {
      inp.style.display = 'none';
    }
    document.getElementById('modalOk').textContent = okText;
    document.getElementById('modalCancel').textContent = cancelText;
    document.getElementById('modalCancel').style.display = cancelText ? 'block' : 'none';
    document.getElementById('modalOverlay').style.display = 'flex';
  });
}
function modalOk() {
  const inp = document.getElementById('modalInput');
  const val = inp.style.display === 'none' ? true : inp.value;
  document.getElementById('modalOverlay').style.display = 'none';
  if (_modalResolve) { _modalResolve(val); _modalResolve = null; }
}
function modalCancel() {
  document.getElementById('modalOverlay').style.display = 'none';
  if (_modalResolve) { _modalResolve(false); _modalResolve = null; }
}
function myAlert(msg, title = '提示') {
  return _openModal({ title, body: msg, cancelText: '' });
}
function myConfirm(msg, title = '确认') {
  return _openModal({ title, body: msg });
}
function myPrompt(msg, title = '输入', placeholder = '', defaultValue = '') {
  return _openModal({ title, body: msg, input: true, placeholder, defaultValue });
}

let currentProject = localStorage.getItem('current_project') || '';

// 简单Markdown渲染
function renderMarkdown(text) {
  if (!text) return '';
  let html = text;
  // 转义HTML
  html = html.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  // 表格 - 更健壮的处理
  const lines = html.split('\n');
  let inTable = false;
  let result = [];
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    if (/^\|.+\|$/.test(line.trim())) {
      const cells = line.trim().split('|').filter((c, idx) => idx > 0 && idx < line.trim().split('|').length - 1);
      if (!inTable) {
        result.push('<table><thead><tr>');
        result.push(cells.map(c => '<th>' + c.trim() + '</th>').join(''));
        result.push('</tr></thead><tbody>');
        inTable = true;
      } else if (line.includes('---')) {
        // 分隔线，跳过
        continue;
      } else {
        result.push('<tr>' + cells.map(c => '<td>' + c.trim() + '</td>').join('') + '</tr>');
      }
    } else {
      if (inTable) {
        result.push('</tbody></table>');
        inTable = false;
      }
      result.push(line);
    }
  }
  if (inTable) result.push('</tbody></table>');
  html = result.join('\n');
  // 代码块
  html = html.replace(/```(\w*)\n([\s\S]*?)```/g, '<pre><code>$2</code></pre>');
  // 行内代码
  html = html.replace(/`([^`]+)`/g, '<code>$1</code>');
  // 加粗
  html = html.replace(/\*\*([^*]+)\*\*/g, '<b>$1</b>');
  // 斜体
  html = html.replace(/\*([^*]+)\*/g, '<i>$1</i>');
  // 标题
  html = html.replace(/^### (.+)$/gm, '<h3>$1</h3>');
  html = html.replace(/^## (.+)$/gm, '<h2>$1</h2>');
  html = html.replace(/^# (.+)$/gm, '<h1>$1</h1>');
  // 列表
  html = html.replace(/^- (.+)$/gm, '<li>$1</li>');
  html = html.replace(/(<li>.*<\/li>)/s, '<ul>$1</ul>');
  // 引用
  html = html.replace(/^&gt; (.+)$/gm, '<blockquote>$1</blockquote>');
  // 链接
  html = html.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank">$1</a>');
  // 换行
  html = html.replace(/\n/g, '<br>');
  // 修复表格换行
  html = html.replace(/<\/tr><br>/g, '</tr>');
  html = html.replace(/<\/thead><br>/g, '</thead>');
  html = html.replace(/<\/tbody><br>/g, '</tbody>');
  return html;
}

function toast(msg, type) {
  let t = document.createElement('div');
  t.style.cssText = 'position:fixed;top:20%;left:50%;transform:translateX(-50%);background:rgba(30,42,32,0.95);color:'+(type==='err'?'#ff6b6b':'#b5d96a')+';padding:12px 24px;border-radius:12px;z-index:9999;font-size:14px;box-shadow:0 4px 20px rgba(0,0,0,0.4);border:1px solid rgba(138,174,60,0.3);max-width:80%;text-align:center;';
  t.textContent = msg;
  document.body.appendChild(t);
  setTimeout(() => { t.style.opacity = '0'; t.style.transition = 'opacity 0.3s'; }, 2000);
  setTimeout(() => t.remove(), 2400);
}

function toggleSidebar() {
  document.querySelector('.sidebar').classList.toggle('open');
  document.getElementById('overlay').classList.toggle('show');
}

function showPage(name, ev) {  document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
  document.getElementById('page-' + name).classList.add('active');
  if (name === 'overview') loadOverview();
  if (name === 'optimize') { loadFeedback(); loadChapterList(); }
  document.querySelectorAll('.nav-item, .bottom-nav-item').forEach(n => n.classList.remove('active'));
  var trigger = ev ? ev.target : null;
  if (!trigger && window.event) trigger = window.event.target;
  if (trigger) {
    var item = trigger.closest('.nav-item, .bottom-nav-item');
    if (item) item.classList.add('active');
  }
  const pageTitleEl = document.getElementById('pageTitle');
  if (pageTitleEl) {
    pageTitleEl.textContent = {
      chat: 'AI对话', projects: '项目列表', overview: '写作', console: '写作控制台', read: '书架',
      characters: '人物', foreshadows: '伏笔', settings: '我的', keys: '密钥',
      setup: '设定', optimize: '优化控制台'
    }[name] || name;
  }
  if (currentProject) {
    const bookTitle = localStorage.getItem('title_' + currentProject) || currentProject;
    const projectNameEl = document.getElementById('projectName');
    if (projectNameEl) projectNameEl.textContent = '当前项目：' + bookTitle;
    const projectNameTopEl = document.getElementById('projectNameTop');
    if (projectNameTopEl) projectNameTopEl.textContent = bookTitle;
    const projectNameSidebarEl = document.getElementById('projectNameSidebar');
    if (projectNameSidebarEl) projectNameSidebarEl.textContent = bookTitle;
  }
  // 手机端点完导航自动关抽屉
  if (window.innerWidth <= 768) {
    document.querySelector('.sidebar').classList.remove('open');
    document.getElementById('overlay').classList.remove('show');
  }
  if (name === 'overview') loadOverview();
  if (name === 'console') { loadConsole(); loadLlmStatus(); }
  if (name === 'read') loadRead();
  if (name === 'characters') loadCharacters();
  if (name === 'foreshadows') { loadForeshadows(); drawTimeline(); }
  if (name === 'home') { loadWritingCalendar(); }
  if (name === 'timeline') { drawTimeline(); }
  if (name === 'outline') { loadOutline(); }
  if (name === 'worldview') { loadWorldview(); }
  if (name === 'settings') loadSettings();
  if (name === 'keys') loadKeys();
  if (name === 'chat') loadChatHistory();
}

async function loadProjects() {
  const r = await fetch('/api/projects');
  const projects = await r.json();
  // 把书名存到localStorage
  projects.forEach(p => {
    if (p.title) localStorage.setItem('title_' + p.name, p.title);
  });
  // 更新侧边栏和顶部的当前小说名
  if (currentProject) {
    const bookTitle = localStorage.getItem('title_' + currentProject) || currentProject;
    const sidebarEl = document.getElementById('projectNameSidebar');
    if (sidebarEl) sidebarEl.textContent = bookTitle;
    const topEl = document.getElementById('projectNameTop');
    if (topEl) topEl.textContent = bookTitle;
  }
  document.getElementById('projectList').innerHTML = projects.length
    ? projects.map(p => `
      <div class="project-item" onclick="openProject('${p.name}')">
        <div>
          <div class="project-name">${p.title || p.name}</div>
          <div class="project-meta">第 ${p.current_chapter}/${p.total_chapters} 章</div>
        </div>
        <div style="display:flex;align-items:center;gap:8px">
          <span class="badge ${p.status}">${p.status === 'running' ? '生成中' : p.status === 'completed' ? '已完成' : '已停止'}</span>
          ${p.status === 'running' ? `<span onclick="event.stopPropagation();stopGen()" style="cursor:pointer;padding:4px" title="暂停">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><rect x="6" y="4" width="4" height="16"/><rect x="14" y="4" width="4" height="16"/></svg>
          </span>` : (p.status === 'stopped' || p.status === 'paused') ? `<span onclick="event.stopPropagation();startGen()" style="cursor:pointer;padding:4px" title="继续">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><polygon points="5,3 19,12 5,21"/></svg>
          </span>` : ''}
          <span onclick="event.stopPropagation();deleteProject('${p.name}')" style="color:var(--red);font-size:18px;cursor:pointer;padding:4px">×</span>
        </div>
      </div>
    `).join('')
    : '<div class="empty-state"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/></svg><div>还没有项目</div><div class="hint">在上方输入项目名，点"创建"开始</div></div>';
}

async function openProject(name) {
  // 先停止之前项目的生成
  if (currentProject && currentProject !== name) {
    try {
      await fetch('/api/generate/stop', {method:'POST'});
    } catch(e) {}
  }
  currentProject = name;
  localStorage.setItem('current_project', name);
  // 清空速度/时间相关变量
  window._chapterStart = null;
  window._lastChapter = null;
  window._chapterTimes = [];
  window._speedHistory = [];
  // 从localStorage读取书名
  const bookTitle = localStorage.getItem('title_' + name) || name;
  document.getElementById('setupTitle').textContent = '设定：' + bookTitle;
  if (document.getElementById('projectNameSidebar')) document.getElementById('projectNameSidebar').textContent = bookTitle;
  if (document.getElementById('projectNameTop')) document.getElementById('projectNameTop').textContent = bookTitle;
  showPage('setup');
  loadSettings();
  loadChatHistory();
}

function showConfirm(msg, onOk) {
  const old = document.getElementById('customModal');
  if (old) old.remove();
  const m = document.createElement('div');
  m.id = 'customModal';
  m.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,0.6);z-index:9999;display:flex;align-items:center;justify-content:center;padding:20px';
  m.innerHTML = `
    <div style="background:var(--card);border:1px solid var(--border);border-radius:16px;padding:24px;max-width:320px;width:100%;box-shadow:0 20px 60px rgba(0,0,0,0.5)">
      <div style="color:var(--text);font-size:15px;line-height:1.6;margin-bottom:20px">${msg}</div>
      <div style="display:flex;gap:10px;justify-content:flex-end">
        <button class="btn btn-ghost" onclick="this.closest('#customModal').remove()">取消</button>
        <button class="btn btn-primary" id="modalOk">确定</button>
      </div>
    </div>`;
  document.body.appendChild(m);
  m.querySelector('#modalOk').onclick = () => { m.remove(); onOk(); };
}

async function deleteProject(name) {
  showConfirm('确认删除「' + name + '」？所有内容都会删掉', async () => {
    await fetch('/api/projects/' + encodeURIComponent(name), {method: 'DELETE'});
    // 清理localStorage里的缓存
    localStorage.removeItem('title_' + name);
    localStorage.removeItem('chat_history_' + name);
    if (currentProject === name) {
      currentProject = '';
      localStorage.removeItem('current_project');
    }
    loadProjects();
    toast('已删除');
  });
}

function createProject() {
  const name = document.getElementById('newName').value.trim();
  if (!name) return toast('请输入项目名');
  currentProject = name;
  localStorage.setItem('current_project', name);
  document.getElementById('setupTitle').textContent = '设定：' + name;
  showPage('setup');
  loadProjects();
  loadChatHistory();
}

let chatHistory = [];
// 按项目加载对话历史
function loadChatHistory() {
  const key = 'chat_history_' + (currentProject || 'default');
  chatHistory = JSON.parse(localStorage.getItem(key) || '[]');
  const box = document.getElementById('chatBox');
  if (box) {
    box.innerHTML = '';
    chatHistory.forEach(h => {
      if (h.role === 'user') {
        const div = document.createElement('div');
        div.style.cssText = 'display:flex;justify-content:flex-end;margin:24px 0';
        div.innerHTML = '<div style="background:var(--accent);color:#000;padding:10px 16px;border-radius:18px 18px 6px 18px;max-width:85%;word-wrap:break-word;font-size:15px;line-height:1.6">'+h.content+'</div>';
        box.appendChild(div);
      } else {
        const div = document.createElement('div');
        div.style.cssText = 'margin:24px 0;color:var(--text);font-size:15px;line-height:1.7;word-wrap:break-word';
        div.className = 'markdown-body';
        
        // 检测有没有修改章节的标记
        const modifyMatch = h.content.match(/<<<MODIFY_CHAPTER:(\d+)>>>/);
        if (modifyMatch) {
          const chNum = parseInt(modifyMatch[1]);
          const cleanReply = h.content.replace(/<<<MODIFY_CHAPTER:\d+>>>/, '');
          const typingId = 'chatTyping_' + Date.now() + '_' + Math.random();
          div.innerHTML = renderMarkdown(cleanReply);
          // 加上修改卡片
          const cardDiv = document.createElement('div');
          cardDiv.style.cssText = 'background:var(--bg-card);border:1px solid var(--border);border-radius:12px;padding:16px;margin-top:12px';
          cardDiv.innerHTML = `
            <div style="font-size:14px;color:var(--accent);font-weight:bold;margin-bottom:8px">确认修改第${chNum}章</div>
            <textarea id="modifyInput_${typingId}" style="width:100%;min-height:100px;background:var(--bg);border:1px solid var(--border);border-radius:8px;padding:8px;color:var(--text);font-size:13px;line-height:1.5;resize:vertical">${cleanReply.replace(/</g, '&lt;')}</textarea>
            <div style="display:flex;gap:8px;margin-top:8px">
              <button onclick="modifyChapterWithInput(${chNum}, '${typingId}')" style="background:var(--accent);color:#000;border:none;border-radius:8px;padding:6px 12px;cursor:pointer;font-size:12px;flex:1">确认修改</button>
              <button onclick="showPage('optimize')" style="background:none;border:1px solid var(--border);color:var(--text-dim);border-radius:8px;padding:6px 12px;cursor:pointer;font-size:12px">去优化控制台</button>
            </div>
          `;
          div.appendChild(cardDiv);
        } else {
          div.innerHTML = renderMarkdown(h.content);
        }
        
        box.appendChild(div);
      }
    });
    box.scrollTop = box.scrollHeight;
  }
}
async function sendChat() {
  const inp = document.getElementById('chatInput');
  const msg = inp.value.trim();
  if (!msg) return;
  inp.value = '';
  const box = document.getElementById('chatBox');
  const typingId = 'chatTyping_' + Date.now();
  
  // 添加用户消息气泡
  const userMsgDiv = document.createElement('div');
  userMsgDiv.style.cssText = 'display:flex;justify-content:flex-end;margin:24px 0';
  userMsgDiv.innerHTML = '<div style="background:var(--accent);color:#000;padding:10px 16px;border-radius:18px 18px 6px 18px;max-width:85%;word-wrap:break-word;font-size:15px;line-height:1.6">'+msg+'</div>';
  box.appendChild(userMsgDiv);
  
  // 根据消息内容显示不同状态
  let initStatus = '正在思考中';
  if (/修改|重写|润色|改/.test(msg)) initStatus = '正在修改中';
  else if (/分析|评价|诊断|挑毛病/.test(msg)) initStatus = '正在分析中';
  else if (/生成大纲|写设定|生成设定/.test(msg)) initStatus = '正在生成大纲';
  else if (/第\d+章|第[一二三四五六七八九十]+章/.test(msg)) initStatus = '正在读取章节';
  else if (/看看|读|检查/.test(msg)) initStatus = '正在查看文章';
  
  // 添加正在输入状态
  const typingDiv = document.createElement('div');
  typingDiv.id = typingId;
  typingDiv.style.cssText = 'margin:24px 0';
  typingDiv.innerHTML = '<div style="color:var(--text-dim);font-size:14px;display:flex;align-items:center;gap:8px"><span class="chatStatusText">'+initStatus+'</span><span class="thinking-dot"></span><span class="thinking-dot"></span><span class="thinking-dot"></span></div>';
  box.appendChild(typingDiv);
  
  box.scrollTop = box.scrollHeight;
  // 状态切换：查看文章后→思考；修改状态保持不变
  if (!/修改|重写|润色|改/.test(msg)) {
    setTimeout(() => {
      const st = document.querySelector('#'+typingId+' .chatStatusText');
      if (st) st.textContent = '正在思考中';
    }, 1000);
  }
  // 先把历史对话传给后端（不包含刚发的这条，后端会自己加）
  const historyToSend = [...chatHistory];
  chatHistory.push({role: "user", content: msg});
  localStorage.setItem('chat_history_' + (currentProject || 'default'), JSON.stringify(chatHistory.slice(-30)));
  try {
    const r = await (await fetch('/api/chat', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message:msg, project:currentProject, history:historyToSend})})).json();
    let reply = r.reply || r.error;
    const originalReply = reply;  // 保存原始回复（带标记），方便后面存到chatHistory里
    // 检测是否是章节内容
    const chMatch = reply.match(/^第(\d+)章\s+(.+)/);
    let saveBtnHtml = '';
    if (chMatch) {
      const chNum = chMatch[1];
      const chTitle = chMatch[2].split('\n')[0];
      saveBtnHtml = `<button onclick="saveChapter(${chNum}, '${chTitle.replace(/'/g, "\\'")}', '${typingId}')" style="background:var(--accent);color:#000;border:none;border-radius:8px;padding:6px 12px;cursor:pointer;font-size:12px;margin-left:8px">保存到第${chNum}章</button>`;
    }
    
    // 检测AI回复里有没有修改章节的标记：<<<MODIFY_CHAPTER:章节号>>>
    const modifyMatch = reply.match(/<<<MODIFY_CHAPTER:(\d+)>>>/);
    let modifyCardHtml = '';
    if (modifyMatch) {
      const chNum = parseInt(modifyMatch[1]);
      // 从回复里去掉这个标记，只显示给用户看的内容
      const cleanReply = reply.replace(/<<<MODIFY_CHAPTER:\d+>>>/, '');
      // 渲染修改卡片：里面有AI给出的修改建议，用户可以编辑
      modifyCardHtml = `<div style="background:var(--bg-card);border:1px solid var(--border);border-radius:12px;padding:16px;margin-top:12px">
        <div style="font-size:14px;color:var(--accent);font-weight:bold;margin-bottom:8px">确认修改第${chNum}章</div>
        <textarea id="modifyInput_${typingId}" style="width:100%;min-height:100px;background:var(--bg);border:1px solid var(--border);border-radius:8px;padding:8px;color:var(--text);font-size:13px;line-height:1.5;resize:vertical">${cleanReply.replace(/</g, '&lt;')}</textarea>
        <div style="display:flex;gap:8px;margin-top:8px">
          <button onclick="modifyChapterWithInput(${chNum}, '${typingId}')" style="background:var(--accent);color:#000;border:none;border-radius:8px;padding:6px 12px;cursor:pointer;font-size:12px;flex:1">确认修改</button>
          <button onclick="showPage('optimize')" style="background:none;border:1px solid var(--border);color:var(--text-dim);border-radius:8px;padding:6px 12px;cursor:pointer;font-size:12px">去优化控制台</button>
        </div>
      </div>`;
      // 更新回复内容（去掉标记）
      reply = cleanReply;
    }
    
    document.getElementById(typingId).innerHTML = '<div style="color:var(--text);font-size:15px;line-height:1.7;word-wrap:break-word;animation:fadeInUp 0.25s ease" class="markdown-body">'+renderMarkdown(reply)+'</div>'+(modifyCardHtml||'')+(saveBtnHtml?'<div style="display:flex;gap:8px;margin-top:8px;align-items:center;flex-wrap:wrap">'+saveBtnHtml+'</div>':'');
    // 保存回复内容到data属性，方便复制
    document.getElementById(typingId).dataset.reply = reply;
    // 保存原始回复（带标记）到chatHistory里，这样刷新后还能渲染修改卡片
    chatHistory.push({role: "assistant", content: originalReply});
    localStorage.setItem('chat_history_' + (currentProject || 'default'), JSON.stringify(chatHistory.slice(-30)));
  } catch(e) {
    console.error('Chat error:', e);
    document.getElementById(typingId).innerHTML = '<span style="color:var(--red)">网络错误：' + e.message + '</span>';
  }
  box.scrollTop = box.scrollHeight;
}

async function saveChapter(chNum, chTitle, typingId) {
  const reply = document.getElementById(typingId).dataset.reply;
  try {
    const r = await (await fetch('/api/save_chapter', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({project:currentProject, chapter_num:chNum, title:chTitle, content:reply})})).json();
    if (r.ok) toast('已保存到第'+chNum+'章');
    else toast('保存失败', 'err');
  } catch(e) {
    toast('保存失败', 'err');
  }
}

async function modifyChapter(chNum, modifyRequest, typingId) {
  // 获取AI之前给出的修改建议（最近一条AI回复）
  const aiSuggestion = document.getElementById(typingId).dataset.reply || '';
  try {
    const r = await (await fetch('/api/modify_chapter', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({project:currentProject, chapter_num:chNum, modify_request:modifyRequest, modify_suggestion:aiSuggestion})})).json();
    if (r.ok) toast('已修改第'+chNum+'章');
    else toast('修改失败：' + (r.error || ''), 'err');
  } catch(e) {
    toast('修改失败', 'err');
  }
}

async function modifyChapterWithInput(chNum, typingId) {
  // 从textarea里读取用户编辑后的修改建议
  const modifyInput = document.getElementById('modifyInput_' + typingId);
  const userEdit = modifyInput ? modifyInput.value : '';
  try {
    // 把修改建议加到"待处理修改建议"池子里！不直接修改章节！
    const r = await (await fetch('/api/add_feedback', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({project: currentProject, chapter_num: chNum, feedback: userEdit})
    })).json();
    if (r.ok) {
      toast('已加到待处理修改建议！请去优化控制台处理！');
      // 跳转到优化控制台
      showPage('optimize');
    } else {
      toast('添加失败：' + (r.error || ''), 'err');
    }
  } catch(e) {
    toast('添加失败', 'err');
  }
}

async function loadOverview() {
  if (!currentProject) return;
  const p = await (await fetch('/api/projects/' + encodeURIComponent(currentProject) + '/progress')).json();
  document.getElementById('ovCur').textContent = p.current_chapter || 0;
  document.getElementById('ovTotal').textContent = p.total_chapters || 0;
  document.getElementById('ovStatus').textContent = p.status === 'running' ? '生成中' : p.status === 'completed' ? '已完成' : '已停止';
  const pct = p.total_chapters ? Math.round(p.current_chapter / p.total_chapters * 100) : 0;
  document.getElementById('ovBar').style.width = pct + '%';
  document.getElementById('ovPct').textContent = pct + '%';
  const fs = await (await fetch('/api/projects/' + encodeURIComponent(currentProject) + '/foreshadows')).json();
  document.getElementById('ovFs').textContent = fs.filter(f => f.status === 'active').length;
  // 加载角色和hooks
  try {
    const s = await (await fetch(`/api/projects/${encodeURIComponent(currentProject)}/characters`)).json();
    const ch = document.getElementById('ovChars');
    if (ch) {
      ch.innerHTML = s.length ? s.map(c => `
        <div style="padding:10px;background:var(--bg);border-radius:6px;margin-bottom:8px;border-left:3px solid var(--accent)">
          <div style="font-weight:600;color:var(--accent-light)">${c.name||c}</div>
          ${c.description ? `<div style="margin-top:4px;font-size:12px;color:var(--text-dim)">${c.description.substring(0, 50)}...</div>` : ''}
        </div>
      `).join('') : '暂无';
    }
  } catch(e) {}
  drawEmotionChart();
  drawWordChart();
  loadRecent();
}

async function exportTxt() {
  window.open('/api/projects/' + encodeURIComponent(currentProject) + '/export', '_blank');
}

async function loadRecent() {
  if (!currentProject) return;
  const data = await (await fetch('/api/projects/' + encodeURIComponent(currentProject) + '/chapters')).json();
  const chs = data.chapters || data;
  const recent = chs.slice(-5).reverse();
  document.getElementById('recentChapters').innerHTML = recent.length
    ? recent.map(c => `<div style="padding:8px 0;border-bottom:1px solid var(--border);cursor:pointer" onclick="showPage('read');loadChapter(${c.num || c.chapter})">
        <span style="color:var(--accent-light)">第${c.num || c.chapter}章</span> ${c.title || ''}
        <span style="float:right;color:var(--text-dim);font-size:12px">${c.word_count || 0}字</span>
      </div>`).join('')
    : '<p style="color:var(--text-dim)">还没有章节</p>';
}

document.addEventListener('keydown', e => {
  if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;
  if (e.key === 'ArrowLeft' && document.getElementById('page-read').style.display !== 'none') prevChapter();
  if (e.key === 'ArrowRight' && document.getElementById('page-read').style.display !== 'none') nextChapter();
});

async function startGen() {
  // 优先从后端读真实 total_chapters，输入框只是 fallback
  let total = 100;
  try {
    const pr = await (await fetch('/api/projects/' + encodeURIComponent(currentProject) + '/progress')).json();
    if (pr.total_chapters) total = pr.total_chapters;
  } catch(e) {}
  const wordsMin = parseInt(document.getElementById('sWordsMin')?.value) || 1900;
  const wordsMax = parseInt(document.getElementById('sWordsMax')?.value) || 2100;
  // 自动读取当前进度，从下一章开始
  let startCh = 1;
  try {
    const p = await (await fetch('/api/projects/' + encodeURIComponent(currentProject) + '/progress')).json();
    startCh = (p.current_chapter || 0) + 1;
    toast('从第' + startCh + '章继续，目标' + total + '章');
  } catch(e) {}
  fetch('/api/generate/start', {
    method: 'POST', headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({project_name: currentProject, total_chapters: total, words_per: (wordsMin+wordsMax)/2, start_chapter: startCh})
  });
  showPage('console');
}

function stopGen() {
  fetch('/api/generate/stop', {
    method: 'POST', headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({project_name: currentProject})
  });
  toast('已暂停');
  setTimeout(loadProjects, 1000);
}

function viewCurrent() {
  showPage('read');
  if (typeof loadChapters === 'function') loadChapters();
}

async function rewriteByChapter() {
  const ch = await myPrompt('请输入要重写哪一章（输入章节号，比如第50章就输入50）：', '重写章节', '章节号');
  if (!ch) return;
  const chNum = parseInt(ch);
  if (isNaN(chNum) || chNum < 1) {
    await myAlert('请输入正确的章节号！', '输入错误');
    return;
  }
  // 从后端读真实 total_chapters
  let total = 100;
  try {
    const pr = await (await fetch('/api/projects/' + encodeURIComponent(currentProject) + '/progress')).json();
    if (pr.total_chapters) total = pr.total_chapters;
  } catch(e) {}
  const wordsMin = parseInt(document.getElementById('sWordsMin')?.value) || 1900;
  const wordsMax = parseInt(document.getElementById('sWordsMax')?.value) || 2100;
  fetch('/api/generate/stop', {
    method: 'POST', headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({project_name: currentProject})
  }).then(() => {
    setTimeout(() => {
      fetch('/api/generate/start', {
        method: 'POST', headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({project_name: currentProject, total_chapters: total, words_per: (wordsMin+wordsMax)/2, start_chapter: chNum})
      });
      toast('已重新生成第' + chNum + '章');
    }, 1000);
  });
}

async function drawEmotionChart() {
  const canvas = document.getElementById('emotionChart');
  const ctx = canvas.getContext('2d');
  const W = canvas.width, H = canvas.height;
  ctx.clearRect(0, 0, W, H);
  // 网格
  ctx.strokeStyle = '#2a2a4a'; ctx.lineWidth = 1;
  for (let i = 0; i <= 5; i++) {
    const y = 20 + i * (H - 40) / 5;
    ctx.beginPath(); ctx.moveTo(40, y); ctx.lineTo(W - 10, y); ctx.stroke();
  }
  const r = await fetch('/api/projects/' + encodeURIComponent(currentProject) + '/emotion-arc');
  const data = await r.json();
  const arc = data.arc || [];
  if (arc.length < 2) {
    ctx.fillStyle = '#888'; ctx.font = '14px sans-serif';
    ctx.fillText('写完第2章后这里会出现情绪曲线', 200, H / 2);
    return;
  }
  const chs = arc.map(a => a.chapter);
  const intens = arc.map(a => a.intensity || 5);
  const minCh = Math.min(...chs), maxCh = Math.max(...chs);
  const xScale = (ch) => 50 + (ch - minCh) / Math.max(1, maxCh - minCh) * (W - 70);
  const yScale = (v) => H - 30 - (v - 1) / 9 * (H - 60);
  // 折线
  ctx.strokeStyle = '#8aae3c'; ctx.lineWidth = 2;
  ctx.beginPath();
  arc.forEach((a, i) => {
    const x = xScale(a.chapter), y = yScale(a.intensity || 5);
    i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
  });
  ctx.stroke();
  // 数据点 + 高潮标记
  arc.forEach(a => {
    const x = xScale(a.chapter), y = yScale(a.intensity || 5);
    ctx.fillStyle = a.climax ? '#ff6b6b' : '#b5d96a';
    ctx.beginPath();
    ctx.arc(x, y, a.climax ? 5 : 3, 0, Math.PI * 2);
    ctx.fill();
  });
}

async function drawWordChart() {
  const canvas = document.getElementById('wordChart');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  const W = canvas.width, H = canvas.height;
  ctx.clearRect(0, 0, W, H);
  const chs = (await (await fetch('/api/projects/' + encodeURIComponent(currentProject) + '/chapters')).json()).chapters || [];
  if (!chs.length) return;
  const maxW = Math.max(...chs.map(c => c.word_count || 0), 1);
  const barW = (W - 60) / chs.length;
  chs.forEach((c, i) => {
    const h = (c.word_count || 0) / maxW * (H - 40);
    ctx.fillStyle = c.word_count > 2800 ? '#6abf69' : c.word_count < 1500 ? '#ff6b6b' : '#8aae3c';
    ctx.fillRect(40 + i * barW + 2, H - 20 - h, barW - 4, h);
  });
}

async function loadFeedback() {
  if (!currentProject) return;
  const r = await (await fetch('/api/get_feedback/' + encodeURIComponent(currentProject))).json();
  const box = document.getElementById('feedbackBox');
  if (!box) return;
  // 把feedback存到全局变量里，方便按钮调用
  window._feedbackList = r.feedback || [];
  if (window._feedbackList.length === 0) {
    box.innerHTML = '<div style="text-align:center;padding:20px;color:var(--text-dim);font-size:12px">暂无修改建议<br><span style="font-size:11px">在AI对话里讨论修改建议，会自动同步到这里</span></div>';
    return;
  }
  box.innerHTML = `<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">
    <span style="font-size:12px;color:var(--text-dim)">共 ${window._feedbackList.length} 条建议</span>
    <button onclick="clearFeedback()" style="background:none;border:1px solid var(--border);border-radius:6px;padding:2px 8px;cursor:pointer;font-size:11px;color:var(--text-dim)">清空</button>
  </div>` + window._feedbackList.map((f, i) => `
    <div style="background:linear-gradient(135deg, rgba(138,174,60,0.1) 0%, rgba(138,174,60,0.05) 100%);border:1px solid rgba(138,174,60,0.3);border-radius:12px;padding:14px;margin-bottom:10px;box-shadow:0 2px 8px rgba(0,0,0,0.1)">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">
        <span style="font-size:14px;color:var(--accent);font-weight:bold;display:flex;align-items:center;gap:4px">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
            <path d="M18 2H6c-1.1 0-2 .9-2 2v16c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zM6 4h5v8l-2.5-1.5L6 12V4z" fill="var(--accent)"/>
          </svg>
          第${f.chapter_num}章
        </span>
        <span style="font-size:11px;color:var(--text-dim)">${f.time ? f.time.substring(11, 16) : ''}</span>
      </div>
      <div style="font-size:13px;color:var(--text);margin-bottom:12px;line-height:1.5">
        <textarea id="feedback_${i}" style="width:100%;min-height:60px;background:var(--bg);border:1px solid var(--border);border-radius:6px;padding:6px;color:var(--text);font-size:13px;line-height:1.5;resize:vertical">${f.feedback}</textarea>
      </div>
      <div style="display:flex;gap:8px">
        <button onclick="quickModifyByIndex(${i})" style="flex:1;background:var(--accent);color:#000;border:none;border-radius:8px;padding:8px 16px;cursor:pointer;font-size:13px;font-weight:bold;display:flex;align-items:center;justify-content:center;gap:4px">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none">
            <path d="M13 2L3 14h7l-1 8 10-12h-7l1-8z" fill="#000"/>
          </svg>
          立马优化
        </button>
        <button onclick="deleteFeedback(${i})" style="background:none;border:1px solid var(--border);border-radius:8px;padding:8px 12px;cursor:pointer;font-size:13px;color:var(--text-dim);display:flex;align-items:center;justify-content:center">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none">
            <path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12 19 6.41z" fill="currentColor"/>
          </svg>
        </button>
      </div>
    </div>
  `).join('');
  // 同时加载修改日志
  loadModifyLog();
}

async function loadModifyLog() {
  if (!currentProject) return;
  const r = await (await fetch('/api/get_modify_log/' + encodeURIComponent(currentProject))).json();
  const box = document.getElementById('optimizeLogBox');
  if (!box) return;
  const log = r.log || [];
  if (log.length === 0) {
    box.innerHTML = '暂无修改记录';
    return;
  }
  box.innerHTML = log.map(l => {
    let color = 'var(--text-dim)';
    const msg = l.message || '';
    // 根据消息内容判断颜色！
    if (l.status === 'error' || msg.includes('失败') || msg.includes('错误')) {
      color = '#f87171';  // 红色
    } else if (msg.includes('完成') || msg.includes('成功') || msg.includes('已读取')) {
      color = '#4ade80';  // 绿色
    } else if (msg.includes('正在') || msg.includes('处理中')) {
      color = '#fbbf24';  // 黄色
    } else {
      color = 'var(--text-dim)';  // 灰色
    }
    return `<div style="color:${color}">[${l.time ? l.time.substring(11, 19) : ''}] ${msg}</div>`;
  }).join('');
  box.scrollTop = box.scrollHeight;
}

async function quickModifyByIndex(index) {
  if (!window._feedbackList || !window._feedbackList[index]) {
    toast('错误：修改建议不存在', 'err');
    return;
  }
  const f = window._feedbackList[index];
  // 从textarea里读取用户编辑后的内容
  const feedbackInput = document.getElementById('feedback_' + index);
  const userEdit = feedbackInput ? feedbackInput.value : f.feedback;
  toast('正在优化第'+f.chapter_num+'章...');
  try {
    const r = await (await fetch('/api/modify_chapter', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({
        project: currentProject,
        chapter_num: f.chapter_num,
        modify_request: userEdit,
        modify_suggestion: userEdit,
        save: false  // 不直接保存！先显示在"修改后"框里！
      })
    })).json();
    if (r.ok && r.new_content) {
      // 自动选择对应的章节
      document.getElementById('editChapterSelect').value = f.chapter_num;
      // 自动加载章节内容
      await loadChapterForEdit();
      // 把AI优化的结果显示在"修改后"框里
      document.getElementById('modifiedChapterText').value = r.new_content;
      toast('AI优化完成，请检查后点击保存章节');
      // 滚动到章节修改区域
      document.getElementById('editChapterSelect').scrollIntoView({behavior: 'smooth'});
    } else {
      toast('优化失败：' + (r.error || ''), 'err');
    }
  } catch(e) {
    toast('优化失败', 'err');
  }
  // 立即刷新修改日志
  loadModifyLog();
}

async function clearFeedback() {
  if (!currentProject) return;
  if (!await myConfirm('确定清空所有修改建议吗？', '清空确认')) return;
  await fetch('/api/clear_feedback/' + encodeURIComponent(currentProject), {method:'DELETE'});
  loadFeedback();
  toast('已清空');
}

async function deleteFeedback(index) {
  // 删除某一条建议（简单实现：先获取全部，然后删除对应索引，再保存）
  const r = await (await fetch('/api/get_feedback/' + encodeURIComponent(currentProject))).json();
  if (r.feedback) {
    r.feedback.splice(index, 1);
    // 保存回去（简单实现：用add_feedback逐个添加，或者加一个新API）
    // 这里先用clear_feedback + 重新添加
    await fetch('/api/clear_feedback/' + encodeURIComponent(currentProject), {method:'DELETE'});
    for (const f of r.feedback) {
      await fetch('/api/add_feedback', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({project:currentProject, chapter_num:f.chapter_num, feedback:f.feedback})});
    }
    loadFeedback();
    toast('已删除');
  }
}

async function quickModify(chNum, feedback) {
  try {
    const r = await (await fetch('/api/modify_chapter', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({project:currentProject, chapter_num:chNum, modify_request:feedback, modify_suggestion:feedback})})).json();
    if (r.ok) toast('已优化第'+chNum+'章');
    else toast('优化失败：' + (r.error || ''), 'err');
  } catch(e) {
    toast('优化失败', 'err');
  }
}

async function loadLlmStatus() {
  const s = await (await fetch('/api/llm/status')).json();
  let html = `模型: ${s.model} | 间隔: ${s.min_interval}s<br>`;
  html += `Keys: ${s.total_keys}个，可用: ${s.keys.filter(k=>k.active).length}个，熔断: ${s.disabled_count}个<br>`;
  html += s.keys.map(k => `<span style="display:inline-block;padding:2px 8px;border-radius:4px;margin:2px;background:${k.active?'rgba(0,217,163,0.2)':'rgba(255,107,107,0.2)'};color:${k.active?'var(--green)':'var(--red)'}">#${k.idx+1} ${k.active?'在用':'熔断'}</span>`).join('');
  document.getElementById('llmStatus').innerHTML = html;
}

function loadConsole() {
  if (!currentProject) return;
  loadFeedback();
  if (window._feedbackInterval) clearInterval(window._feedbackInterval);
  window._feedbackInterval = setInterval(loadFeedback, 5000);
  const logBox = document.getElementById('logBox');
  logBox.innerHTML = '加载中...';
  // 先读最近章节记录显示出来
  fetch('/api/projects/' + encodeURIComponent(currentProject) + '/chapters')
    .then(r => r.json())
    .then(data => {
      const chapters = data.chapters || data || [];
      if (chapters.length) {
        let html = '<div style="color:var(--text-dim);font-size:12px;margin-bottom:8px">—— 最近 ' + Math.min(chapters.length, 10) + ' 章 ——</div>';
        chapters.slice(-10).reverse().forEach(ch => {
          html += `<div class="log-line log-step">[第${ch.num}章] ${ch.title || ''}</div>`;
        });
        logBox.innerHTML = html;
      } else {
        logBox.innerHTML = '<p style="color:var(--text-dim);font-size:13px">暂无日志</p>';
      }
    })
    .catch(() => { logBox.innerHTML = '连接中...'; });
  // 关闭旧的EventSource
  if (window._es) { window._es.close(); window._es = null; }
  const es = new EventSource('/api/projects/' + encodeURIComponent(currentProject) + '/stream');
  window._es = es;
  es.onerror = function() {
    logBox.innerHTML = '<p style="color:var(--orange);font-size:13px">连接断开，自动重连中...</p>';
  };
  es.onopen = function() {
    logBox.innerHTML = '';
  };
  es.onmessage = function(e) {
    const data = JSON.parse(e.data);
    if (data.done) { es.close(); return; }
    // 状态图标
    const icons = {
      writing: '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#8aae3c" stroke-width="2"><path d="M12 20h9M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"/></svg> 正在写入',
      step: '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#8aae3c" stroke-width="2"><circle cx="12" cy="12" r="3"/><path d="M12 1v6m0 10v6m11-11h-6m-10 0H1"/></svg> 处理中',
      warning: '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#e4883f" stroke-width="2"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/></svg> 警告',
      error: '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#e74c3c" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg> 错误',
      completed: '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#8aae3c" stroke-width="2"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg> 完成',
    };
    const icon = icons[data.type] || icons.step;
    document.getElementById('statusIcon').innerHTML = icon;
    // 进度条
    if (data.chapter) {
      // 从后端拿最新total_chapters
      fetch(`/api/projects/${currentProject}/progress`).then(r=>r.json()).then(pr=>{
        const total = pr.total_chapters || 100;
        const pct = Math.round(data.chapter / total * 100);
        document.getElementById('progressBar').style.width = pct + '%';
        document.getElementById('progressText').textContent = `第 ${data.chapter} 章 / 共 ${total} 章`;
        // 计算预计剩余时间（用已完成章节的平均时间）
        if (window._chapterTimes && window._chapterTimes.length >= 2) {
          const avgTime = window._chapterTimes.reduce((a,b)=>a+b, 0) / window._chapterTimes.length;
          const remaining = total - data.chapter;
          if (remaining > 0 && avgTime > 0) {
            const eta = remaining * avgTime;
            let etaText;
            if (eta < 60) etaText = `${Math.round(eta)} 分钟`;
            else if (eta < 1440) etaText = `${(eta/60).toFixed(1)} 小时`;
            else etaText = `${(eta/1440).toFixed(1)} 天`;
            document.getElementById('etaInfo').textContent = `预计剩余：${remaining} 章 ≈ ${etaText}`;
          }
        }
      });
    }
    if (data.type === 'writing') {
      document.getElementById('wordCount').textContent = `本章已写 ${data.chars} 字`;
      // 记录章节开始时间
      if (!window._chapterStart || window._lastChapter != data.chapter) {
        window._chapterStart = Date.now();
        window._lastChapter = data.chapter;
      }
      // 计算实时速度（最近30秒的平均速度）
      const now = Date.now();
      if (!window._speedHistory) window._speedHistory = [];
      window._speedHistory.push({time: now, chars: data.chars});
      // 只保留最近30秒的数据
      window._speedHistory = window._speedHistory.filter(p => now - p.time < 30000);
      if (window._speedHistory.length >= 2) {
        const first = window._speedHistory[0];
        const lastPoint = window._speedHistory[window._speedHistory.length - 1];
        const dt = (lastPoint.time - first.time) / 1000 / 60; // 分钟
        const dc = lastPoint.chars - first.chars;
        if (dt > 0.1 && dc > 0) {
          const speed = Math.round(dc / dt);
          document.getElementById('speedInfo').textContent = `速度：${speed} 字/分钟`;
        }
      }
      const lastLog = logBox.lastChild;
      if (lastLog && lastLog.dataset.ch === String(data.chapter)) {
        lastLog.textContent = `[${data.ts||''}] 第${data.chapter}章 已写 ${data.chars} 字`;
        return;
      }
    }
    // 章节完成时，记录章节用时
    if (data.type === 'done' && window._chapterStart) {
      const elapsed = (Date.now() - window._chapterStart) / 1000 / 60; // 分钟
      if (elapsed > 0.1) {
        if (!window._chapterTimes) window._chapterTimes = [];
        window._chapterTimes.push(elapsed);
        // 只保留最近10章的数据
        if (window._chapterTimes.length > 10) window._chapterTimes.shift();
      }
      // 清空速度显示
      document.getElementById('speedInfo').textContent = '';
      window._speedHistory = [];
    }
    const div = document.createElement('div');
    div.className = 'log-line log-' + (data.type || 'step');
    if (data.chapter) div.dataset.ch = data.chapter;
    div.textContent = (data.ts ? '[' + data.ts + '] ' : '') + (data.msg || data.error || '');
    if (data.type === 'writing') div.textContent = `[${data.ts||''}] 第${data.chapter}章 已写 ${data.chars} 字`;
    logBox.appendChild(div);
    logBox.scrollTop = logBox.scrollHeight;
  };
}

async function loadRead() {
  // 先显示所有项目（书名）
  const projects = await (await fetch('/api/projects')).json();
  const list = document.getElementById('readList');
  list.innerHTML = projects.length
    ? projects.map(p => `
      <div onclick="selectBook('${p.name}')" style="padding:14px 12px;border-radius:10px;cursor:pointer;margin-bottom:8px;background:rgba(138,174,60,0.08)">
        <div style="font-size:14px;font-weight:700">${p.title || p.name}</div>
        <div style="font-size:11px;color:var(--text-dim);margin-top:4px">${p.current_chapter || 0}章 · ${p.status === 'running' ? '生成中' : '已停止'}</div>
      </div>
    `).join('')
    : '<p style="color:var(--text-dim)">还没有书</p>';
  document.getElementById('chapterCard').style.display = 'none';
}

async function selectBook(name) {
  currentProject = name;
  localStorage.setItem('current_project', name);
  loadChatHistory();
  const data = await (await fetch('/api/projects/' + encodeURIComponent(name) + '/chapters')).json();
  const chs = data.chapters || [];
  document.getElementById('readList').innerHTML = chs.length
    ? chs.map(c => `
      <div class="read-item" id="readItem${c.num}" onclick="loadChapter(${c.num})" style="padding:10px 12px;border-radius:8px;cursor:pointer;margin-bottom:4px">
        <div style="font-size:13px;font-weight:600">第${c.num}章</div>
        <div style="font-size:11px;color:var(--text-dim);margin-top:2px">${c.title || ''}</div>
      </div>
    `).join('')
    : '<p style="color:var(--text-dim)">还没有章节</p>';
}

let currentChapter = 0;

async function loadChapter(ch) {
  currentChapter = ch;
  const c = await (await fetch('/api/projects/' + encodeURIComponent(currentProject) + '/chapters/' + ch)).json();
  document.getElementById('chapterCard').style.display = 'block';
  document.getElementById('readEmpty').style.display = 'none';
  document.getElementById('chTitle').textContent = c.title || '第' + ch + '章';
  document.getElementById('chContent').textContent = c.content || '（空）';
  document.getElementById('chEditArea').value = c.content || '';
  document.getElementById('chContent').style.display = 'block';
  document.getElementById('chEditArea').style.display = 'none';
  document.getElementById('editActions').style.display = 'none';
  document.getElementById('editBtn').textContent = '编辑';
  // 上下章按钮
  document.getElementById('prevCh').style.visibility = ch > 1 ? 'visible' : 'hidden';
  document.getElementById('nextCh').style.visibility = c.content ? 'visible' : 'hidden';
  // 滚动到顶
  document.getElementById('chapterCard').scrollTop = 0;
  // 更新目录高亮
  document.querySelectorAll('.read-item').forEach(el => el.style.background = '');
  const item = document.getElementById('readItem' + ch);
  if (item) item.style.background = 'rgba(138,174,60,0.15)';
}

function clearChat() {
  document.getElementById('chatBox').innerHTML = '<div style="color:var(--text-dim);font-size:12px;text-align:center">对话已清空</div>';
}

async function runChatEdit() {
  const input = document.getElementById('chatInput');
  const btn = document.getElementById('chatSendBtn');
  const inst = input.value.trim();
  if (!inst) return;
  input.value = '';
  btn.disabled = true; btn.style.opacity = '0.5';
  const box = document.getElementById('chatBox');
  if (box.children.length === 1) box.innerHTML = '';
  box.innerHTML += `<div class="chat-msg chat-user">${inst}</div>`;
  box.scrollTop = box.scrollHeight;
  // AI 流式气泡
  const aiMsg = document.createElement('div');
  aiMsg.className = 'chat-msg chat-ai';
  aiMsg.textContent = '';
  box.appendChild(aiMsg);
  box.scrollTop = box.scrollHeight;

  try {
    const resp = await fetch('/api/chat-edit', {
      method: 'POST', headers: {'Content-Type': 'application/json', 'X-Token': TOKEN},
      body: JSON.stringify({project: currentProject, chapter: currentChapter, instruction: inst})
    });
    const reader = resp.body.getReader();
    const decoder = new TextDecoder();
    let full = '';
    while (true) {
      const {done, value} = await reader.read();
      if (done) break;
      const text = decoder.decode(value);
      const lines = text.split('\n\n');
      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const chunk = line.slice(6);
          if (chunk === '[DONE]') continue;
          full += chunk;
          aiMsg.textContent = full;
          document.getElementById('chContent').textContent = full;
          box.scrollTop = box.scrollHeight;
        }
      }
    }
    aiMsg.textContent = `<svg style="width:14px;height:14px;vertical-align:middle" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"/></svg> 已修改并保存（${full.length}字）`;
  } catch (e) {
    aiMsg.textContent = `<svg style="width:14px;height:14px;vertical-align:middle" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg> 错误: ${e.message}`;
    aiMsg.style.borderColor = 'var(--red)';
  }
  btn.disabled = false; btn.style.opacity = '1';
  box.scrollTop = box.scrollHeight;
}

function prevChapter() { if (currentChapter > 1) loadChapter(currentChapter - 1); }
function nextChapter() { loadChapter(currentChapter + 1); }

function exportAll() {
  window.location.href = '/api/projects/' + encodeURIComponent(currentProject) + '/export';
}

function exportCurrentChapter() {
  const ch = currentChapter;
  if (!ch) return;
  window.location.href = '/api/projects/' + encodeURIComponent(currentProject) + '/export/' + ch;
}

function toggleEdit() {
  const ed = document.getElementById('chEditArea');
  const content = document.getElementById('chContent');
  const actions = document.getElementById('editActions');
  const btn = document.getElementById('editBtn');
  const editing = ed.style.display !== 'none';
  if (editing) {
    ed.style.display = 'none'; content.style.display = 'block';
    actions.style.display = 'none'; btn.textContent = '编辑';
  } else {
    ed.style.display = 'block'; content.style.display = 'none';
    actions.style.display = 'block'; btn.textContent = '预览';
  }
}

async function saveChapterEdit() {
  const title = document.getElementById('chTitle').textContent;
  const content = document.getElementById('chEditArea').value;
  await fetch('/api/projects/' + encodeURIComponent(currentProject) + '/chapters/' + currentChapter, {
    method: 'PUT', headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({title, content})
  });
  document.getElementById('chContent').textContent = content;
  toggleEdit();
  toast('已保存');
}

// archetype → 图标 + 配色（全局，renderCharGraph 要用）
// 图标来自 Lucide Icons 官方 SVG
const CHAR_STYLE = {
  protagonist:  { color: '#ffd700', bg: '#ffd700', label: '主角',
    icon: '<path d="M11.562 3.266a.5.5 0 0 1 .876 0L15.39 8.87a1 1 0 0 0 1.516.294L21.183 5.5a.5.5 0 0 1 .798.519l-2.834 10.246a1 1 0 0 1-.956.734H5.81a1 1 0 0 1-.957-.734L2.02 6.02a.5.5 0 0 1 .798-.519l4.276 3.664a1 1 0 0 0 1.516-.294z"/><path d="M5 21h14"/>' },
  antagonist:   { color: '#ff5252', bg: '#ff5252', label: '反派',
    icon: '<path d="m12.5 17-.5-1-.5 1h1z"/><path d="M15 22a1 1 0 0 0 1-1v-1a2 2 0 0 0 1.56-3.25 8 8 0 1 0-11.12 0A2 2 0 0 0 8 20v1a1 1 0 0 0 1 1z"/><circle cx="15" cy="12" r="1"/><circle cx="9" cy="12" r="1"/>' },
  family:       { color: '#4fc3f7', bg: '#4fc3f7', label: '家人',
    icon: '<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>' },
  warrior:      { color: '#ff7043', bg: '#ff7043', label: '武将',
    icon: '<polyline points="14.5 17.5 3 6 3 3 6 3 17.5 14.5"/><line x1="13" x2="19" y1="19" y2="13"/><line x1="16" x2="20" y1="16" y2="20"/><line x1="19" x2="21" y1="21" y2="19"/>' },
  sage:         { color: '#ce93d8', bg: '#ce93d8', label: '谋士/法师',
    icon: '<path d="m21.64 3.64-1.28-1.28a1.21 1.21 0 0 0-1.72 0L2.36 18.64a1.21 1.21 0 0 0 0 1.72l1.28 1.28a1.2 1.2 0 0 0 1.72 0L21.64 5.36a1.2 1.2 0 0 0 0-1.72"/><path d="m14 7 3 3"/><path d="M5 6v4"/><path d="M19 14v4"/><path d="M10 2v2"/><path d="M7 8H3"/><path d="M21 16h-4"/><path d="M11 3H9"/>' },
  noble:        { color: '#ffb74d', bg: '#ffb74d', label: '权贵',
    icon: '<line x1="3" x2="21" y1="22" y2="22"/><line x1="6" x2="6" y1="18" y2="11"/><line x1="10" x2="10" y1="18" y2="11"/><line x1="14" x2="14" y1="18" y2="11"/><line x1="18" x2="18" y1="18" y2="11"/><polygon points="12 2 20 7 4 7"/>' },
  creature:     { color: '#81c784', bg: '#81c784', label: '动物/灵兽',
    icon: '<circle cx="11" cy="4" r="2"/><circle cx="18" cy="8" r="2"/><circle cx="20" cy="16" r="2"/><path d="M9 10a5 5 0 0 1 5 5v3.5a3.5 3.5 0 0 1-6.84 1.045Q6.52 17.48 4.46 16.84A3.5 3.5 0 0 1 5.5 10Z"/>' },
  divine:       { color: '#fff176', bg: '#fff176', label: '神仙',
    icon: '<circle cx="12" cy="12" r="4"/><path d="M12 2v2"/><path d="M12 20v2"/><path d="m4.93 4.93 1.41 1.41"/><path d="m17.66 17.66 1.41 1.41"/><path d="M2 12h2"/><path d="M20 12h2"/><path d="m6.34 17.66-1.41 1.41"/><path d="m19.07 4.93-1.41 1.41"/>' },
  demon:        { color: '#9c27b0', bg: '#9c27b0', label: '鬼怪妖魔',
    icon: '<path d="M9 10h.01"/><path d="M15 10h.01"/><path d="M12 2a8 8 0 0 0-8 8v12l3-3 2.5 2.5L12 19l2.5 2.5L17 19l3 3V10a8 8 0 0 0-8-8z"/>' },
  female:       { color: '#f48fb1', bg: '#f48fb1', label: '女性',
    icon: '<path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/>' },
  mysterious:   { color: '#b0bec5', bg: '#b0bec5', label: '神秘/危险',
    icon: '<path d="M2.062 12.348a1 1 0 0 1 0-.696 10.75 10.75 0 0 1 19.876 0 1 1 0 0 1 0 .696 10.75 10.75 0 0 1-19.876 0"/><circle cx="12" cy="12" r="3"/>' },
  faction:      { color: '#a5d6a7', bg: '#a5d6a7', label: '势力/组织',
    icon: '<path d="M4 15s1-1 4-1 5 2 8 2 4-1 4-1V3s-1 1-4 1-5-2-8-2-4 1-4 1z"/><line x1="4" x2="4" y1="22" y2="15"/>' },
  npc:          { color: '#90a4ae', bg: '#90a4ae', label: '配角',
    icon: '<circle cx="12" cy="8" r="5"/><path d="M20 21a8 8 0 0 0-16 0"/>' },
  plant:        { color: '#66bb6a', bg: '#66bb6a', label: '植物精怪',
    icon: '<path d="M12 5a3 3 0 1 1 3 3m-3-3a3 3 0 1 0-3 3m3-3v1M9 8a3 3 0 1 0 3 3M9 8h1m5 0a3 3 0 1 1-3 3m3-3h-1m-2 3v-1"/><circle cx="12" cy="8" r="2"/><path d="M12 10v12"/><path d="M12 22c4.2 0 7-1.667 7-5-4.2 0-7 1.667-7 5Z"/><path d="M12 22c-4.2 0-7-1.667-7-5 4.2 0 7 1.667 7 5Z"/>' },
  robot:        { color: '#78909c', bg: '#78909c', label: '机械/机器人',
    icon: '<path d="M12 8V4H8"/><rect width="16" height="12" x="4" y="8" rx="2"/><path d="M2 14h2"/><path d="M20 14h2"/><path d="M15 13v2"/><path d="M9 13v2"/>' },
  assassin:     { color: '#546e7a', bg: '#546e7a', label: '刺客',
    icon: '<path d="M10.733 5.076a10.744 10.744 0 0 1 11.205 6.575 1 1 0 0 1 0 .696 10.747 10.747 0 0 1-1.444 2.49"/><path d="M14.084 14.158a3 3 0 0 1-4.242-4.242"/><path d="M17.479 17.499a10.75 10.75 0 0 1-15.417-5.151 1 1 0 0 1 0-.696 10.75 10.75 0 0 1 4.446-5.143"/><path d="m2 2 20 20"/>' },
  merchant:     { color: '#ffca28', bg: '#ffca28', label: '商人',
    icon: '<path d="M6 2 3 6v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6l-3-4Z"/><path d="M3 6h18"/><path d="M16 10a4 4 0 0 1-8 0"/>' },
  healer:       { color: '#f06292', bg: '#f06292', label: '医生/治疗',
    icon: '<path d="M19 14c1.49-1.46 3-3.21 3-5.5A5.5 5.5 0 0 0 16.5 3c-1.76 0-3 .5-4.5 2-1.5-1.5-2.74-2-4.5-2A5.5 5.5 0 0 0 2 8.5c0 2.3 1.5 4.05 3 5.5l7 7Z"/><path d="M3.22 12H9.5l.5-1 2 4.5 2-7 1.5 3.5h5.27"/>' },
  artisan:      { color: '#a1887f', bg: '#a1887f', label: '工匠/炼器',
    icon: '<path d="m15 12-8.373 8.373a1 1 0 1 1-3-3L12 9"/><path d="m18 15 4-4"/><path d="m21.5 11.5-1.914-1.914A2 2 0 0 1 19 8.172V7l-2.26-2.26a6 6 0 0 0-4.202-1.756L9 2.96l.92.82A6.18 6.18 0 0 1 12 8.4V10l2 2h1.172a2 2 0 0 1 1.414.586L18.5 14.5"/>' },
  elf:          { color: '#b9f6ca', bg: '#b9f6ca', label: '精灵',
    icon: '<path d="M9.937 15.5A2 2 0 0 0 8.5 14.063l-6.135-1.582a.5.5 0 0 1 0-.962L8.5 9.936A2 2 0 0 0 9.937 8.5l1.582-6.135a.5.5 0 0 1 .963 0L14.063 8.5A2 2 0 0 0 15.5 9.937l6.135 1.581a.5.5 0 0 1 0 .964L15.5 14.063a2 2 0 0 0-1.437 1.437l-1.582 6.135a.5.5 0 0 1-.963 0z"/><path d="M20 3v4"/><path d="M22 5h-4"/><path d="M4 17v2"/><path d="M5 18H3"/>' },
  dragon:       { color: '#ef5350', bg: '#ef5350', label: '龙族',
    icon: '<path d="M8.5 14.5A2.5 2.5 0 0 0 11 12c0-1.38-.5-2-1-3-1.072-2.143-.224-4.054 2-6 .5 2.5 2 4.9 4 6.5 2 1.6 3 3.5 3 5.5a7 7 0 1 1-14 0c0-1.153.433-2.294 1-3a2.5 2.5 0 0 0 2.5 2.5z"/>' },
  elemental:    { color: '#4dd0e1', bg: '#4dd0e1', label: '元素生物',
    icon: '<path d="M4 14a1 1 0 0 1-.78-1.63l9.9-10.2a.5.5 0 0 1 .86.46l-1.92 6.02A1 1 0 0 0 13 10h7a1 1 0 0 1 .78 1.63l-9.9 10.2a.5.5 0 0 1-.86-.46l1.92-6.02A1 1 0 0 0 11 14z"/>' },
};

async function loadCharacters() {
  if (!currentProject) return;
  const chars = await (await fetch('/api/projects/' + encodeURIComponent(currentProject) + '/characters')).json();
  // 从 canon 读主角/反派名
  let protagName = '', villainName = '';
  try {
    const canon = await (await fetch('/api/projects/' + encodeURIComponent(currentProject) + '/settings')).json();
    protagName = (canon.protagonist_name || '').trim();
    const villainDesc = (canon.villain || '').trim();
    const kin = villainDesc.match(/之[侄孙子徒][——\s]*([一-龥]{2,3})/);
    if (kin) villainName = kin[1];
    else {
      const dash = villainDesc.split(/[——\-]/).pop() || '';
      const m = dash.match(/^([一-龥]{2,3})/);
      if (m) villainName = m[0];
    }
  } catch (e) {}
  const tagged = chars.map(c => {
    let role = c.role_type || 'support';
    if (protagName && c.name.includes(protagName)) role = 'protagonist';
    else if (villainName && c.name.includes(villainName)) role = 'antagonist';
    return { ...c, _role: role };
  });

  // archetype → 图标 + 配色已提到全局 CHAR_STYLE
  window._allChars = tagged;
  renderCharGraph();
}

function renderCharGraph() {
  const all = window._allChars || [];
  const q = (document.getElementById('charSearch')?.value || '').toLowerCase();
  const filter = document.getElementById('charFilter')?.value || 'all';
  const filtered = all.filter(c => {
    if (q && !c.name.toLowerCase().includes(q)) return false;
    if (filter === 'all') return true;
    if (filter === 'main') return c._role === 'protagonist' || c._role === 'antagonist';
    return (c.archetype || 'npc') === filter;
  });

  const isDead = (c) => {
    const t = (c.state || '') + (c.notes || '');
    return /死|尸|消散|静止|击杀|陨落|寂灭|陨落|殒|亡/.test(t);
  };
  const card = (c) => {
    const s = c._role === 'protagonist' || c._role === 'antagonist' ? CHAR_STYLE[c._role] : (CHAR_STYLE[c.archetype] || CHAR_STYLE.npc);
    const dead = isDead(c);
    return `<div style="background:rgba(0,0,0,0.2);border:1px solid var(--border);border-left:3px solid ${s.color};border-radius:12px;padding:12px;transition:all 0.2s;${dead?'opacity:0.6;':''}" onmouseover="this.style.borderColor='var(--accent)'" onmouseout="this.style.borderColor='var(--border)'">
      <div style="display:flex;align-items:center;gap:10px">
        <div style="width:36px;height:36px;border-radius:50%;background:${s.bg};display:flex;align-items:center;justify-content:center;color:white;flex-shrink:0">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">${s.icon}</svg>
        </div>
        <div style="flex:1;min-width:0">
          <div style="font-weight:600;font-size:13px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${c.name}</div>
          <div style="font-size:11px;color:${s.color};margin-top:2px">${s.label} · 第${c.first_chapter||0}章出场</div>
        </div>
      </div>
      <div style="margin-top:6px">
        <span style="font-size:10px;padding:2px 8px;border-radius:10px;${dead?'background:rgba(255,107,107,0.15);color:#ff6b6b;':'background:rgba(106,191,105,0.15);color:#6abf69;'}">${dead?'死亡':'存活'}</span>
      </div>
      ${c.state ? `<div style="font-size:11px;color:var(--text-dim);margin-top:6px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${c.state}</div>` : ''}
    </div>`;
  };

  document.getElementById('charGraph').innerHTML = filtered.length
    ? filtered.map(card).join('')
    : '<p style="color:var(--text-dim);grid-column:1/-1">没有匹配的人物</p>';
}

async function drawTimeline() {
  const canvas = document.getElementById('timelineCanvas');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  const W = canvas.width, H = canvas.height;
  ctx.clearRect(0, 0, W, H);
  const data = await (await fetch('/api/projects/' + encodeURIComponent(currentProject) + '/chapters')).json();
  const chs = data.chapters || [];
  if (!chs.length) return;
  // 获取时间线事件
  const timeline = await (await fetch('/api/projects/' + encodeURIComponent(currentProject) + '/timeline')).json();
  const step = (W - 40) / chs.length;
  // 画主线（上面）
  ctx.strokeStyle = '#8aae3c'; ctx.lineWidth = 2;
  ctx.beginPath(); ctx.moveTo(20, H/3); ctx.lineTo(W-20, H/3); ctx.stroke();
  // 画伏笔线（下面）
  ctx.strokeStyle = '#4a9eff'; ctx.lineWidth = 2;
  ctx.beginPath(); ctx.moveTo(20, H*2/3); ctx.lineTo(W-20, H*2/3); ctx.stroke();
  // 记录每个点的位置和章节号
  window.timelinePoints = [];
  chs.forEach((c, i) => {
    const x = 30 + i * step;
    window.timelinePoints.push({ x: x, chapter: c.num });
    // 重要性分级：如果有fight事件，用红点
    const events = timeline.filter(e => e.chapter === c.num);
    const hasFight = events.some(e => e.type === 'fight');
    const hasDiscovery = events.some(e => e.type === 'discovery');
    // 主线的点在上面
    if (hasFight) {
      ctx.fillStyle = '#ff6b6b'; // 红点 = 战斗
    } else if (hasDiscovery) {
      ctx.fillStyle = '#ffd93d'; // 黄点 = 发现
    } else {
      ctx.fillStyle = '#b5d96a'; // 绿点 = 普通
    }
    ctx.beginPath(); ctx.arc(x, H/3, 5, 0, Math.PI*2); ctx.fill();
    // 伏笔线的点在下面（蓝色）
    ctx.fillStyle = '#4a9eff';
    ctx.beginPath(); ctx.arc(x, H*2/3, 4, 0, Math.PI*2); ctx.fill();
    // 显示章节号
    ctx.fillStyle = '#888'; ctx.font = '10px sans-serif';
    ctx.fillText(String(c.num), x-4, H/3 + 20);
    // 显示章节标题（如果有的话）
    if (c.title) {
      ctx.fillStyle = '#666'; ctx.font = '9px sans-serif';
      ctx.fillText(c.title.substring(0, 5), x-10, H/3 - 10);
    }
    // 显示事件摘要
    if (events.length > 0) {
      ctx.fillStyle = '#8aae3c'; ctx.font = '8px sans-serif';
      ctx.fillText(events[0].summary.substring(0, 10), x-20, H/3 + 40);
    }
  });
  // 点击事件
  canvas.onclick = function(e) {
    const rect = canvas.getBoundingClientRect();
    const scaleX = canvas.width / rect.width;
    const clickX = (e.clientX - rect.left) * scaleX;
    // 找最近的点
    let nearest = null, minDist = 999;
    window.timelinePoints.forEach(p => {
      const dist = Math.abs(p.x - clickX);
      if (dist < minDist) { minDist = dist; nearest = p; }
    });
    if (nearest) {
      // 显示该章的事件
      const events = timeline.filter(e => e.chapter === nearest.chapter);
      const detailDiv = document.getElementById('timelineDetail');
      if (events.length > 0) {
        let html = '<div style="color:#b5d96a;font-weight:bold;margin-bottom:8px">第' + nearest.chapter + '章</div>';
        events.forEach(ev => {
          // 类型翻译成中文
          const typeMap = {
            'discovery': '发现',
            'transition': '过渡',
            'dialogue': '对话',
            'fight': '战斗'
          };
          const typeName = typeMap[ev.type] || ev.type || '事件';
          html += '<div style="margin-bottom:8px;padding:8px;background:#0a0a14;border-radius:4px">';
          html += '<div style="color:#8aae3c;font-size:11px;margin-bottom:4px">' + typeName + '</div>';
          html += '<div style="margin-bottom:4px">' + (ev.summary || '') + '</div>';
          if (ev.location) html += '<div style="color:#888;font-size:11px">地点：' + ev.location + '</div>';
          if (ev.elapsed) html += '<div style="color:#ffd93d;font-size:11px">时间流逝：' + ev.elapsed + '</div>';
          if (ev.characters && ev.characters.length > 0) html += '<div style="color:#b5d96a;font-size:11px">出场人物：' + ev.characters.join('、') + '</div>';
          html += '</div>';
        });
        detailDiv.innerHTML = html;
      } else {
        detailDiv.innerHTML = '<div style="color:#b5d96a;font-weight:bold">第' + nearest.chapter + '章</div><div>暂无事件数据</div>';
      }
    }
  };
}

async function loadForeshadows() {
  if (!currentProject) { document.getElementById('fsList').innerHTML = '<p style="color:var(--text-dim);padding:20px">请先选择项目</p>'; return; }
  const fs = await (await fetch('/api/projects/' + encodeURIComponent(currentProject) + '/foreshadows')).json();
  const active = fs.filter(f => f.status === 'active');
  const resolved = fs.filter(f => f.status === 'resolved');
  const currentCh = parseInt(document.getElementById('ovCur').textContent) || 0;
  // overdue: 埋了15章以上还没回收
  const overdue = active.filter(f => currentCh - f.plant_chapter > 15);
  const healthy = active.filter(f => currentCh - f.plant_chapter <= 15);

  const render = (list, color) => list.length ? list.map(f => `
    <div style="padding:10px;background:var(--bg);border-radius:6px;margin-bottom:8px;font-size:13px;border-left:3px solid ${color}">
      <div>第${f.plant_chapter}章埋${f.resolve_chapter ? ' → 第' + f.resolve_chapter + '章收' : ''}</div>
      <div style="margin-top:4px;color:var(--text)">${f.plant_summary}</div>
      ${f.resolve_summary ? `<div style="margin-top:4px;color:var(--text-dim);font-size:12px">回收：${f.resolve_summary}</div>` : ''}
    </div>
  `).join('') : '<p style="color:var(--text-dim);font-size:13px">无</p>';

  document.getElementById('fsList').innerHTML = `
    <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:16px">
      <div>
        <div style="font-size:13px;font-weight:600;color:var(--red);margin-bottom:8px"><svg style="width:14px;height:14px;vertical-align:middle" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg> 超期未收（${overdue.length}）</div>
        ${render(overdue, '#ff6b6b')}
      </div>
      <div>
        <div style="font-size:13px;font-weight:600;color:var(--orange);margin-bottom:8px"><svg style="width:14px;height:14px;vertical-align:middle" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg> 进行中（${healthy.length}）</div>
        ${render(healthy, '#fdcb6e')}
      </div>
      <div>
        <div style="font-size:13px;font-weight:600;color:var(--green);margin-bottom:8px"><svg style="width:14px;height:14px;vertical-align:middle" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"/></svg> 已回收（${resolved.length}）</div>
        ${render(resolved, '#00b894')}
      </div>
    </div>`;
}

async function loadWritingCalendar() {
  const r = await (await fetch('/api/writing_calendar')).json();
  const calendar = r.calendar || [];
  
  if (calendar.length === 0) {
    document.getElementById('writingCalendar').innerText = '还没有写作记录';
    return;
  }
  
  // 计算总字数和连续打卡天数
  const totalWords = calendar.reduce((sum, d) => sum + d.words, 0);
  
  // 最近7天的写作记录
  const recent7 = calendar.slice(-7);
  let html = `总字数：${(totalWords / 10000).toFixed(1)}万字\n\n`;
  html += `最近7天：\n`;
  recent7.forEach(d => {
    const bar = '█'.repeat(Math.min(20, Math.floor(d.words / 200)));
    html += `${d.date.slice(5)}: ${bar} ${(d.words / 1000).toFixed(1)}k字\n`;
  });
  
  document.getElementById('writingCalendar').innerText = html;
}

async function loadOutline() {
  if (!currentProject) return;
  // 显示加载动画
  document.getElementById('outlineContent').innerHTML = '<div style="text-align:center;padding:40px;color:var(--text-dim)"><div style="display:inline-block;width:20px;height:20px;border:3px solid var(--border);border-top-color:var(--accent);border-radius:50%;animation:spin 1s linear infinite"></div><div style="margin-top:12px;font-size:13px">正在加载大纲...</div></div>';
  try {
    // 从settings里读取完整的大纲
    const r = await (await fetch('/api/projects/' + encodeURIComponent(currentProject) + '/settings')).json();
    let html = '<div style="display:grid;grid-template-columns:1fr;gap:12px">';
    if (r.title) html += `<div style="padding:12px;background:var(--bg);border-radius:8px;border-left:3px solid var(--accent)"><div style="font-size:12px;color:var(--text-dim)">书名</div><div style="font-size:15px;font-weight:600;margin-top:4px">${r.title}</div></div>`;
    if (r.genre) html += `<div style="padding:12px;background:var(--bg);border-radius:8px;border-left:3px solid var(--accent)"><div style="font-size:12px;color:var(--text-dim)">题材</div><div style="font-size:15px;font-weight:600;margin-top:4px">${r.genre}</div></div>`;
    if (r.style) html += `<div style="padding:12px;background:var(--bg);border-radius:8px;border-left:3px solid var(--accent)"><div style="font-size:12px;color:var(--text-dim)">文风</div><div style="font-size:15px;font-weight:600;margin-top:4px">${r.style}</div></div>`;
    if (r.protagonist_name) html += `<div style="padding:12px;background:var(--bg);border-radius:8px;border-left:3px solid var(--accent)"><div style="font-size:12px;color:var(--text-dim)">主角</div><div style="font-size:15px;font-weight:600;margin-top:4px">${r.protagonist_name}</div></div>`;
    if (r.gold_finger) html += `<div style="padding:12px;background:var(--bg);border-radius:8px;border-left:3px solid var(--accent)"><div style="font-size:12px;color:var(--text-dim)">金手指</div><div style="font-size:13px;margin-top:4px;line-height:1.6">${r.gold_finger}</div></div>`;
    if (r.villain) html += `<div style="padding:12px;background:var(--bg);border-radius:8px;border-left:3px solid var(--accent)"><div style="font-size:12px;color:var(--text-dim)">主要反派</div><div style="font-size:13px;margin-top:4px;line-height:1.6">${r.villain}</div></div>`;
    if (r.outline) html += `<div style="padding:12px;background:var(--bg);border-radius:8px;border-left:3px solid var(--accent)"><div style="font-size:12px;color:var(--text-dim)">总大纲</div><div style="font-size:13px;margin-top:4px;line-height:1.6">${r.outline}</div></div>`;
    html += '</div>';
    // 分章大纲
    try {
      const co = await (await fetch('/api/projects/' + encodeURIComponent(currentProject) + '/chapter-outline')).json();
      if (co.volumes && co.volumes.length) {
        html += `<div style="margin-top:16px;font-size:14px;font-weight:600">全本卷级大纲（共${co.volumes.length}卷）</div>`;
        html += '<div style="margin-top:10px;display:flex;flex-direction:column;gap:8px">';
        co.volumes.forEach(v => {
          html += `<div style="padding:12px;background:var(--bg);border-radius:8px;border-left:3px solid var(--accent)">
            <div style="display:flex;justify-content:space-between;align-items:center">
              <div style="font-size:13px;font-weight:600">第${v.volume}卷 · ${v.title || ''}</div>
              <div style="font-size:11px;color:var(--text-dim)">${v.chapters || ''}</div>
            </div>
            ${v.conflict ? `<div style="font-size:12px;color:var(--text-dim);margin-top:6px">核心冲突：${v.conflict}</div>` : ''}
            ${v.climax ? `<div style="font-size:12px;color:#ff6b6b;margin-top:3px">卷末高潮：${v.climax}</div>` : ''}
            ${v.arc ? `<div style="font-size:12px;color:#6abf69;margin-top:3px">主角成长：${v.arc}</div>` : ''}
            ${v.hook ? `<div style="font-size:12px;color:#ffd93d;margin-top:3px">勾子：${v.hook}</div>` : ''}
          </div>`;
        });
        html += '</div>';
      } else {
        html += `<div style="margin-top:16px;text-align:center;padding:20px;background:var(--bg);border-radius:8px">
          <div style="font-size:13px;color:var(--text-dim)">分卷大纲会在设定页生成总大纲时自动生成</div>
        </div>`;
      }
    } catch(e) {}
    document.getElementById('outlineContent').innerHTML = html || '还没有设定';
  } catch(e) {
    document.getElementById('outlineContent').innerText = '加载失败：' + e.message;
  }
}

async function genChapterOutline() {
  if (!currentProject) return;
  const btn = event.target;
  btn.textContent = '生成中...';
  btn.disabled = true;
  try {
    const r = await fetch('/api/projects/' + encodeURIComponent(currentProject) + '/chapter-outline', { method: 'POST' });
    const data = await r.json();
    if (data.error) { alert('生成失败: ' + data.error); return; }
    loadOutline();
  } catch(e) { alert('生成失败: ' + e); }
  finally { btn.textContent = '重新生成'; btn.disabled = false; }
}

async function loadWorldview() {
  if (!currentProject) return;
  // 先加载已保存的地图
  try {
    const mapData = await (await fetch('/api/projects/' + encodeURIComponent(currentProject) + '/world-map')).json();
    if (mapData.regions && mapData.regions.length) {
      drawWorldMap(mapData);
    }
  } catch(e) {}
  // 显示加载动画
  document.getElementById('worldviewContent').innerHTML = '<div style="text-align:center;padding:40px;color:var(--text-dim)"><div style="display:inline-block;width:20px;height:20px;border:3px solid var(--border);border-top-color:var(--accent);border-radius:50%;animation:spin 1s linear infinite"></div><div style="margin-top:12px;font-size:13px">正在加载世界观...</div></div>';
  try {
    const r = await (await fetch('/api/projects/' + encodeURIComponent(currentProject) + '/settings')).json();
    let html = '<div style="display:grid;grid-template-columns:1fr;gap:12px">';
    if (r.world_setting) html += `<div style="padding:12px;background:var(--bg);border-radius:8px;border-left:3px solid var(--accent)"><div style="font-size:12px;color:var(--text-dim)">世界观</div><div style="font-size:13px;margin-top:4px;line-height:1.6">${r.world_setting}</div></div>`;
    if (r.power_system) html += `<div style="padding:12px;background:var(--bg);border-radius:8px;border-left:3px solid var(--accent)"><div style="font-size:12px;color:var(--text-dim)">力量体系</div><div style="font-size:13px;margin-top:4px;line-height:1.6">${r.power_system}</div></div>`;
    if (r.gold_finger) html += `<div style="padding:12px;background:var(--bg);border-radius:8px;border-left:3px solid var(--accent)"><div style="font-size:12px;color:var(--text-dim)">金手指</div><div style="font-size:13px;margin-top:4px;line-height:1.6">${r.gold_finger}</div></div>`;
    if (r.villain) html += `<div style="padding:12px;background:var(--bg);border-radius:8px;border-left:3px solid var(--accent)"><div style="font-size:12px;color:var(--text-dim)">主要反派</div><div style="font-size:13px;margin-top:4px;line-height:1.6">${r.villain}</div></div>`;
    html += '</div>';
    document.getElementById('worldviewContent').innerHTML = html || '还没有世界观设定';
  } catch(e) {
    document.getElementById('worldviewContent').innerText = '还没有世界观设定';
  }
}

async function genWorldMap() {
  if (!currentProject) return;
  const btn = event.target;
  btn.textContent = '生成中...';
  btn.disabled = true;
  try {
    const r = await fetch('/api/projects/' + encodeURIComponent(currentProject) + '/world-map', { method: 'POST' });
    const data = await r.json();
    if (data.error) { alert('生成失败: ' + data.error); return; }
    drawWorldMap(data);
  } catch(e) { alert('生成失败: ' + e); }
  finally { btn.textContent = '生成世界地图'; btn.disabled = false; }
}

let _worldMapData = null;
let _worldMapScale = 1;
let _worldMapOffsetX = 0;
let _worldMapOffsetY = 0;
let _lastTouchDist = 0;
let _fsScale = 1;
let _fsOffsetX = 0;
let _fsOffsetY = 0;
let _fsDragging = false;
let _fsLastX = 0;
let _fsLastY = 0;
let _fsTouchDist = 0;

function toggleMapZoomHint() {
  const h = document.getElementById('mapZoomHint');
  h.style.display = h.style.display === 'none' ? 'block' : 'none';
  if (h.style.display === 'block') setTimeout(() => { h.style.display = 'none'; }, 3000);
}

function toggleMapFullscreen() {
  const fs = document.getElementById('mapFullscreen');
  if (fs.style.display === 'none' || !fs.style.display) {
    fs.style.display = 'flex';
    _fsScale = 1; _fsOffsetX = 0; _fsOffsetY = 0;
    renderFsMap();
    // 绑定全屏 canvas 事件
    const fc = document.getElementById('mapFullscreenCanvas');
    fc.onwheel = (e) => {
      e.preventDefault();
      const delta = e.deltaY > 0 ? 0.9 : 1.1;
      _fsScale = Math.max(0.5, Math.min(3, _fsScale * delta));
      renderFsMap();
    };
    fc.onmousedown = (e) => { _fsDragging = true; _fsLastX = e.offsetX; _fsLastY = e.offsetY; };
    fc.onmousemove = (e) => {
      if (!_fsDragging) return;
      _fsOffsetX += e.offsetX - _fsLastX;
      _fsOffsetY += e.offsetY - _fsLastY;
      _fsLastX = e.offsetX; _fsLastY = e.offsetY;
      renderFsMap();
    };
    fc.onmouseup = () => { _fsDragging = false; };
    fc.onmouseleave = () => { _fsDragging = false; };
    fc.ontouchstart = (e) => {
      if (e.touches.length === 2) {
        _fsTouchDist = Math.hypot(e.touches[0].clientX - e.touches[1].clientX, e.touches[0].clientY - e.touches[1].clientY);
      } else if (e.touches.length === 1) {
        _fsDragging = true;
        _fsLastX = e.touches[0].clientX;
        _fsLastY = e.touches[0].clientY;
      }
    };
    fc.ontouchmove = (e) => {
      e.preventDefault();
      const rect = fc.getBoundingClientRect();
      const scaleX = fc.width / rect.width;
      const scaleY = fc.height / rect.height;
      if (e.touches.length === 2) {
        const dist = Math.hypot(e.touches[0].clientX - e.touches[1].clientX, e.touches[0].clientY - e.touches[1].clientY);
        if (_fsTouchDist > 0) {
          _fsScale = Math.max(0.5, Math.min(3, _fsScale * dist / _fsTouchDist));
          renderFsMap();
        }
        _fsTouchDist = dist;
      } else if (e.touches.length === 1 && _fsDragging) {
        const tx = e.touches[0].clientX;
        const ty = e.touches[0].clientY;
        _fsOffsetX += (tx - _fsLastX) * scaleX;
        _fsOffsetY += (ty - _fsLastY) * scaleY;
        _fsLastX = tx; _fsLastY = ty;
        renderFsMap();
      }
    };
    fc.ontouchend = () => { _fsTouchDist = 0; _fsDragging = false; };
  } else {
    fs.style.display = 'none';
  }
}

function renderFsMap() {
  if (!_worldMapData) return;
  const fc = document.getElementById('mapFullscreenCanvas');
  const fctx = fc.getContext('2d');
  const W = fc.width, H = fc.height;
  fctx.save();
  fctx.setTransform(1, 0, 0, 1, 0, 0);
  fctx.clearRect(0, 0, W, H);
  fctx.fillStyle = '#0a0a14';
  fctx.fillRect(0, 0, W, H);
  fctx.restore();
  fctx.save();
  fctx.translate(_fsOffsetX, _fsOffsetY);
  fctx.scale(_fsScale, _fsScale);
  // 网格
  fctx.strokeStyle = 'rgba(138,174,60,0.05)';
  fctx.lineWidth = 1;
  for (let x = 0; x < W; x += 40) { fctx.beginPath(); fctx.moveTo(x, 0); fctx.lineTo(x, H); fctx.stroke(); }
  for (let y = 0; y < H; y += 40) { fctx.beginPath(); fctx.moveTo(0, y); fctx.lineTo(W, y); fctx.stroke(); }
  const regions = _worldMapData.regions || [];
  // 连线
  fctx.strokeStyle = 'rgba(138,174,60,0.2)';
  fctx.lineWidth = 1.5;
  fctx.setLineDash([5, 5]);
  regions.forEach((r, i) => {
    const cx1 = (r.x / 100) * W;
    const cy1 = (r.y / 100) * H;
    const dists = regions.map((other, j) => {
      if (i === j) return { j: -1, d: 999 };
      const dx = (r.x - other.x) / 100 * W;
      const dy = (r.y - other.y) / 100 * H;
      return { j, d: Math.sqrt(dx*dx + dy*dy) };
    }).filter(x => x.j >= 0).sort((a,b) => a.d - b.d);
    for (let k = 0; k < Math.min(2, dists.length); k++) {
      const other = regions[dists[k].j];
      fctx.beginPath();
      fctx.moveTo(cx1, cy1);
      fctx.lineTo((other.x / 100) * W, (other.y / 100) * H);
      fctx.stroke();
    }
  });
  fctx.setLineDash([]);
  // 区域
  regions.forEach((r, idx) => {
    const cx = (r.x / 100) * W;
    const cy = (r.y / 100) * H;
    const color = r.color || '#8aae3c';
    const rand = _seededRandom(idx * 1000 + 42);
    const points = [];
    const n = 8;
    for (let i = 0; i < n; i++) {
      const angle = (i / n) * Math.PI * 2;
      const radius = 50 + rand() * 20;
      points.push({ x: cx + Math.cos(angle) * radius, y: cy + Math.sin(angle) * radius });
    }
    fctx.beginPath();
    fctx.moveTo(points[0].x, points[0].y);
    for (let i = 1; i < points.length; i++) fctx.lineTo(points[i].x, points[i].y);
    fctx.closePath();
    fctx.fillStyle = color + '33';
    fctx.fill();
    fctx.strokeStyle = color;
    fctx.lineWidth = 2;
    fctx.stroke();
    // 地形符号
    _drawTerrain(fctx, cx, cy, r.desc, rand);
    fctx.fillStyle = '#e8f0e8';
    fctx.font = 'bold 16px sans-serif';
    fctx.textAlign = 'center';
    fctx.fillText(r.name, cx, cy - 65);
    fctx.fillStyle = color;
    fctx.font = '13px sans-serif';
    fctx.fillText(r.power || '', cx, cy + 70);
    if (r.desc) {
      fctx.fillStyle = '#8a9a8a';
      fctx.font = '11px sans-serif';
      fctx.fillText(r.desc, cx, cy + 88);
    }
  });
  fctx.restore();
}

// 简单的伪随机（固定 seed，每次渲染形状一致）
function _seededRandom(seed) {
  let s = seed;
  return () => { s = (s * 9301 + 49297) % 233280; return s / 233280; };
}

// 画地形符号
function _drawTerrain(ctx, cx, cy, desc, rand) {
  const d = desc || '';
  const hasMountain = /山|峰|岩|崖|岭/.test(d);
  const hasForest = /林|树|森|木/.test(d);
  const hasWater = /水|河|湖|海|江|溪/.test(d);
  const hasCity = /城|堡|镇|都|关/.test(d);
  const hasCave = /巢|穴|窟|洞/.test(d);
  ctx.strokeStyle = 'rgba(255,255,255,0.7)';
  ctx.fillStyle = 'rgba(255,255,255,0.5)';
  ctx.lineWidth = 1;
  // 山
  if (hasMountain) {
    for (let i = 0; i < 2; i++) {
      const x = cx + (rand() - 0.5) * 30;
      const y = cy + (rand() - 0.5) * 20;
      ctx.beginPath();
      ctx.moveTo(x - 6, y + 4);
      ctx.lineTo(x, y - 6);
      ctx.lineTo(x + 6, y + 4);
      ctx.stroke();
    }
  }
  // 树
  if (hasForest) {
    for (let i = 0; i < 2; i++) {
      const x = cx + (rand() - 0.5) * 30;
      const y = cy + (rand() - 0.5) * 20;
      ctx.beginPath();
      ctx.moveTo(x, y - 5);
      ctx.lineTo(x - 4, y + 2);
      ctx.lineTo(x + 4, y + 2);
      ctx.closePath();
      ctx.stroke();
      ctx.beginPath();
      ctx.moveTo(x, y + 2);
      ctx.lineTo(x, y + 5);
      ctx.stroke();
    }
  }
  // 水
  if (hasWater) {
    const x = cx + (rand() - 0.5) * 30;
    const y = cy + (rand() - 0.5) * 20;
    ctx.beginPath();
    ctx.moveTo(x - 6, y);
    ctx.quadraticCurveTo(x - 3, y - 3, x, y);
    ctx.quadraticCurveTo(x + 3, y + 3, x + 6, y);
    ctx.stroke();
  }
  // 城市
  if (hasCity) {
    const x = cx + (rand() - 0.5) * 20;
    const y = cy + (rand() - 0.5) * 20;
    ctx.strokeRect(x - 4, y - 4, 8, 8);
  }
  // 洞穴
  if (hasCave) {
    const x = cx + (rand() - 0.5) * 20;
    const y = cy + (rand() - 0.5) * 20;
    ctx.beginPath();
    ctx.arc(x, y, 5, Math.PI, 0);
    ctx.stroke();
  }
}

function drawWorldMap(data) {
  _worldMapData = data;
  const container = document.getElementById('worldMapContainer');
  const canvas = document.getElementById('worldMapCanvas');
  const legend = document.getElementById('worldMapLegend');
  container.style.display = 'block';
  const ctx = canvas.getContext('2d');
  const W = canvas.width, H = canvas.height;

  const render = () => {
    ctx.save();
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.clearRect(0, 0, W, H);
    ctx.fillStyle = '#0a0a14';
    ctx.fillRect(0, 0, W, H);
    ctx.restore();

    ctx.save();
    ctx.translate(_worldMapOffsetX, _worldMapOffsetY);
    ctx.scale(_worldMapScale, _worldMapScale);

    // 网格
    ctx.strokeStyle = 'rgba(138,174,60,0.05)';
    ctx.lineWidth = 1;
    for (let x = 0; x < W; x += 40) { ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, H); ctx.stroke(); }
    for (let y = 0; y < H; y += 40) { ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(W, y); ctx.stroke(); }

    const regions = data.regions || [];
    // 连线
    ctx.strokeStyle = 'rgba(138,174,60,0.2)';
    ctx.lineWidth = 1.5;
    ctx.setLineDash([5, 5]);
    regions.forEach((r, i) => {
      const cx1 = (r.x / 100) * W;
      const cy1 = (r.y / 100) * H;
      const dists = regions.map((other, j) => {
        if (i === j) return { j: -1, d: 999 };
        const dx = (r.x - other.x) / 100 * W;
        const dy = (r.y - other.y) / 100 * H;
        return { j, d: Math.sqrt(dx*dx + dy*dy) };
      }).filter(x => x.j >= 0).sort((a,b) => a.d - b.d);
      for (let k = 0; k < Math.min(2, dists.length); k++) {
        const other = regions[dists[k].j];
        ctx.beginPath();
        ctx.moveTo(cx1, cy1);
        ctx.lineTo((other.x / 100) * W, (other.y / 100) * H);
        ctx.stroke();
      }
    });
    ctx.setLineDash([]);

    // 不规则多边形区域
    regions.forEach((r, idx) => {
      const cx = (r.x / 100) * W;
      const cy = (r.y / 100) * H;
      const color = r.color || '#8aae3c';
      const rand = _seededRandom(idx * 1000 + 42);
      // 生成不规则多边形（8 个点）
      const points = [];
      const n = 8;
      for (let i = 0; i < n; i++) {
        const angle = (i / n) * Math.PI * 2;
        const radius = 35 + rand() * 15;
        points.push({ x: cx + Math.cos(angle) * radius, y: cy + Math.sin(angle) * radius });
      }
      // 画多边形
      ctx.beginPath();
      ctx.moveTo(points[0].x, points[0].y);
      for (let i = 1; i < points.length; i++) ctx.lineTo(points[i].x, points[i].y);
      ctx.closePath();
      ctx.fillStyle = color + '33';
      ctx.fill();
      ctx.strokeStyle = color;
      ctx.lineWidth = 2;
      ctx.stroke();
      // 地形纹理（山/树/水/城）
      _drawTerrain(ctx, cx, cy, r.desc, rand);
      // 名字
      ctx.fillStyle = '#e8f0e8';
      ctx.font = 'bold 13px sans-serif';
      ctx.textAlign = 'center';
      ctx.fillText(r.name, cx, cy - 50);
      // 势力
      ctx.fillStyle = color;
      ctx.font = '11px sans-serif';
      ctx.fillText(r.power || '', cx, cy + 55);
      // 存位置用于点击检测
      r._cx = cx; r._cy = cy; r._radius = 45;
    });

    ctx.restore();
  };

  render();

  // 缩放（滚轮）
  canvas.onwheel = (e) => {
    e.preventDefault();
    const delta = e.deltaY > 0 ? 0.9 : 1.1;
    _worldMapScale = Math.max(0.5, Math.min(3, _worldMapScale * delta));
    render();
  };
  // 拖拽平移
  let dragging = false, lastX = 0, lastY = 0;
  canvas.onmousedown = (e) => { dragging = true; lastX = e.offsetX; lastY = e.offsetY; };
  canvas.onmousemove = (e) => {
    if (!dragging) return;
    _worldMapOffsetX += e.offsetX - lastX;
    _worldMapOffsetY += e.offsetY - lastY;
    lastX = e.offsetX; lastY = e.offsetY;
    render();
  };
  canvas.onmouseup = () => { dragging = false; };
  canvas.onmouseleave = () => { dragging = false; };
  // 手机双指捏合缩放
  canvas.ontouchstart = (e) => {
    if (e.touches.length === 2) {
      _lastTouchDist = Math.hypot(
        e.touches[0].clientX - e.touches[1].clientX,
        e.touches[0].clientY - e.touches[1].clientY
      );
    } else if (e.touches.length === 1) {
      dragging = true;
      lastX = e.touches[0].clientX;
      lastY = e.touches[0].clientY;
    }
  };
  canvas.ontouchmove = (e) => {
    e.preventDefault();
    const rect = canvas.getBoundingClientRect();
    const scaleX = canvas.width / rect.width;
    const scaleY = canvas.height / rect.height;
    if (e.touches.length === 2) {
      const dist = Math.hypot(
        e.touches[0].clientX - e.touches[1].clientX,
        e.touches[0].clientY - e.touches[1].clientY
      );
      if (_lastTouchDist > 0) {
        const delta = dist / _lastTouchDist;
        _worldMapScale = Math.max(0.5, Math.min(3, _worldMapScale * delta));
        render();
      }
      _lastTouchDist = dist;
    } else if (e.touches.length === 1 && dragging) {
      const tx = e.touches[0].clientX;
      const ty = e.touches[0].clientY;
      _worldMapOffsetX += (tx - lastX) * scaleX;
      _worldMapOffsetY += (ty - lastY) * scaleY;
      lastX = tx; lastY = ty;
      render();
    }
  };
  canvas.ontouchend = () => { _lastTouchDist = 0; dragging = false; };
  // 点击区域
  canvas.onclick = (e) => {
    if (!_worldMapData) return;
    const rect = canvas.getBoundingClientRect();
    const scaleX = W / rect.width;
    const x = (e.offsetX * scaleX - _worldMapOffsetX) / _worldMapScale;
    const y = (e.offsetY * scaleX - _worldMapOffsetY) / _worldMapScale;
    const regions = _worldMapData.regions || [];
    for (const r of regions) {
      const dx = x - r._cx, dy = y - r._cy;
      if (Math.sqrt(dx*dx + dy*dy) < r._radius) {
        alert(`${r.name}\n势力：${r.power || '未知'}\n\n${r.desc || '暂无描述'}`);
        return;
      }
    }
  };

  // 图例
  legend.innerHTML = '';
  const regs = data.regions || [];
  const powers = {};
  regs.forEach(r => { powers[r.color] = r.power || ''; });
  Object.entries(powers).forEach(([color, power]) => {
    legend.innerHTML += `<span style="display:flex;align-items:center;gap:4px"><span style="width:10px;height:10px;border-radius:50%;background:${color}"></span>${power}</span>`;
  });
}

async function loadSettings() {
  if (!currentProject) return;
  // 加载题材列表
  try {
    const g = await (await fetch('/api/genres')).json();
    document.getElementById('sGenre').innerHTML = '<option>自动</option>' + g.genres.map(x => `<option>${x}</option>`).join('');
  } catch(e) {}
  const s = await (await fetch('/api/projects/' + encodeURIComponent(currentProject) + '/settings')).json();
  document.getElementById('sTitle').value = s.title || '';
  if (document.getElementById('sTags')) document.getElementById('sTags').value = s.tags || '';
  if (document.getElementById('sIntro')) document.getElementById('sIntro').value = s.intro || '';
  if (document.getElementById('sStyle')) document.getElementById('sStyle').value = s.style || '';
  document.getElementById('sGenre').value = s.genre || '自动';
  if (document.getElementById('sTotalChMin')) document.getElementById('sTotalChMin').value = s.total_ch_min || '100';
  if (document.getElementById('sTotalChMax')) document.getElementById('sTotalChMax').value = s.total_ch_max || '100';
  if (document.getElementById('sWordsMin')) document.getElementById('sWordsMin').value = s.words_min || '1900';
  if (document.getElementById('sWordsMax')) document.getElementById('sWordsMax').value = s.words_max || '2100';
  document.getElementById('sName').value = s.protagonist_name || '';
  document.getElementById('sRealm').value = s.protagonist_realm || '';
  document.getElementById('sPersonality').value = s.protagonist_personality || '';
  if (document.getElementById('sTag')) document.getElementById('sTag').value = s.character_tag || '';
  if (document.getElementById('sShortGoal')) document.getElementById('sShortGoal').value = s.short_goal || '';
  if (document.getElementById('sEmotionHook')) document.getElementById('sEmotionHook').value = s.emotion_hook || '';
  document.getElementById('sGold').value = s.gold_finger || '';
  document.getElementById('sPower').value = s.power_system || '';
  document.getElementById('sVillain').value = s.villain || '';
  document.getElementById('sWorld').value = s.world_setting || '';
  document.getElementById('sOutline').value = s.outline || '';
  if (document.getElementById('sPhases')) document.getElementById('sPhases').value = s.phases || '';
  // 分卷大纲
  const sVo = document.getElementById('sVolumeOutline');
  if (sVo) {
    fetch('/api/projects/' + encodeURIComponent(currentProject) + '/chapter-outline')
      .then(r => r.json())
      .then(co => {
        if (co.volumes && co.volumes.length) {
          sVo.innerHTML = co.volumes.map(v => 
            `<div style="margin-bottom:6px;padding:6px;background:rgba(138,174,60,0.1);border-radius:6px">
              <div style="font-weight:600;color:var(--text)">第${v.volume}卷 · ${v.title || ''} <span style="font-weight:normal;color:var(--text-dim)">(${v.chapters || ''})</span></div>
              ${v.conflict ? `<div style="margin-top:3px">冲突：${v.conflict}</div>` : ''}
              ${v.climax ? `<div style="color:#ff6b6b">高潮：${v.climax}</div>` : ''}
            </div>`
          ).join('');
        }
      }).catch(() => {});
  }
}

async function runImport() {
  const text = document.getElementById('importText').value.trim();
  if (!text) return toast('先粘贴内容');
  document.getElementById('importResult').innerText = '导入中...';
  const r = await (await fetch('/api/import', {
    method: 'POST', headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({project: currentProject, title: document.getElementById('sTitle').value, content: text})
  })).json();
  document.getElementById('importResult').innerText = `已导入 ${r.imported_chapters} 章`;
}

async function uploadFile() {
  const f = document.getElementById('importFile').files[0];
  if (!f) return;
  document.getElementById('importResult').innerText = '上传中...';
  const fd = new FormData();
  fd.append('project', currentProject);
  fd.append('file', f);
  const r = await (await fetch('/api/import-file', {method: 'POST', body: fd})).json();
  document.getElementById('importResult').innerText = r.error || `已导入 ${r.imported_chapters} 章`;
}

async function extractStyle() {
  const text = document.getElementById('styleText').value.trim();
  if (!text) return toast('先粘贴参考文本');
  document.getElementById('styleResult').innerText = '提取中...';
  const r = await (await fetch('/api/extract-style', {
    method: 'POST', headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({project: currentProject, reference_text: text})
  })).json();
  if (r.style) {
    document.getElementById('styleResult').innerText = `风格指纹已保存：${r.style.style_guide || ''}`;
  } else {
    document.getElementById('styleResult').innerText = r.error || '失败';
  }
}

async function runDeslop() {
  const ch = parseInt(document.getElementById('deslopCh').value);
  if (!ch) return toast('填章节号');
  document.getElementById('deslopResult').innerText = '重写中...';
  const r = await (await fetch('/api/deslop', {
    method: 'POST', headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({project: currentProject, chapter: ch})
  })).json();
  document.getElementById('deslopResult').innerText = `完成: ${r.before}字 → ${r.after}字`;
}

async function runReview() {
  const ch = parseInt(document.getElementById('reviewCh').value);
  if (!ch) return toast('填章节号');
  document.getElementById('reviewResult').innerText = '审稿中...';
  const r = await (await fetch('/api/review', {
    method: 'POST', headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({project: currentProject, chapter: ch})
  })).json();
  document.getElementById('reviewResult').innerText = JSON.stringify(r, null, 2);
}

async function runRadar() {
  document.getElementById('radarResult').innerHTML = '<div style="text-align:center;color:var(--text-dim);padding:40px">分析中（约5秒）...</div>';
  const r = await (await fetch('/api/radar')).json();
  const icons = {
    '都市': '<rect x="3" y="3" width="18" height="18" rx="2"/><path d="M3 9h18M9 21V9"/>',
    '修仙': '<path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/>',
    '系统': '<circle cx="12" cy="12" r="3"/><path d="M12 1v6m0 10v6M4.22 4.22l4.24 4.24m7.08 7.08l4.24 4.24M1 12h6m10 0h6"/>',
    '历史': '<circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 4"/>',
    '游戏': '<line x1="6" y1="12" x2="10" y2="12"/><line x1="8" y1="10" x2="8" y2="14"/><rect x="2" y="6" width="20" height="12" rx="2"/>',
    '科幻': '<circle cx="12" cy="12" r="3"/><circle cx="12" cy="12" r="10"/>',
    '悬疑': '<path d="M9 12l2 2 4-4"/><circle cx="12" cy="12" r="10"/>',
    '言情': '<path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"/>',
    '默认': '<path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/>'
  };
  function getIcon(genre) {
    for (const k in icons) if (genre.includes(k)) return icons[k];
    return icons['默认'];
  }
  let html = '';
  if (r.rising && r.rising.length) {
    html += '<div style="margin:16px 0 8px;font-size:14px;color:var(--accent-light)">正在上升</div>';
    r.rising.forEach(t => {
      html += '<div style="display:flex;gap:12px;background:rgba(138,174,60,0.08);border-radius:14px;padding:14px;margin:10px 0">'
        + '<div style="flex-shrink:0;width:44px;height:44px;background:rgba(138,174,60,0.15);border-radius:12px;display:flex;align-items:center;justify-content:center;color:var(--accent-light)">'
        + '<svg style="width:22px;height:22px" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">' + getIcon(t.genre) + '</svg></div>'
        + '<div style="flex:1;min-width:0">'
        + '<div style="font-size:16px;font-weight:600;color:var(--accent-light)">' + t.genre + '</div>'
        + '<div style="font-size:12px;color:var(--text-dim);margin:4px 0">' + t.why + '</div>'
        + '<div style="font-size:13px;color:var(--orange);padding:6px 8px;background:rgba(228,136,63,0.1);border-radius:6px;margin:6px 0">钩子：' + t.hook + '</div>'
        + '</div></div>';
    });
  }
  if (r.avoid && r.avoid.length) {
    html += '<div style="margin:16px 0 8px;font-size:14px;color:var(--red)">别碰</div><div style="display:flex;flex-wrap:wrap;gap:8px">';
    r.avoid.forEach(a => html += '<span style="padding:6px 12px;background:rgba(255,107,107,0.15);border-radius:20px;font-size:13px;color:var(--red)">' + a + '</span>');
    html += '</div>';
  }
  if (r.golden_ideas && r.golden_ideas.length) {
    html += '<div style="margin:16px 0 8px;font-size:14px;color:var(--accent-light)">黄金开篇建议</div>';
    r.golden_ideas.forEach((g,i) => html += '<div style="background:linear-gradient(135deg,rgba(138,174,60,0.15),rgba(228,136,63,0.1));padding:14px;border-radius:12px;margin:8px 0;font-size:14px"><b>#'+(i+1)+'</b> '+g+'</div>');
  }
  document.getElementById('radarResult').innerHTML = html || '分析失败，请重试';
}

async function runCover() {
  document.getElementById('coverResult').innerText = '生成中（约10-20秒）...';
  const r = await (await fetch('/api/cover/generate', {
    method: 'POST', headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
      title: document.getElementById('sTitle').value,
      genre: document.getElementById('sGenre').value,
      protagonist: document.getElementById('sName').value,
      extra_prompt: document.getElementById('coverExtra').value,
    })
  })).json();
  if (r.url) {
    document.getElementById('coverResult').innerHTML =
      `<img src="${r.url}" style="max-width:200px;border-radius:8px"><br><a href="${r.url}" target="_blank" style="font-size:12px">打开大图</a>`;
  } else {
    document.getElementById('coverResult').innerText = '失败: ' + (r.detail || JSON.stringify(r));
  }
}

async function runStyleExtract() {
  const text = document.getElementById('styleText').value.trim();
  if (!text) return toast('先粘贴文字');
  document.getElementById('styleResult').innerText = '分析中...';
  const r = await (await fetch('/api/styleguide/extract', {
    method: 'POST', headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({text: text, project: currentProject})
  })).json();
  document.getElementById('styleResult').innerText = '已学到文风：\n' + r.guide;
}

async function runDoctor() {
  const r = await (await fetch('/api/projects/' + encodeURIComponent(currentProject) + '/doctor')).json();
  let html = '';
  if (r.ok) html += '<div style="color:#4caf50"><svg style="width:14px;height:14px;vertical-align:middle" viewBox="0 0 24 24" fill="none" stroke="#4caf50" stroke-width="2"><polyline points="20 6 9 17 4 12"/></svg> 体检通过</div>';
  (r.issues||[]).forEach(i => html += `<div style="color:#f44336"><svg style="width:14px;height:14px;vertical-align:middle" viewBox="0 0 24 24" fill="none" stroke="#f44336" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg> ${i}</div>`);
  (r.warnings||[]).forEach(w => html += `<div style="color:#ff9800"><svg style="width:14px;height:14px;vertical-align:middle" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg> ${w}</div>`);
  (r.info||[]).forEach(i => html += `<div style="color:var(--text-dim)">ℹ ${i}</div>`);
  document.getElementById('doctorResult').innerHTML = html;
}

async function runDeconstruct() {
  const text = document.getElementById('deconstructText').value.trim();
  if (!text) return toast('先粘贴对标文本');
  document.getElementById('deconstructResult').innerText = '拆解中...';
  const r = await (await fetch('/api/deconstruct', {
    method: 'POST', headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({text: text, genre: document.getElementById('sGenre').value})
  })).json();
  if (r.error) {
    document.getElementById('deconstructResult').innerText = '失败: ' + (r.raw||r.error);
    return;
  }
  let html = `<b>钩子类型:</b> ${r.hook_type||''}\n`;
  html += `<b>开篇分析:</b> ${r.opening_analysis||''}\n`;
  html += `<b>爽点节奏:</b> ${r.cool_point_pattern||''}\n`;
  html += `<b>章末钩子:</b> ${r.chapter_hook||''}\n`;
  html += `<b>主角印象:</b> ${r.protagonist_impression||''}\n`;
  html += `<b>可迁移规则:</b>\n`;
  (r.transferable_rules||[]).forEach(x => html += `  • ${x}\n`);
  document.getElementById('deconstructResult').innerText = html;
}

async function runTypoCheck() {
  const ch = document.getElementById('typoCh').value;
  if (!ch) return toast('请输入章节号');
  document.getElementById('typoResult').innerText = '检查中...';
  const r = await (await fetch('/api/typo_check', {
    method: 'POST', headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({project: currentProject, chapter: parseInt(ch)})
  })).json();
  if (r.error) {
    document.getElementById('typoResult').innerText = '失败: ' + r.error;
    return;
  }
  if (r.typos.length === 0) {
    document.getElementById('typoResult').innerText = '通过：没有发现错别字';
  } else {
    let html = `发现 ${r.typos.length} 个错别字：\n`;
    r.typos.forEach(t => html += `  • 「${t.wrong}」→ 应该是「${t.right}」（第${t.line}行）\n`);
    document.getElementById('typoResult').innerText = html;
  }
}

async function runSensitiveCheck() {
  const ch = document.getElementById('sensitiveCh').value;
  if (!ch) return toast('请输入章节号');
  document.getElementById('sensitiveResult').innerText = '检查中...';
  const r = await (await fetch('/api/sensitive_check', {
    method: 'POST', headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({project: currentProject, chapter: parseInt(ch)})
  })).json();
  if (r.error) {
    document.getElementById('sensitiveResult').innerText = '失败: ' + r.error;
    return;
  }
  if (r.words.length === 0) {
    document.getElementById('sensitiveResult').innerText = '通过：没有发现敏感词';
  } else {
    let html = `发现 ${r.words.length} 个敏感词：\n`;
    r.words.forEach(w => html += `  • 「${w.word}」（出现${w.count}次）\n`);
    document.getElementById('sensitiveResult').innerText = html;
  }
}

async function saveSettings() {
  await fetch('/api/projects/' + encodeURIComponent(currentProject) + '/settings', {
    method: 'POST', headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
      title: document.getElementById('sTitle').value,
      tags: document.getElementById('sTags').value,
      intro: document.getElementById('sIntro').value,
      style: document.getElementById('sStyle').value,
      genre: document.getElementById('sGenre').value,
      total_ch_min: document.getElementById('sTotalChMin').value,
      total_ch_max: document.getElementById('sTotalChMax').value,
      words_min: document.getElementById('sWordsMin').value,
      words_max: document.getElementById('sWordsMax').value,
      protagonist_name: document.getElementById('sName').value,
      protagonist_realm: document.getElementById('sRealm').value,
      protagonist_personality: document.getElementById('sPersonality').value,
      character_tag: document.getElementById('sTag').value,
      short_goal: document.getElementById('sShortGoal').value,
      emotion_hook: document.getElementById('sEmotionHook').value,
      gold_finger: document.getElementById('sGold').value,
      power_system: document.getElementById('sPower').value,
      villain: document.getElementById('sVillain').value,
      world_setting: document.getElementById('sWorld').value,
      outline: document.getElementById('sOutline').value,
      phases: document.getElementById('sPhases').value,
    })
  });
  toast('已保存');
}

async function genOutline() {
  const topic = document.getElementById('topic').value.trim();
  if (!topic) return toast('请输入题材');
  const btn = document.querySelector('button[onclick="genOutline()"]');
  btn.disabled = true;
  btn.textContent = '生成中...';
  try {
    const total = parseInt(document.getElementById('sTotalChMax')?.value) || 100;
    const r = await fetch('/api/generate/outline', {
      method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({topic, style: document.getElementById('sGenre').value, chapters: total, project_name: currentProject})
    });
    const data = await r.json();
    if (data.error) return toast(data.error);
    document.getElementById('sTitle').value = data.title || '';
    if (document.getElementById('sTags')) document.getElementById('sTags').value = data.tags || '';
    if (document.getElementById('sIntro')) document.getElementById('sIntro').value = data.intro || '';
    if (document.getElementById('sStyle')) document.getElementById('sStyle').value = data.style || '';
    document.getElementById('sName').value = data.protagonist_name || '';
    document.getElementById('sRealm').value = data.protagonist_realm || '';
    document.getElementById('sPersonality').value = data.protagonist_personality || '';
    if (document.getElementById('sTag')) document.getElementById('sTag').value = data.character_tag || '';
    if (document.getElementById('sShortGoal')) document.getElementById('sShortGoal').value = data.short_goal || '';
    if (document.getElementById('sEmotionHook')) document.getElementById('sEmotionHook').value = data.emotion_hook || '';
    document.getElementById('sGold').value = data.gold_finger || '';
    document.getElementById('sPower').value = data.power_system || '';
    if (document.getElementById('sVillain')) document.getElementById('sVillain').value = data.villain || '';
    if (document.getElementById('sWorld')) document.getElementById('sWorld').value = data.world_setting || '';
    // 总大纲
    if (document.getElementById('sOutline')) document.getElementById('sOutline').value = data.outline || '';
    // 自动生成分章大纲
    setTimeout(async () => {
      try {
        await fetch('/api/projects/' + encodeURIComponent(currentProject) + '/chapter-outline', { method: 'POST' });
      } catch(e) {}
    }, 500);
    // 剧情大框架
    let phasesText = '';
    if (data.phases && Array.isArray(data.phases)) {
      data.phases.forEach((p, i) => {
        phasesText += `第${i+1}阶段（${p.chapters}）：${p.summary}\n`;
      });
    }
    if (document.getElementById('sPhases')) document.getElementById('sPhases').value = phasesText;
    toast('大纲已生成');
  } finally {
    btn.disabled = false;
    btn.textContent = 'AI 生成大纲';
  }
}

async function loadKeys() {
  const k = await (await fetch('/api/keys')).json();
  document.getElementById('kAgnes').placeholder = k.AGNES_KEY ? '已配置' : '未配置';
  document.getElementById('kZhipu').placeholder = k.ZHIPU_KEY ? '已配置' : '未配置';
  document.getElementById('kSilicon').placeholder = k.SILICONFLOW_KEY ? '已配置' : '未配置';
  document.getElementById('kDeepseek').placeholder = k.DEEPSEEK_KEY ? '已配置' : '未配置';
}

async function saveKeys() {
  await fetch('/api/keys', {
    method: 'POST', headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
      AGNES_KEY: document.getElementById('kAgnes').value,
      ZHIPU_KEY: document.getElementById('kZhipu').value,
      SILICONFLOW_KEY: document.getElementById('kSilicon').value,
      DEEPSEEK_KEY: document.getElementById('kDeepseek').value,
    })
  });
  toast('已保存');
}

async function loadChatProjects() {
  const dropdown = document.getElementById('projectDropdown');
  if (!dropdown) return;
  const projects = await (await fetch('/api/projects')).json();
  dropdown.innerHTML = projects.map(p => `<div onclick="switchChatProject('${p.name}')" style="padding:10px 12px;cursor:pointer;border-radius:8px;font-size:14px;color:${p.name===currentProject?'var(--accent)':'var(--text)'}" onmouseover="this.style.background='rgba(138,174,60,0.1)'" onmouseout="this.style.background='none'">${p.title || p.name}</div>`).join('');
  // 超过3个就加滑栏
  if (projects.length > 3) {
    dropdown.style.maxHeight = '150px';
    dropdown.style.overflowY = 'auto';
  }
}

function toggleProjectDropdown() {
  const dropdown = document.getElementById('projectDropdown');
  if (dropdown.style.display === 'none' || !dropdown.style.display) {
    loadChatProjects();
    dropdown.style.display = 'block';
  } else {
    dropdown.style.display = 'none';
  }
}

function switchChatProject(name) {
  currentProject = name;
  localStorage.setItem('current_project', name);
  document.getElementById('projectDropdown').style.display = 'none';
  loadChatHistory();
}

async function loadGenres() {
  const r = await (await fetch('/api/genres')).json();
  const sel = document.getElementById('sGenre');
  if (!sel) return;
  sel.innerHTML = '<option>自动</option>' + r.genres.map(g => `<option>${g}</option>`).join('');
}

// ===== 章节修改功能 =====
async function loadChapterList() {
  if (!currentProject) return;
  const r = await (await fetch('/api/projects/' + encodeURIComponent(currentProject) + '/chapters')).json();
  const sel = document.getElementById('editChapterSelect');
  if (!sel) return;
  sel.innerHTML = '<option value="">请选择章节</option>' + r.chapters.map(c => `<option value="${c.num}">第${c.num}章 ${c.title || ''}</option>`).join('');
  // 重新初始化自定义下拉框
  if (sel.nextSibling && sel.nextSibling.classList.contains('custom-select')) {
    sel.nextSibling.remove();
  }
  initCustomSelect(sel);
}

async function loadChapterForEdit() {
  const chNum = document.getElementById('editChapterSelect').value;
  if (!chNum) return;
  const r = await (await fetch('/api/projects/' + encodeURIComponent(currentProject) + '/chapters/' + chNum)).json();
  document.getElementById('originalChapterText').value = r.content || '';
  document.getElementById('modifiedChapterText').value = r.content || '';
}

async function saveModifiedChapter() {
  const chNum = document.getElementById('editChapterSelect').value;
  if (!chNum) return;
  const newContent = document.getElementById('modifiedChapterText').value;
  if (!newContent) return;
  toast('正在保存...');
  try {
    const r = await (await fetch('/api/save_chapter', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({project: currentProject, chapter_num: chNum, title: '', content: newContent})
    })).json();
    if (r.ok) toast('已保存第' + chNum + '章');
    else toast('保存失败', 'err');
  } catch(e) {
    toast('保存失败', 'err');
  }
}

async function aiModifyChapter() {
  const chNum = document.getElementById('editChapterSelect').value;
  if (!chNum) return;
  const originalText = document.getElementById('originalChapterText').value;
  const optimizeType = document.getElementById('optimizeType').value;
  
  // 根据优化类型，生成不同的prompt
  let prompt = '';
  if (optimizeType === 'structure') {
    prompt = '请优化这一章的结构，包括：节奏、场景顺序、删减冗余内容。只改结构问题，不要改文风。';
  } else if (optimizeType === 'style') {
    prompt = '请优化这一章的语气和风格，包括：人物声音一致性、世界观一致性。只改风格问题，不要改剧情。';
  } else if (optimizeType === 'polish') {
    prompt = '请润色这一章的句子，包括：删掉副词、过滤词、变化句子节奏。只改句子，不要改剧情。';
  }
  
  toast('AI正在优化...');
  try {
    const r = await (await fetch('/api/modify_chapter', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({project: currentProject, chapter_num: chNum, modify_request: prompt, modify_suggestion: '', save: false})
    })).json();
    if (r.ok && r.new_content) {
      document.getElementById('modifiedChapterText').value = r.new_content;
      toast('AI优化完成，请检查后点击应用修改');
    } else {
      toast('AI优化失败：' + (r.error || ''), 'err');
    }
  } catch(e) {
    toast('AI优化失败', 'err');
  }
}

async function saveAiResultToFeedback() {
  const chNum = document.getElementById('editChapterSelect').value;
  if (!chNum) return;
  const aiResult = document.getElementById('aiResultText').value;
  if (!aiResult) return;
  try {
    const r = await (await fetch('/api/add_feedback', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({project: currentProject, chapter_num: chNum, feedback: aiResult})
    })).json();
    if (r.ok) toast('已加到待处理修改建议！');
    else toast('添加失败', 'err');
  } catch(e) {
    toast('添加失败', 'err');
  }
}

async function aiDiagnoseChapter() {
  const chNum = document.getElementById('editChapterSelect').value;
  if (!chNum) return;
  const originalText = document.getElementById('originalChapterText').value;
  toast('AI正在诊断...');
  try {
    const r = await (await fetch('/api/chat', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({message: '请诊断这一章有什么问题，包括：节奏、人物、逻辑、文风等方面，给出具体的修改建议：\n\n' + originalText, project: currentProject, history: []})
    })).json();
    if (r.reply) {
      document.getElementById('aiResultText').value = r.reply;
      toast('AI诊断完成');
    } else {
      toast('AI诊断失败', 'err');
    }
  } catch(e) {
    toast('AI诊断失败', 'err');
  }
}

// ===== 自定义下拉框 =====
// 暂时禁用自定义下拉框，先恢复原生select
// function initCustomSelect(selectElement) {
//   // 隐藏原生select
//   selectElement.style.display = 'none';
//
//   // 创建自定义下拉框
//   const customSelect = document.createElement('div');
//   customSelect.className = 'custom-select';
//
//   // 创建触发按钮
//   const trigger = document.createElement('div');
//   trigger.className = 'custom-select-trigger';
//   trigger.textContent = selectElement.options[selectElement.selectedIndex].textContent;
//
//   // 创建选项列表
//   const options = document.createElement('div');
//   options.className = 'custom-select-options';
//
//   // 填充选项
//   for (let i = 0; i < selectElement.options.length; i++) {
//     const option = document.createElement('div');
//     option.className = 'custom-select-option' + (i === selectElement.selectedIndex ? ' selected' : '');
//     option.textContent = selectElement.options[i].textContent;
//     option.dataset.value = selectElement.options[i].value;
//     option.onclick = function() {
//       selectElement.selectedIndex = i;
//       trigger.textContent = this.textContent;
//       options.querySelectorAll('.custom-select-option').forEach(o => o.classList.remove('selected'));
//       this.classList.add('selected');
//       customSelect.classList.remove('open');
//       // 触发change事件
//       selectElement.dispatchEvent(new Event('change'));
//     };
//     options.appendChild(option);
//   }
//
//   // 点击触发按钮，打开/关闭选项列表
//   trigger.onclick = function(e) {
//     e.stopPropagation();
//     customSelect.classList.toggle('open');
//   };
//
//   // 点击外部，关闭选项列表
//   document.addEventListener('click', function() {
//     customSelect.classList.remove('open');
//   });
//
//   // 组装
//   customSelect.appendChild(trigger);
//   customSelect.appendChild(options);
//
//   // 替换原生select
//   selectElement.parentNode.insertBefore(customSelect, selectElement);
// }

// 页面加载完成后，初始化所有自定义下拉框
// window.addEventListener('load', function() {
//   document.querySelectorAll('select').forEach(sel => {
//     initCustomSelect(sel);
//   });
// });

loadProjects();
loadGenres();
loadChatProjects();

// 恢复历史对话
loadChatHistory();
