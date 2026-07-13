/**
 * Shared utilities for the Resume ATS UI.
 * L8 Fix: Consolidated from copy-pasted code across 10+ files.
 */

// ─────────────────────────────────────────────────────────────────────────────
// S4 Fix: HTML escaping to prevent XSS via candidate data
// ─────────────────────────────────────────────────────────────────────────────
function escapeHtml(text) {
    if (text === null || text === undefined) return '';
    const div = document.createElement('div');
    div.textContent = String(text);
    return div.innerHTML;
}

// ─────────────────────────────────────────────────────────────────────────────
// Toast notification system
// ─────────────────────────────────────────────────────────────────────────────
function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container') || createToastContainer();
    const toast = document.createElement('div');
    toast.className = `toast ${type} toast-${type}`;
    toast.textContent = message;
    container.appendChild(toast);
    setTimeout(() => toast.remove(), 5000);
}

function createToastContainer() {
    const container = document.createElement('div');
    container.id = 'toast-container';
    container.className = 'toast-container';
    document.body.appendChild(container);
    return container;
}

// ─────────────────────────────────────────────────────────────────────────────
// Auth utilities
// ─────────────────────────────────────────────────────────────────────────────
async function logout(redirectTo = '/ui/auth/login.html') {
    try {
        await fetch('/api/v1/auth/logout', {
            method: 'POST',
            credentials: 'include',
        });
    } catch (error) {
        console.error('Logout request failed:', error);
    } finally {
        window.location.href = redirectTo;
    }
}

async function fetchWithAuth(url, options = {}) {
    const headers = { ...options.headers };

    let response = await fetch(url, {
        ...options,
        headers,
        credentials: 'include',
    });

    if (response.status === 401) {
        const refreshResponse = await fetch('/api/v1/auth/refresh', {
            method: 'POST',
            credentials: 'include',
        });

        if (refreshResponse.ok) {
            response = await fetch(url, {
                ...options,
                headers,
                credentials: 'include',
            });
        } else {
            await logout();
            return response;
        }
    }

    if (response.status === 403) {
        showToast('Access denied. Redirecting to login...', 'error');
        setTimeout(() => logout(), 1500);
    }

    return response;
}

// ─────────────────────────────────────────────────────────────────────────────
// Auth guard for protected pages
// ─────────────────────────────────────────────────────────────────────────────
async function requireAuth(allowedRoles = null) {
    try {
        const response = await fetchWithAuth('/api/v1/auth/me');
        if (!response.ok) {
            await logout();
            return null;
        }
        const user = await response.json();

        if (allowedRoles && !allowedRoles.includes(user.role)) {
            showToast('Access denied', 'error');
            await logout();
            return null;
        }
        return user;
    } catch (error) {
        console.error('Auth check failed:', error);
        await logout();
        return null;
    }
}

// ─────────────────────────────────────────────────────────────────────────────
// Time formatting
// ─────────────────────────────────────────────────────────────────────────────
function timeAgo(dateString) {
    if (!dateString) return 'N/A';
    const date = new Date(dateString);
    const seconds = Math.floor((Date.now() - date.getTime()) / 1000);

    const intervals = {
        year: 31536000,
        month: 2592000,
        week: 604800,
        day: 86400,
        hour: 3600,
        minute: 60,
    };

    for (const [unit, secondsInUnit] of Object.entries(intervals)) {
        const interval = Math.floor(seconds / secondsInUnit);
        if (interval >= 1) {
            return `${interval} ${unit}${interval > 1 ? 's' : ''} ago`;
        }
    }
    return 'Just now';
}

// ─────────────────────────────────────────────────────────────────────────────
// Score styling
// ─────────────────────────────────────────────────────────────────────────────
function scoreClass(score) {
    if (score >= 90) return 'score-excellent';
    if (score >= 75) return 'score-good';
    if (score >= 60) return 'score-average';
    return 'score-poor';
}

function scoreBadge(score) {
    return `<span class="badge ${scoreClass(score)}">${score ? score.toFixed(1) : 'N/A'}</span>`;
}

// ─────────────────────────────────────────────────────────────────────────────
// Status badge styling
// ─────────────────────────────────────────────────────────────────────────────
function statusBadge(status) {
    const statusClasses = {
        'applied': 'badge-info',
        'shortlisted': 'badge-success',
        'interviewing': 'badge-warning',
        'offered': 'badge-success',
        'rejected': 'badge-danger',
        'hired': 'badge-success',
        'active': 'badge-success',
        'draft': 'badge-secondary',
        'paused': 'badge-warning',
        'closed': 'badge-danger',
    };
    const cls = statusClasses[status] || 'badge-secondary';
    return `<span class="badge ${cls}">${escapeHtml(status)}</span>`;
}

// ─────────────────────────────────────────────────────────────────────────────
// Recommendation badge
// ─────────────────────────────────────────────────────────────────────────────
function recommendationBadge(rec) {
    if (!rec) return '';
    const recClasses = {
        'Strong Hire': 'badge-success',
        'Hire': 'badge-success',
        'Review': 'badge-warning',
        'Reject': 'badge-danger',
    };
    const cls = recClasses[rec] || 'badge-secondary';
    return `<span class="badge ${cls}">${escapeHtml(rec)}</span>`;
}

// ─────────────────────────────────────────────────────────────────────────────
// Export for modules (if using ES6)
// ─────────────────────────────────────────────────────────────────────────────
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        escapeHtml,
        showToast,
        logout,
        fetchWithAuth,
        requireAuth,
        timeAgo,
        scoreClass,
        scoreBadge,
        statusBadge,
        recommendationBadge,
    };
}
