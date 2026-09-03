import type { ReactNode } from 'react';
import { useLocation } from 'react-router-dom';
import useDarkMode from '../hooks/useDarkMode';
import '../pages/admin.css';

interface AdminLayoutProps {
  title: string;
  subtitle?: string;
  breadcrumb?: ReactNode;
  actions?: ReactNode;
  tabs?: ReactNode;
  children: ReactNode;
}

const NAV_LINKS = [
  { href: '/', label: 'Dashboard' },
  { href: '/admin/clusters', label: 'Clusters' },
  { href: '/admin/users', label: 'Users' },
];

/** Header, navigation, and main column shared by every admin page. */
export function AdminLayout({ title, subtitle, breadcrumb, actions, tabs, children }: AdminLayoutProps) {
  const { isDark, mode, toggle } = useDarkMode();
  const { pathname } = useLocation();
  const themeLabel = mode === 'system' ? 'Auto' : mode === 'dark' ? 'Dark' : 'Light';

  const logout = () => {
    localStorage.removeItem('admin_token');
    localStorage.removeItem('admin_token_expires');
    window.location.href = '/saml/logout?redirect_to=/admin/login';
  };

  return (
    <div className="cp-page">
      <header className="cp-header">
        <div className="cp-header-inner">
          <div>
            {breadcrumb && <div className="cp-breadcrumb">{breadcrumb}</div>}
            <h1>{title}</h1>
            {subtitle && <p className="cp-muted">{subtitle}</p>}
          </div>
          <nav className="cp-nav">
            {NAV_LINKS.map(({ href, label }) => (
              <a key={href} href={href} className={pathname === href ? 'active' : undefined}>
                {label}
              </a>
            ))}
            {actions}
            <button type="button" onClick={toggle} className="theme-toggle" title={`Theme: ${themeLabel} (click to cycle)`}>
              <span className="theme-toggle-icon">{isDark ? '☾' : '☀'}</span>
              <span>{themeLabel}</span>
            </button>
            <button type="button" className="cp-btn cp-btn-small cp-btn-quiet" onClick={logout}>
              Logout
            </button>
          </nav>
        </div>
        {tabs && <div className="cp-tabs">{tabs}</div>}
      </header>
      <main className="cp-main">{children}</main>
    </div>
  );
}
