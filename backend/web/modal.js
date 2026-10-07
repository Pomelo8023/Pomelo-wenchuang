// 自定义弹窗组件（独立页面共用）
let _modalResolve = null;
let _modalInjected = false;

function _injectModal() {
  if (_modalInjected) return;
  _modalInjected = true;
  const div = document.createElement('div');
  div.id = 'modalOverlay';
  div.style.cssText = 'display:none;position:fixed;inset:0;background:rgba(0,0,0,0.6);z-index:9999;align-items:center;justify-content:center';
  div.innerHTML = `
    <div style="background:#1a1a2e;border:1px solid #2a2a4e;border-radius:16px;padding:24px;min-width:320px;max-width:90vw;box-shadow:0 8px 32px rgba(0,0,0,0.4)">
      <div id="modalTitle" style="font-size:16px;font-weight:600;margin-bottom:12px;color:#e0e0e0"></div>
      <div id="modalBody" style="font-size:13px;color:#999;margin-bottom:16px;line-height:1.6"></div>
      <input id="modalInput" type="text" style="display:none;width:100%;padding:8px 12px;margin-bottom:16px;background:rgba(0,0,0,0.2);border:1px solid #2a2a4e;border-radius:8px;color:#e0e0e0;font-size:13px;box-sizing:border-box">
      <div style="display:flex;gap:10px;justify-content:flex-end">
        <button id="modalCancel" onclick="modalCancel()" style="padding:8px 16px;background:transparent;border:1px solid #2a2a4e;border-radius:8px;color:#999;cursor:pointer;font-size:13px">取消</button>
        <button id="modalOk" onclick="modalOk()" style="padding:8px 16px;background:#8aae3c;border:none;border-radius:8px;color:white;cursor:pointer;font-size:13px">确定</button>
      </div>
    </div>`;
  document.body.appendChild(div);
}

function _openModal({ title, body, input = false, placeholder = '', defaultValue = '', okText = '确定', cancelText = '取消' }) {
  _injectModal();
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
    const cancelBtn = document.getElementById('modalCancel');
    cancelBtn.textContent = cancelText;
    cancelBtn.style.display = cancelText ? 'block' : 'none';
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

function myAlert(msg, title = '提示') { return _openModal({ title, body: msg, cancelText: '' }); }
function myConfirm(msg, title = '确认') { return _openModal({ title, body: msg }); }
function myPrompt(msg, title = '输入', placeholder = '', defaultValue = '') { return _openModal({ title, body: msg, input: true, placeholder, defaultValue }); }
