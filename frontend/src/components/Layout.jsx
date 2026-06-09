import { useState, useEffect } from 'react'
import { NavLink, useNavigate, useLocation } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'
import {
  LayoutDashboard, Upload, Clock, MessageSquare,
  FileText, Settings, Shield, LogOut, ChevronRight,
  Bell, Menu, X, ScanSearch
} from 'lucide-react'
import clsx from 'clsx'

const NAV_SECTIONS = [
  {
    label: 'Основное',
    items: [
      { to: '/', label: 'Дашборд', icon: LayoutDashboard, exact: true },
      { to: '/upload', label: 'Загрузить фото', icon: Upload },
      { to: '/history', label: 'История проверок', icon: Clock },
    ],
  },
  {
    label: 'Взаимодействие',
    items: [
      { to: '/comments', label: 'Заявки', icon: MessageSquare },
      { to: '/reports', label: 'Отчёты', icon: FileText },
    ],
  },
  {
    label: 'Система',
    items: [
      { to: '/settings', label: 'Настройки', icon: Settings, disabled: true },
      { to: '/roles', label: 'Роли', icon: Shield, disabled: true },
    ],
  },
]

const ROLE_LABELS = {
  admin: 'Администратор',
  inspector: 'Инспектор',
  analyst: 'Аналитик',
  resident: 'Житель',
}

const BREADCRUMBS = {
  '/': 'Дашборд',
  '/upload': 'Загрузка',
  '/history': 'История',
  '/comments': 'Заявки',
  '/reports': 'Отчёты',
}

export default function Layout({ children }) {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [sidebarOpen, setSidebarOpen] = useState(false)

  // Close sidebar on route change (mobile)
  useEffect(() => { setSidebarOpen(false) }, [location.pathname])

  // Close on resize to desktop
  useEffect(() => {
    const handler = () => { if (window.innerWidth >= 1024) setSidebarOpen(false) }
    window.addEventListener('resize', handler)
    return () => window.removeEventListener('resize', handler)
  }, [])

  const currentLabel = Object.entries(BREADCRUMBS).find(([path]) =>
    path === '/' ? location.pathname === '/' : location.pathname.startsWith(path)
  )?.[1] ?? 'InspectAI'

  const initials = user?.full_name
    ? user.full_name.split(' ').map(w => w[0]).slice(0, 2).join('')
    : user?.username?.slice(0, 2).toUpperCase() ?? '??'

  return (
    <div className="flex h-screen bg-surface-1 overflow-hidden">

      {/* ── Mobile overlay backdrop ── */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 bg-black/40 z-30 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* ── Sidebar ── */}
      <aside className={clsx(
        'fixed lg:static inset-y-0 left-0 z-40',
        'w-60 flex-shrink-0 bg-white border-r border-surface-3 flex flex-col',
        'transition-transform duration-250 ease-in-out',
        sidebarOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'
      )}>
        {/* Logo */}
        <div className="px-5 py-5 border-b border-surface-3 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 bg-brand-600 rounded-lg flex items-center justify-center flex-shrink-0">
              <ScanSearch size={16} className="text-white" />
            </div>
            <div>
              <div className="font-semibold text-sm text-ink-primary tracking-tight">InspectAI</div>
              <div className="text-[10px] text-ink-disabled uppercase tracking-widest hidden sm:block">Контроль рекламы</div>
            </div>
          </div>
          {/* Close button — mobile only */}
          <button
            className="lg:hidden text-ink-disabled hover:text-ink-tertiary p-1"
            onClick={() => setSidebarOpen(false)}
          >
            <X size={18} />
          </button>
        </div>

        {/* Nav */}
        <nav className="flex-1 px-3 py-4 overflow-y-auto">
          {NAV_SECTIONS.map(section => (
            <div key={section.label} className="mb-5">
              <div className="px-3 mb-1.5 text-[10px] font-semibold text-ink-disabled uppercase tracking-widest">
                {section.label}
              </div>
              {section.items.map(item => (
                <NavItem key={item.to} {...item} />
              ))}
            </div>
          ))}
        </nav>

        {/* User card */}
        <div className="px-3 py-4 border-t border-surface-3">
          <div className="flex items-center gap-2.5 px-3 py-2.5 rounded-btn">
            <div className="w-8 h-8 rounded-full bg-brand-100 text-brand-700 flex items-center justify-center text-xs font-semibold flex-shrink-0">
              {initials}
            </div>
            <div className="flex-1 min-w-0">
              <div className="text-sm font-medium text-ink-primary truncate">{user?.full_name || user?.username}</div>
              <div className="text-xs text-ink-disabled truncate">{ROLE_LABELS[user?.role] ?? user?.role}</div>
            </div>
            <button
              onClick={() => { logout(); navigate('/login') }}
              className="text-ink-disabled hover:text-danger-600 transition-colors flex-shrink-0"
              title="Выйти"
            >
              <LogOut size={14} />
            </button>
          </div>
          <div className="flex items-center gap-1.5 mt-2 px-3">
            <span className="w-1.5 h-1.5 rounded-full bg-success-500 animate-pulse-dot" />
            <span className="text-[10px] text-ink-disabled">Система активна</span>
          </div>
        </div>
      </aside>

      {/* ── Main area ── */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">

        {/* Topbar */}
        <header className="h-14 bg-white border-b border-surface-3 flex items-center px-4 gap-3 flex-shrink-0">
          {/* Burger — mobile only */}
          <button
            className="lg:hidden p-2 -ml-1 text-ink-secondary hover:bg-surface-1 rounded-btn transition-colors"
            onClick={() => setSidebarOpen(true)}
            aria-label="Открыть меню"
          >
            <Menu size={20} />
          </button>

          {/* Breadcrumb */}
          <div className="flex items-center gap-1.5 text-sm text-ink-disabled min-w-0">
            <span className="hidden sm:inline">InspectAI</span>
            <ChevronRight size={13} className="hidden sm:inline flex-shrink-0" />
            <span className="text-ink-secondary font-medium truncate">{currentLabel}</span>
          </div>

          {/* Actions */}
          <div className="ml-auto flex items-center gap-2">
            <button className="relative p-2 text-ink-secondary hover:bg-surface-1 rounded-btn transition-colors">
              <Bell size={16} />
              <span className="absolute top-1.5 right-1.5 w-1.5 h-1.5 bg-danger-500 rounded-full" />
            </button>
            <button
              onClick={() => navigate('/upload')}
              className="btn-primary text-xs px-3 py-1.5 gap-1.5"
            >
              <Upload size={13} />
              <span className="hidden sm:inline">Новая проверка</span>
              <span className="sm:hidden">Фото</span>
            </button>
          </div>
        </header>

        {/* Page content */}
        <main className="flex-1 overflow-y-auto">
          <div className="page-enter">
            {children}
          </div>
        </main>
      </div>
    </div>
  )
}

function NavItem({ to, label, icon: Icon, disabled }) {
  if (disabled) {
    return (
      <div className="flex items-center gap-3 px-3 py-2.5 rounded-btn text-sm text-ink-disabled cursor-not-allowed select-none mb-0.5">
        <Icon size={16} className="flex-shrink-0" />
        <span>{label}</span>
      </div>
    )
  }
  return (
    <NavLink
      to={to}
      end={to === '/'}
      className={({ isActive }) => clsx('nav-item mb-0.5', isActive && 'active')}
    >
      <Icon size={16} className="flex-shrink-0" />
      <span className="flex-1 truncate">{label}</span>
    </NavLink>
  )
}
