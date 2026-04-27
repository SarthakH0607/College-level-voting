// ============================================================
// SmartVote — Shared Utilities
// ============================================================

const Utils = (() => {

  // ── Toast Notifications ──────────────────────────────────
  const toastContainer = (() => {
    let container = document.getElementById('toast-container');
    if (!container) {
      container = document.createElement('div');
      container.id = 'toast-container';
      document.body.appendChild(container);
    }
    return container;
  })();

  function showToast(message, type = 'info', duration = 3500) {
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;

    const icons = { success: '✅', error: '❌', warning: '⚠️', info: 'ℹ️' };
    toast.innerHTML = `
      <span class="toast-icon">${icons[type] || icons.info}</span>
      <span class="toast-message">${message}</span>
      <button class="toast-close" onclick="this.parentElement.remove()">&times;</button>
    `;

    toastContainer.appendChild(toast);
    requestAnimationFrame(() => toast.classList.add('toast-visible'));

    setTimeout(() => {
      toast.classList.remove('toast-visible');
      toast.addEventListener('transitionend', () => toast.remove());
    }, duration);
  }

  // ── Loading State ────────────────────────────────────────
  function setLoading(button, loading, originalText) {
    if (loading) {
      button.dataset.originalText = button.innerHTML;
      button.innerHTML = `<span class="spinner"></span> Loading...`;
      button.disabled = true;
      button.classList.add('btn-loading');
    } else {
      button.innerHTML = originalText || button.dataset.originalText || 'Submit';
      button.disabled = false;
      button.classList.remove('btn-loading');
    }
  }

  // ── Date Formatting ────────────────────────────────────
  function formatDate(timestamp) {
    if (!timestamp) return '—';
    const date = timestamp.toDate ? timestamp.toDate() : new Date(timestamp);
    return date.toLocaleDateString('en-US', {
      year: 'numeric', month: 'short', day: 'numeric'
    });
  }

  function formatDateTime(timestamp) {
    if (!timestamp) return '—';
    const date = timestamp.toDate ? timestamp.toDate() : new Date(timestamp);
    return date.toLocaleDateString('en-US', {
      year: 'numeric', month: 'short', day: 'numeric',
      hour: '2-digit', minute: '2-digit'
    });
  }

  function timeAgo(timestamp) {
    if (!timestamp) return '';
    const date = timestamp.toDate ? timestamp.toDate() : new Date(timestamp);
    const seconds = Math.floor((Date.now() - date.getTime()) / 1000);
    const intervals = [
      { label: 'year', seconds: 31536000 },
      { label: 'month', seconds: 2592000 },
      { label: 'week', seconds: 604800 },
      { label: 'day', seconds: 86400 },
      { label: 'hour', seconds: 3600 },
      { label: 'minute', seconds: 60 }
    ];
    for (const interval of intervals) {
      const count = Math.floor(seconds / interval.seconds);
      if (count >= 1) return `${count} ${interval.label}${count > 1 ? 's' : ''} ago`;
    }
    return 'Just now';
  }

  // ── Status Badge ─────────────────────────────────────────
  function statusBadge(status) {
    const map = {
      active:   { class: 'badge-success', label: 'Active', icon: '🟢' },
      upcoming: { class: 'badge-warning', label: 'Upcoming', icon: '🟡' },
      closed:   { class: 'badge-danger',  label: 'Closed', icon: '🔴' }
    };
    const s = map[status] || map.upcoming;
    return `<span class="badge ${s.class}">${s.icon} ${s.label}</span>`;
  }

  // ── Election Card Builder ────────────────────────────────
  function buildElectionCard(election, userVotedIn, role) {
    const hasVoted = userVotedIn && userVotedIn.includes(election.id);
    const isActive = election.status === 'active';
    const isClosed = election.status === 'closed';

    const isHtml = window.location.pathname.endsWith('.html') || window.location.pathname === '/' || window.location.pathname.indexOf('.') > -1;
    const formatLink = (page) => isHtml ? page : page.replace('.html', '');

    let actionBtn = '';
    if (isClosed) {
      actionBtn = `<a href="${formatLink('results.html')}?id=${election.id}" class="btn btn-outline btn-sm">View Results</a>`;
    } else if (hasVoted) {
      actionBtn = `<span class="badge badge-success">✔ Already Voted</span>
                   <a href="${formatLink('results.html')}?id=${election.id}" class="btn btn-outline btn-sm" style="margin-left:8px;">View Results</a>`;
    } else if (isActive) {
      if (role === 'teacher') {
        actionBtn = `<a href="${formatLink('teacher-vote.html')}?id=${election.id}" class="btn btn-primary btn-sm btn-glow">🔒 Vote with Verification</a>`;
      } else {
        actionBtn = `<a href="${formatLink('vote.html')}?id=${election.id}" class="btn btn-primary btn-sm btn-glow">Vote Now →</a>`;
      }
    } else {
      actionBtn = `<span class="badge badge-warning">🕒 Coming Soon</span>`;
    }

    const biometricBadge = election.requiresBiometric
      ? `<span class="badge badge-purple">🔒 Biometric Required</span>` : '';

    return `
      <div class="election-card card animate-fade-in">
        <div class="card-header">
          <h3 class="card-title">${election.title}</h3>
          <div class="card-badges">
            ${statusBadge(election.status)}
            ${biometricBadge}
          </div>
        </div>
        <p class="card-desc">${election.description || 'No description provided.'}</p>
        <div class="card-meta">
          <span>📅 ${formatDate(election.startDate)} — ${formatDate(election.endDate)}</span>
          <span>🗳️ ${election.totalVotes || 0} votes</span>
        </div>
        <div class="card-actions">${actionBtn}</div>
      </div>
    `;
  }

  // ── Sidebar Toggle ──────────────────────────────────────
  function initSidebar() {
    const hamburger = document.getElementById('hamburger-btn');
    const sidebar = document.getElementById('sidebar');
    const overlay = document.getElementById('sidebar-overlay');

    if (!sidebar) return;

    // Auto-inject toggle button if not present
    if (!sidebar.querySelector('.sidebar-toggle')) {
      const toggleBtn = document.createElement('button');
      toggleBtn.className = 'sidebar-toggle';
      toggleBtn.innerHTML = '<span class="toggle-icon">◀</span><span class="toggle-label">Collapse</span>';
      sidebar.appendChild(toggleBtn);
    }

    // Wrap link text in <span class="nav-text"> for collapse and add tooltips
    sidebar.querySelectorAll('.sidebar-nav li a').forEach(link => {
      if (!link.querySelector('.nav-text')) {
        const icon = link.textContent.trim().split(' ')[0]; // emoji
        const text = link.textContent.trim().substring(icon.length).trim();
        link.setAttribute('data-tooltip', text);
        link.innerHTML = icon + ' <span class="nav-text">' + text + '</span>';
      }
    });

    // Restore collapsed state from localStorage
    const isCollapsed = localStorage.getItem('smartvote-sidebar-collapsed') === 'true';
    if (isCollapsed) {
      sidebar.classList.add('sidebar-collapsed');
      document.body.classList.add('sidebar-is-collapsed');
    }

    // Toggle button click — collapse/expand
    const toggleBtn = sidebar.querySelector('.sidebar-toggle');
    if (toggleBtn) {
      toggleBtn.addEventListener('click', () => {
        sidebar.classList.toggle('sidebar-collapsed');
        document.body.classList.toggle('sidebar-is-collapsed');
        const collapsed = sidebar.classList.contains('sidebar-collapsed');
        localStorage.setItem('smartvote-sidebar-collapsed', collapsed);
        // Update label
        const label = toggleBtn.querySelector('.toggle-label');
        if (label) label.textContent = collapsed ? 'Expand' : 'Collapse';
      });
    }

    // Mobile hamburger
    if (hamburger) {
      hamburger.addEventListener('click', () => {
        sidebar.classList.toggle('sidebar-open');
        if (overlay) overlay.classList.toggle('overlay-visible');
      });
      if (overlay) {
        overlay.addEventListener('click', () => {
          sidebar.classList.remove('sidebar-open');
          overlay.classList.remove('overlay-visible');
        });
      }
    }
  }

  // ── Logout ──────────────────────────────────────────────
  function initLogout() {
    document.querySelectorAll('.logout-btn').forEach(btn => {
      btn.addEventListener('click', async (e) => {
        e.preventDefault();
        try {
          await auth.signOut();
          showToast('Logged out successfully', 'success');
          setTimeout(() => window.location.href = 'home.html', 500);
        } catch (err) {
          showToast('Logout failed: ' + err.message, 'error');
        }
      });
    });
  }

  // ── Populate User Name in Welcome ──────────────────────
  function setWelcome(userData) {
    const el = document.getElementById('welcome-name');
    if (el && userData) {
      const prefix = userData.role === 'teacher' ? 'Prof. ' : '';
      el.textContent = prefix + (userData.name || 'User');
    }
  }

  // ── Profile Avatar ────────────────────────────────────
  function setProfileAvatar(userData) {
    const el = document.getElementById('nav-profile-img');
    if (el && userData && userData.photoURL) {
      el.src = userData.photoURL;
    }
  }

  // ── Query Params ──────────────────────────────────────
  function getParam(key) {
    return new URLSearchParams(window.location.search).get(key);
  }

  // ── Escape HTML ───────────────────────────────────────
  function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  // Public API
  return {
    showToast,
    setLoading,
    formatDate,
    formatDateTime,
    timeAgo,
    statusBadge,
    buildElectionCard,
    initSidebar,
    initLogout,
    setWelcome,
    setProfileAvatar,
    getParam,
    escapeHtml
  };
})();
