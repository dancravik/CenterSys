// Боковая панель.
(function () {
  const activePage = document.currentScript.getAttribute('data-active') || '';

  const navItems = [
    { id: 'overview', href: '/1.html', label: 'Обзор',     icon: 'grid' },
    { id: 'aspects',  href: '/2.html', label: 'Аспекты',   icon: 'fileText' },
    { id: 'reviews',  href: '/3.html', label: 'Отзывы',    icon: 'message' },
    { id: 'trends',   href: '#',       label: 'Тренды',    icon: 'activity' },
    { id: 'reports',  href: '/4.html', label: 'Отчёты',    icon: 'file' },
  ];

  const navHTML = navItems
    .map(item => {
      const cls = item.id === activePage ? ' class="active"' : '';
      return `<a href="${item.href}"${cls}>${svg(item.icon)} ${item.label}</a>`;
    })
    .join('\n    ');

  const html = `
<aside class="sidebar">
  <div class="sidebar-brand">
    <div class="sidebar-logo">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="22" height="22">${ICON.graduation}</svg>
    </div>
    <div>
      <h2>UniReview</h2>
      <span>Analytics Dashboard</span>
    </div>
  </div>
  <nav>
    ${navHTML}
  </nav>
  <div class="sidebar-bottom">
    <a href="#">${svg('settings')} Настройки</a>
  </div>
</aside>`;

  document.body.insertAdjacentHTML('afterbegin', html);
})();
