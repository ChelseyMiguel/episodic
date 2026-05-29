// Page exit transition — fades out before navigating to any internal link
(function () {
  document.addEventListener('click', function (e) {
    var a = e.target.closest('a[href]');
    if (!a || !a.href) return;

    // Skip: external links, new tab, anchors, mailto/tel, javascript:
    if (
      a.target === '_blank' ||
      a.hostname !== location.hostname ||
      a.href.startsWith('mailto:') ||
      a.href.startsWith('tel:') ||
      a.href.startsWith('javascript:') ||
      a.hash && a.pathname === location.pathname
    ) return;

    e.preventDefault();
    var href = a.href;

    document.documentElement.style.transition = 'opacity 0.18s ease';
    document.documentElement.style.opacity = '0';
    setTimeout(function () {
      window.location.href = href;
    }, 190);
  });
})();
