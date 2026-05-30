// Page exit transition
// The 'page-ready' class (added by FOUC guard on DOMContentLoaded) carries
// the CSS transition, so setting opacity:0 here will always animate smoothly.
(function () {
  document.addEventListener('click', function (e) {
    var a = e.target.closest('a[href]');
    if (!a || !a.href) return;

    // Skip: external links, new tab, anchors on same page, mailto/tel
    if (
      a.target === '_blank' ||
      a.hostname !== location.hostname ||
      a.href.indexOf('mailto:') === 0 ||
      a.href.indexOf('tel:') === 0 ||
      a.href.indexOf('javascript:') === 0 ||
      (a.hash && a.pathname === location.pathname)
    ) return;

    e.preventDefault();
    var href = a.href;

    document.documentElement.style.opacity = '0';
    setTimeout(function () {
      window.location.href = href;
    }, 240);
  });
})();
