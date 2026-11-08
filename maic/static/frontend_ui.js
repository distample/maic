const $ = (id) => document.getElementById(id);

const h = (tag, attrs, ...children) => {
  const element = document.createElement(tag);
  if (attrs) {
    Object.entries(attrs).forEach(([key, value]) => {
      if (key === 'style' && typeof value === 'object') {
        Object.assign(element.style, value);
      } else if (key.startsWith('on')) {
        element.addEventListener(key.slice(2).toLowerCase(), value);
      } else if (key === 'className') {
        element.className = value;
      } else if (key === 'innerHTML') {
        element.innerHTML = value;
      } else if (typeof value === 'boolean' && key in element) {
        element[key] = value;
      } else {
        element.setAttribute(key, value);
      }
    });
  }
  children
    .flat()
    .forEach((child) => {
      if (child != null) {
        element.append(typeof child === 'string' ? child : child);
      }
    });
  if (tag === 'button' && !element.hasAttribute('type')) element.type = 'button';
  return element;
};

// Dialogs live outside the re-rendered app. Restore both background access
// and focus on every closing path, including removal by another render.
function mountDialog(overlay, panel, title) {
  const previousFocus = document.activeElement;
  const background = [...document.body.children].filter(el => el !== overlay);
  const previousInert = background.map(el => el.inert);
  panel.setAttribute('role', 'dialog');
  panel.setAttribute('aria-modal', 'true');
  panel.setAttribute('aria-label', title);
  panel.tabIndex = -1;
  background.forEach(el => { el.inert = true; });
  let closed = false;
  const finish = () => {
    if (closed) return;
    closed = true;
    observer.disconnect();
    document.removeEventListener('keydown', onKey, true);
    background.forEach((el, i) => { el.inert = previousInert[i]; });
    if (previousFocus && previousFocus.isConnected) previousFocus.focus({preventScroll:true});
  };
  const close = () => { overlay.remove(); finish(); };
  const focusable = () => [...panel.querySelectorAll('button,input,select,textarea,a[href],[tabindex]')]
    .filter(el => !el.disabled && el.tabIndex >= 0 && el.getClientRects().length);
  const onKey = e => {
    if (e.key === 'Escape') { e.preventDefault(); e.stopImmediatePropagation(); close(); return; }
    if (e.key !== 'Tab') return;
    const items = focusable();
    const first = items[0] || panel, last = items[items.length - 1] || panel;
    if (!panel.contains(document.activeElement) || (e.shiftKey && document.activeElement === first) ||
        (!e.shiftKey && document.activeElement === last) || !items.length) {
      e.preventDefault(); (e.shiftKey ? last : first).focus();
    }
    e.stopImmediatePropagation();
  };
  const observer = new MutationObserver(() => { if (!overlay.isConnected) finish(); });
  overlay._dismiss = close;
  overlay.addEventListener('click', e => { if (e.target === overlay) close(); });
  document.body.append(overlay);
  observer.observe(document.body, {childList:true});
  document.addEventListener('keydown', onKey, true);
  (focusable()[0] || panel).focus();
  return close;
}

function captureAppFocus(app) {
  const el = document.activeElement;
  if (!el || !app.contains(el)) return null;
  const key = el.id || el.dataset.focusKey || el.getAttribute('aria-label');
  const text = el.tagName === 'BUTTON' ? el.textContent.trim() : null;
  return () => {
    const target = [...app.querySelectorAll('button,input,select,textarea,[tabindex]')].find(node =>
      key ? (node.id === key || node.dataset.focusKey === key || node.getAttribute('aria-label') === key)
        : text && node.tagName === 'BUTTON' && node.textContent.trim() === text);
    if (target && !target.disabled) target.focus({preventScroll:true});
  };
}

function _convOptionText(text) {
  return t('ui.option.'+String(text).toLowerCase().replace(/[^a-z0-9]+/g,'_').replace(/^_|_$/g,''),text);
}
