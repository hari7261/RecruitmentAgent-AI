(function() {
  function getSidebarElements() {
    return {
      sidebar: document.getElementById('sidebar'),
      overlay: document.getElementById('sidebarOverlay'),
    };
  }

  function setActiveSidebarLink() {
    var path = window.location.pathname;
    var links = document.querySelectorAll('.sidebar-nav a');
    links.forEach(function(a) {
      if (a.getAttribute('href') === path) {
        a.classList.add('active');
      } else {
        a.classList.remove('active');
      }
    });
  }

  function openSidebar() {
    var elements = getSidebarElements();
    var sidebar = elements.sidebar;
    var overlay = elements.overlay;
    if (sidebar) sidebar.classList.add('open');
    if (overlay) overlay.classList.add('open');
    if (window.innerWidth <= 768) document.body.style.overflow = 'hidden';
  }

  function closeSidebar() {
    var elements = getSidebarElements();
    var sidebar = elements.sidebar;
    var overlay = elements.overlay;
    if (sidebar) sidebar.classList.remove('open');
    if (overlay) overlay.classList.remove('open');
    document.body.style.overflow = '';
  }

  function updateSidebarUser(user) {
    if (!user) return;

    var avatar = document.getElementById('sidebarAvatar');
    var name = document.getElementById('sidebarName');
    var email = document.getElementById('sidebarEmail');
    var displayName = user.full_name || user.name || user.username || 'Workspace User';
    var displayEmail = user.email || 'Signed-in account';

    if (avatar) avatar.textContent = displayName.charAt(0).toUpperCase();
    if (name) name.textContent = displayName;
    if (email) email.textContent = displayEmail;
  }

  function loadSidebarUser() {
    fetch('/api/v1/auth/me', { credentials: 'include' })
      .then(function(response) {
        if (!response.ok) return null;
        return response.json();
      })
      .then(function(user) {
        if (user) updateSidebarUser(user);
      })
      .catch(function(error) {
        console.debug('Sidebar user info unavailable:', error);
      });
  }

  function bindResponsiveSidebarEvents() {
    document.addEventListener('keydown', function(event) {
      if (event.key === 'Escape') closeSidebar();
    });

    window.addEventListener('resize', function() {
      if (window.innerWidth > 768) {
        closeSidebar();
      }
    });
  }

  function logout() {
    fetch('/api/v1/auth/logout', { method: 'POST', credentials: 'include' })
      .finally(function() {
        window.location.href = '/ui/auth/login.html';
      });
  }

  function initSidebar() {
    setActiveSidebarLink();
    window.openSidebar = openSidebar;
    window.closeSidebar = closeSidebar;
    window.logout = logout;
    bindResponsiveSidebarEvents();
    loadSidebarUser();
  }

  function loadSidebar() {
    var root = document.getElementById('shared-sidebar-root');
    if (!root) return;

    fetch('/ui/org/shared-sidebar.html', { cache: 'no-cache' })
      .then(function(response) {
        if (!response.ok) throw new Error('Sidebar fetch failed');
        return response.text();
      })
      .then(function(html) {
        root.innerHTML = html;
        initSidebar();
      })
      .catch(function(error) {
        console.error('Unable to load sidebar:', error);
      });
  }

  loadSidebar();
})();
