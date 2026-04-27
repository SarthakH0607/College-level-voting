// ============================================================
// SmartVote — Auth Guard & Role-Based Routing
// Include AFTER firebase-config.js and config.js on every protected page
// ============================================================

const AuthGuard = (() => {

  // Cache user data to avoid repeated Firestore reads
  let _cachedUser = null;

  /**
   * Protect the current page.
   * @param {Function} onReady — called with (firebaseUser, firestoreUserData) when auth + role check passes
   */
  function protect(onReady) {
    let currentPage = window.location.pathname.split('/').pop() || 'index.html';
    // Normalize: ensure page name always has .html for roleAccess lookup
    if (currentPage && !currentPage.includes('.')) currentPage = currentPage + '.html';

    auth.onAuthStateChanged(async (user) => {
      if (!user) {
        // Not logged in → redirect to login
        window.location.href = 'home.html';
        return;
      }

      try {
        // Fetch user role from Firestore
        const userDoc = await db.collection('users').doc(user.uid).get();

        if (!userDoc.exists) {
          Utils.showToast('User profile not found. Please register again.', 'error');
          await auth.signOut();
          window.location.href = 'register.html';
          return;
        }

        const userData = { id: userDoc.id, ...userDoc.data() };
        _cachedUser = userData;

        // Check role access (handle URLs with or without .html extension)
        const currentPageHtml = currentPage.endsWith('.html') ? currentPage : currentPage + '.html';
        const allowedRoles = APP_CONFIG.roleAccess[currentPage] || APP_CONFIG.roleAccess[currentPageHtml];
        if (allowedRoles && !allowedRoles.includes(userData.role)) {
          // Wrong role → redirect to correct dashboard
          Utils.showToast('Access denied. Redirecting to your dashboard.', 'warning');
          const dashboard = APP_CONFIG.roleDashboard[userData.role] || 'login.html';
          setTimeout(() => { window.location.href = dashboard; }, 800);
          return;
        }

        // Apply role-based theme
        document.documentElement.setAttribute('data-role', userData.role);

        // Update UI elements
        Utils.setWelcome(userData);
        Utils.setProfileAvatar(userData);
        Utils.initSidebar();
        Utils.initLogout();

        // Ready callback
        if (typeof onReady === 'function') {
          onReady(user, userData);
        }

      } catch (err) {
        console.error('Auth guard error:', err);
        Utils.showToast('Authentication error. Please log in again.', 'error');
        await auth.signOut();
        window.location.href = 'home.html';
      }
    });
  }

  /**
   * Get cached user data (available after protect() resolves)
   */
  function getUser() {
    return _cachedUser;
  }

  return { protect, getUser };
})();
