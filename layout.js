// Collapsible sidebar. The preference stays in this browser.
const appShell=document.querySelector('.app');
document.querySelector('.breadcrumb').insertAdjacentHTML('afterbegin','<button class="sidebar-toggle" data-action="toggle-sidebar"><span class="nav-icon">«</span></button>');
// Collapsed links show icons only, so give each one a tooltip with its label.
document.querySelectorAll('#nav .nav-item').forEach(a=>{a.title=[...a.childNodes].filter(n=>n.nodeType===3).map(n=>n.textContent).join('').trim()});
function setSidebar(collapsed){appShell.classList.toggle('sidebar-collapsed',collapsed);save('draftmate.sidebarCollapsed',collapsed);const b=document.querySelector('.sidebar-toggle'),label=collapsed?'Expand sidebar':'Collapse sidebar';b.querySelector('.nav-icon').textContent=collapsed?'»':'«';b.setAttribute('aria-label',label);b.title=label}
document.addEventListener('click',e=>{if(e.target.closest('[data-action="toggle-sidebar"]'))setSidebar(!appShell.classList.contains('sidebar-collapsed'))});
setSidebar(read('draftmate.sidebarCollapsed',false));
// Home-screen app support (see manifest.webmanifest and sw.js).
if('serviceWorker'in navigator)navigator.serviceWorker.register('sw.js').catch(()=>{});
