import React from 'react';
import type { UserInfo } from '../api/client';
import useDarkMode from '../hooks/useDarkMode';

interface HeaderProps {
  activeTab?: 'overview' | 'reports';
  onTabChange?: (tab: 'overview' | 'reports') => void;
  userInfo?: UserInfo;
}

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8100';

const Header: React.FC<HeaderProps> = ({ activeTab = 'overview', onTabChange, userInfo }) => {
  const { isDark, mode, toggle } = useDarkMode();

  const themeLabel = mode === 'system' ? 'Auto' : mode === 'dark' ? 'Dark' : 'Light';

  const handleLogin = () => {
    window.location.href = `${API_URL}/saml/login?redirect_to=${encodeURIComponent(window.location.href)}`;
  };

  const handleLogout = () => {
    window.location.href = `${API_URL}/saml/logout?redirect_to=${encodeURIComponent(window.location.origin)}`;
  };

  return (
    <header className="header">
      <div className="header-content">
        <div className="header-brand">
          <img src="/REIT_logo.png" alt="REIT Logo" className="header-logo" />
          <h1 className="header-title">Slurm Usage History Dashboard</h1>
        </div>
        <nav className="header-nav">
          <button
            type="button"
            className={`nav-tab ${activeTab === 'overview' ? 'active' : ''}`}
            onClick={() => {
              onTabChange?.('overview');
              if (activeTab === 'overview') window.scrollTo({ top: 0, behavior: 'smooth' });
            }}
          >
            Dashboard
          </button>
          <button
            type="button"
            className={`nav-tab ${activeTab === 'reports' ? 'active' : ''}`}
            onClick={() => onTabChange?.('reports')}
          >
            Reports
          </button>
          <button type="button" onClick={toggle} className="theme-toggle" title={`Theme: ${themeLabel} (click to cycle)`}>
            <span className="theme-toggle-icon">{isDark ? '\u263E' : '\u2600'}</span>
            <span>{themeLabel}</span>
          </button>
          {!userInfo && (
            <button type="button" className="nav-login" onClick={handleLogin}>
              Login
            </button>
          )}
          {userInfo && (
            <>
              <div className="header-user">
                <span className="header-user-label">User</span>
                <span>{userInfo.username || userInfo.email}</span>
              </div>
              {userInfo.is_admin && (
                <a href="/admin/login" className="nav-admin">
                  Admin
                </a>
              )}
              <button type="button" onClick={handleLogout}>
                Logout
              </button>
            </>
          )}
        </nav>
      </div>
    </header>
  );
};

export default Header;
