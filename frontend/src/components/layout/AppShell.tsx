/**
 * Application chrome.
 *
 * A persistent sidebar on desktop, a slide-over on mobile, and a top bar that
 * carries identity, language and notifications. Navigation is filtered by role
 * so nobody is offered a screen they cannot open.
 */

import { useEffect, useState } from 'react'
import { NavLink, useLocation } from 'react-router-dom'
import {
  BarChart3,
  Bell,
  CalendarDays,
  ClipboardList,
  Gauge,
  HeartHandshake,
  LayoutGrid,
  LogOut,
  Menu,
  ScanSearch,
  Sparkles,
  TrendingUp,
  Users,
  X,
} from 'lucide-react'
import type { ReactNode } from 'react'

import { useAuth } from '../../auth/AuthContext'
import { useI18n } from '../../i18n'
import { relativeTime } from '../../lib/format'
import * as endpoints from '../../lib/endpoints'
import { useAsync } from '../../lib/useAsync'
import type { Role } from '../../lib/types'
import { Avatar, Badge, Button, cx } from '../ui'
import { LanguageSelect } from './LanguageSelect'
import { DemoBar } from './DemoBar'
import { BrandMark } from './BrandMark'
import type { TranslationKey } from '../../i18n/types'

interface NavItem {
  to: string
  labelKey: TranslationKey
  icon: ReactNode
  roles: Role[]
  section: 'work' | 'intelligence' | 'people'
}

const NAV_ITEMS: NavItem[] = [
  { to: '/customer', labelKey: 'nav.customer', icon: <ClipboardList className="size-4" />, roles: ['CUSTOMER'], section: 'work' },
  { to: '/worker', labelKey: 'nav.worker', icon: <ClipboardList className="size-4" />, roles: ['WORKER'], section: 'work' },
  { to: '/dashboard', labelKey: 'nav.dashboard', icon: <Gauge className="size-4" />, roles: ['ADMIN'], section: 'work' },
  { to: '/bookings', labelKey: 'nav.bookings', icon: <CalendarDays className="size-4" />, roles: ['CUSTOMER', 'WORKER', 'ADMIN'], section: 'work' },
  { to: '/services', labelKey: 'nav.services', icon: <LayoutGrid className="size-4" />, roles: ['CUSTOMER', 'WORKER', 'ADMIN'], section: 'work' },
  { to: '/matching', labelKey: 'nav.matching', icon: <ScanSearch className="size-4" />, roles: ['CUSTOMER', 'ADMIN'], section: 'intelligence' },
  { to: '/forecast', labelKey: 'nav.forecast', icon: <TrendingUp className="size-4" />, roles: ['WORKER', 'ADMIN'], section: 'intelligence' },
  { to: '/workforce', labelKey: 'nav.workforce', icon: <Users className="size-4" />, roles: ['WORKER', 'ADMIN'], section: 'intelligence' },
  { to: '/analytics', labelKey: 'nav.analytics', icon: <BarChart3 className="size-4" />, roles: ['ADMIN'], section: 'intelligence' },
  { to: '/welfare', labelKey: 'nav.welfare', icon: <HeartHandshake className="size-4" />, roles: ['WORKER', 'ADMIN'], section: 'people' },
]

const SECTION_KEYS = {
  work: 'nav.sections.work',
  intelligence: 'nav.sections.intelligence',
  people: 'nav.sections.people',
} as const

export function AppShell({ children }: { children: ReactNode }) {
  const { user, signOut } = useAuth()
  const { t } = useI18n()
  const location = useLocation()
  const [menuOpen, setMenuOpen] = useState(false)
  const [notificationsOpen, setNotificationsOpen] = useState(false)

  useEffect(() => {
    setMenuOpen(false)
    setNotificationsOpen(false)
  }, [location.pathname])

  const role = user?.role
  const items = NAV_ITEMS.filter((item) => role && item.roles.includes(role))
  const sections = (['work', 'intelligence', 'people'] as const).filter((section) =>
    items.some((item) => item.section === section),
  )

  return (
    <div className="bg-ink-50 min-h-dvh">
      <DemoBar />

      {/* Sidebar - desktop */}
      <aside className="border-ink-200 fixed inset-y-0 left-0 z-30 hidden w-60 flex-col border-r bg-white lg:flex">
        <div className="border-ink-200 flex h-16 items-center border-b px-5">
          <BrandMark />
        </div>
        <nav className="flex-1 space-y-5 overflow-y-auto px-3 py-5">
          {sections.map((section) => (
            <div key={section}>
              <p className="label px-3 pb-1.5">{t(SECTION_KEYS[section])}</p>
              <ul className="space-y-0.5">
                {items
                  .filter((item) => item.section === section)
                  .map((item) => (
                    <li key={item.to}>
                      <SidebarLink to={item.to} icon={item.icon} label={t(item.labelKey)} />
                    </li>
                  ))}
              </ul>
            </div>
          ))}
        </nav>
        <div className="border-ink-200 border-t p-3">
          <p className="text-ink-400 px-2 pb-2 text-[11px] leading-relaxed">
            {t('brand.principle')}
          </p>
        </div>
      </aside>

      {/* Sidebar - mobile slide-over */}
      {menuOpen ? (
        <div
          className="bg-ink-900/40 fixed inset-0 z-40 lg:hidden"
          onClick={() => setMenuOpen(false)}
          aria-hidden
        />
      ) : null}
      <aside
        className={cx(
          'fixed inset-y-0 left-0 z-50 flex w-64 flex-col bg-white transition-transform duration-200 lg:hidden',
          menuOpen ? 'translate-x-0 shadow-[var(--shadow-overlay)]' : '-translate-x-full',
        )}
        aria-hidden={!menuOpen}
      >
        <div className="border-ink-200 flex h-16 items-center justify-between border-b px-4">
          <BrandMark />
          <button
            type="button"
            onClick={() => setMenuOpen(false)}
            aria-label={t('common.close')}
            className="text-ink-500 hover:bg-ink-100 rounded-lg p-1.5"
          >
            <X className="size-5" aria-hidden />
          </button>
        </div>
        <nav className="flex-1 space-y-5 overflow-y-auto px-3 py-5">
          {sections.map((section) => (
            <div key={section}>
              <p className="label px-3 pb-1.5">{t(SECTION_KEYS[section])}</p>
              <ul className="space-y-0.5">
                {items
                  .filter((item) => item.section === section)
                  .map((item) => (
                    <li key={item.to}>
                      <SidebarLink to={item.to} icon={item.icon} label={t(item.labelKey)} />
                    </li>
                  ))}
              </ul>
            </div>
          ))}
        </nav>
      </aside>

      <div className="lg:pl-60">
        <header className="border-ink-200 sticky top-0 z-20 border-b bg-white/95 backdrop-blur">
          <div className="flex h-16 items-center gap-3 px-4 sm:px-6">
            <button
              type="button"
              onClick={() => setMenuOpen(true)}
              aria-label="Open navigation"
              className="text-ink-600 hover:bg-ink-100 -ml-1 rounded-lg p-2 lg:hidden"
            >
              <Menu className="size-5" aria-hidden />
            </button>

            <div className="min-w-0 flex-1 lg:hidden">
              <BrandMark compact />
            </div>

            <div className="ml-auto flex items-center gap-2">
              <LanguageSelect />

              <NotificationBell
                open={notificationsOpen}
                onToggle={() => setNotificationsOpen((value) => !value)}
              />

              {user ? (
                <div className="flex items-center gap-2 pl-1">
                  <div className="hidden text-right sm:block">
                    <p className="text-ink-900 max-w-[11rem] truncate text-sm font-medium">
                      {user.full_name}
                    </p>
                    <p className="text-ink-400 text-xs">{roleLabel(user.role)}</p>
                  </div>
                  <Avatar name={user.full_name} />
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={signOut}
                    aria-label={t('nav.signOut')}
                    className="px-2"
                  >
                    <LogOut className="size-4" aria-hidden />
                  </Button>
                </div>
              ) : null}
            </div>
          </div>
        </header>

        <main className="mx-auto w-full max-w-7xl px-4 py-6 sm:px-6 sm:py-8">{children}</main>
      </div>
    </div>
  )
}

function SidebarLink({ to, icon, label }: { to: string; icon: ReactNode; label: string }) {
  return (
    <NavLink
      to={to}
      className={({ isActive }) =>
        cx(
          'flex items-center gap-2.5 rounded-lg px-3 py-2 text-sm font-medium transition-colors',
          isActive
            ? 'bg-brand-50 text-brand-800'
            : 'text-ink-600 hover:bg-ink-100 hover:text-ink-900',
        )
      }
    >
      <span className="shrink-0">{icon}</span>
      <span className="truncate">{label}</span>
    </NavLink>
  )
}

function roleLabel(role: Role): string {
  return role === 'ADMIN' ? 'Cooperative admin' : role === 'WORKER' ? 'Worker' : 'Customer'
}

function NotificationBell({ open, onToggle }: { open: boolean; onToggle: () => void }) {
  const { t } = useI18n()
  const { data, reload } = useAsync(() => endpoints.getNotifications(), [])
  const unread = data?.filter((item) => !item.is_read).length ?? 0

  return (
    <div className="relative">
      <button
        type="button"
        onClick={onToggle}
        aria-label={t('nav.notifications')}
        aria-expanded={open}
        className="text-ink-600 hover:bg-ink-100 relative rounded-lg p-2"
      >
        <Bell className="size-5" aria-hidden />
        {unread > 0 ? (
          <span className="bg-danger-500 absolute top-1 right-1 flex size-4 items-center justify-center rounded-full text-[10px] font-semibold text-white">
            {unread > 9 ? '9+' : unread}
          </span>
        ) : null}
      </button>

      {open ? (
        <div className="border-ink-200 absolute right-0 z-30 mt-2 w-80 max-w-[calc(100vw-2rem)] overflow-hidden rounded-xl border bg-white shadow-[var(--shadow-overlay)]">
          <div className="border-ink-200 flex items-center justify-between border-b px-4 py-2.5">
            <p className="text-ink-900 text-sm font-semibold">{t('nav.notifications')}</p>
            {unread > 0 ? <Badge tone="brand">{unread} new</Badge> : null}
          </div>
          <ul className="max-h-80 divide-y divide-ink-100 overflow-y-auto">
            {(data ?? []).slice(0, 12).map((item) => (
              <li key={item.id}>
                <button
                  type="button"
                  onClick={async () => {
                    if (!item.is_read) {
                      await endpoints.markNotificationRead(item.id).catch(() => undefined)
                      void reload()
                    }
                  }}
                  className={cx(
                    'hover:bg-ink-50 w-full px-4 py-3 text-left',
                    !item.is_read && 'bg-brand-50/50',
                  )}
                >
                  <p className="text-ink-900 text-sm font-medium">{item.title}</p>
                  {item.body ? <p className="text-ink-500 mt-0.5 text-xs">{item.body}</p> : null}
                  <p className="text-ink-400 mt-1 text-[11px]">{relativeTime(item.created_at)}</p>
                </button>
              </li>
            ))}
            {!data?.length ? (
              <li className="text-ink-500 px-4 py-6 text-center text-sm">
                {t('common.noResults')}
              </li>
            ) : null}
          </ul>
        </div>
      ) : null}
    </div>
  )
}

export { Sparkles }
