import { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  AreaChart, Area, BarChart, Bar, XAxis, YAxis,
  CartesianGrid, Tooltip, ResponsiveContainer, Cell
} from 'recharts'
import {
  ClipboardList, AlertTriangle, CheckCircle2, Cpu,
  TrendingUp, MapPin, ExternalLink, RefreshCw
} from 'lucide-react'
import { statsAPI, mapAPI } from '../utils/api'
import { useToast } from '../hooks/useToast'
import { format } from 'date-fns'
import { ru } from 'date-fns/locale'
import clsx from 'clsx'

const VIOLATION_TYPE_LABELS = {
  size_mismatch: 'Несоответствие размера',
  forbidden_content: 'Запрещённый контент',
  illegal_sign: 'Незаконная вывеска',
  no_permit: 'Нет разрешения',
  text_error: 'Ошибка в тексте',
  other: 'Прочее',
}

const STATUS_META = {
  completed: { label: 'Завершена', cls: 'badge-green' },
  processing: { label: 'Обработка', cls: 'badge-blue' },
  pending:    { label: 'Ожидание', cls: 'badge-amber' },
  error:      { label: 'Ошибка', cls: 'badge-red' },
}

const VIOLATION_COLORS = ['#3b82f6','#ef4444','#f59e0b','#22c55e','#8b5cf6','#64748b']

export default function Dashboard() {
  const [stats, setStats]       = useState(null)
  const [mapPoints, setMapPoints] = useState([])
  const [mapKey, setMapKey]     = useState('')
  const [mapReady, setMapReady] = useState(false)
  const [loading, setLoading]   = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const mapRef  = useRef(null)
  const ymapRef = useRef(null)
  const navigate = useNavigate()
  const { toast } = useToast()

  const load = async (silent = false) => {
    if (!silent) setLoading(true); else setRefreshing(true)
    try {
      const [sRes, cfgRes, ptsRes] = await Promise.all([
        statsAPI.dashboard(),
        mapAPI.config().catch(() => ({ data: { api_key: '' } })),
        mapAPI.points().catch(() => ({ data: [] })),
      ])
      setStats(sRes.data)
      setMapPoints(ptsRes.data)
      setMapKey(cfgRes.data.api_key || '')
    } catch {
      if (!silent) toast('Ошибка загрузки статистики', 'error')
    } finally {
      setLoading(false); setRefreshing(false)
    }
  }

  useEffect(() => { load() }, [])

  useEffect(() => {
    if (!mapPoints.length || mapReady) return
    const key = mapKey && mapKey !== 'YOUR_YANDEX_MAPS_KEY' ? mapKey : null
    const initMap = () => {
      if (!window.ymaps || !mapRef.current) return
      window.ymaps.ready(() => {
        if (ymapRef.current) { ymapRef.current.destroy(); ymapRef.current = null }
        const center = mapPoints.length ? [mapPoints[0].lat, mapPoints[0].lon] : [57.1529, 65.5343]
        const myMap = new window.ymaps.Map(mapRef.current, { center, zoom: 12, controls: ['zoomControl'] })
        mapPoints.forEach(p => {
          const pm = new window.ymaps.Placemark([p.lat, p.lon],
            { balloonContentHeader: p.address || 'Без адреса', balloonContentBody: `Нарушений: <b>${p.violations}</b>`, hintContent: p.address },
            { preset: p.violations > 0 ? 'islands#redDotIcon' : 'islands#greenDotIcon' }
          )
          pm.events.add('click', () => navigate(`/results/${p.id}`))
          myMap.geoObjects.add(pm)
        })
        ymapRef.current = myMap
        setMapReady(true)
      })
    }
    if (key && !window.ymaps) {
      const s = document.createElement('script')
      s.src = `https://api-maps.yandex.ru/2.1/?apikey=${key}&lang=ru_RU`
      s.onload = initMap
      document.head.appendChild(s)
    } else if (window.ymaps) { initMap() }
  }, [mapPoints, mapKey])

  if (loading) return <PageSkeleton />

  const violationEntries = Object.entries(stats?.violation_by_type || {})
  const totalByType = violationEntries.reduce((a, [, v]) => a + v, 0)
  const donutData = violationEntries.map(([k, v]) => ({
    name: VIOLATION_TYPE_LABELS[k] || k,
    value: v,
    pct: totalByType ? Math.round(v / totalByType * 100) : 0,
  }))

  return (
    <div className="p-4 sm:p-6 max-w-screen-xl mx-auto">
      {/* Header */}
      <div className="flex items-start justify-between mb-5">
        <div>
          <h1 className="text-lg sm:text-xl font-semibold text-ink-primary">Обзор системы</h1>
          <p className="text-xs sm:text-sm text-ink-tertiary mt-0.5">
            Тюмень · {format(new Date(), 'LLLL yyyy', { locale: ru })}
          </p>
        </div>
        <button onClick={() => load(true)} disabled={refreshing} className="btn-secondary text-xs gap-1.5">
          <RefreshCw size={13} className={refreshing ? 'animate-spin' : ''} />
          <span className="hidden sm:inline">Обновить</span>
        </button>
      </div>

      {/* Stats — 2 cols on mobile, 4 on xl */}
      <div className="grid grid-cols-2 xl:grid-cols-4 gap-3 sm:gap-4 mb-5">
        <StatCard label="Проверок" value={stats?.total_inspections ?? 0}
          icon={<ClipboardList size={18} />} iconBg="bg-brand-50 text-brand-600"
          delta="+23% к прошлому месяцу" deltaUp />
        <StatCard label="Нарушений" value={stats?.total_violations ?? 0}
          icon={<AlertTriangle size={18} />} iconBg="bg-danger-50 text-danger-600"
          delta={`+${stats?.today_violations ?? 0} за сегодня`} deltaUp={false} />
        <StatCard label="Устранено" value={stats?.resolved_violations ?? 0}
          icon={<CheckCircle2 size={18} />} iconBg="bg-success-50 text-success-600"
          delta={`${stats?.resolve_percent ?? 0}% от выявленных`} deltaUp />
        <StatCard label="Точность, %" value={stats?.model_accuracy ?? 0}
          icon={<Cpu size={18} />} iconBg="bg-warn-50 text-warn-600"
          delta="+1.2% за месяц" deltaUp />
      </div>

      {/* Charts — stack on mobile, side-by-side on xl */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-4 mb-5">
        {/* Trend — full width on mobile, 2/3 on xl */}
        <div className="xl:col-span-2 card p-4 sm:p-5">
          <div className="mb-4">
            <div className="text-sm font-semibold text-ink-primary">Динамика нарушений</div>
            <div className="text-xs text-ink-tertiary mt-0.5">По месяцам за 6 периодов</div>
          </div>
          <ResponsiveContainer width="100%" height={160}>
            <AreaChart data={stats?.monthly_trend || []} margin={{ top: 4, right: 4, left: -20, bottom: 0 }}>
              <defs>
                <linearGradient id="ag" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%"  stopColor="#3b82f6" stopOpacity={0.12} />
                  <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
              <XAxis dataKey="month" tick={{ fontSize: 10, fill: '#94a3b8' }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fontSize: 10, fill: '#94a3b8' }} axisLine={false} tickLine={false} />
              <Tooltip contentStyle={{ fontSize: 12, borderRadius: 8, border: '1px solid #e2e8f0' }} />
              <Area type="monotone" dataKey="count" name="Нарушений"
                stroke="#3b82f6" strokeWidth={2} fill="url(#ag)"
                dot={{ r: 3, fill: '#3b82f6', strokeWidth: 0 }}
                activeDot={{ r: 5, fill: '#1d4ed8' }} />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        {/* Breakdown */}
        <div className="card p-4 sm:p-5">
          <div className="text-sm font-semibold text-ink-primary mb-1">Типы нарушений</div>
          <div className="text-xs text-ink-tertiary mb-3">Распределение</div>
          {donutData.length === 0 ? (
            <div className="h-32 flex items-center justify-center text-sm text-ink-disabled">Нет данных</div>
          ) : (
            <>
              <ResponsiveContainer width="100%" height={110}>
                <BarChart data={donutData} layout="vertical" margin={{ left: 0, right: 4 }}>
                  <XAxis type="number" hide />
                  <YAxis type="category" dataKey="name" tick={{ fontSize: 9, fill: '#94a3b8' }} width={95} axisLine={false} tickLine={false} />
                  <Tooltip formatter={(v, n, p) => [v, p.payload.pct + '%']}
                    contentStyle={{ fontSize: 12, borderRadius: 8, border: '1px solid #e2e8f0' }} />
                  <Bar dataKey="value" radius={[0, 4, 4, 0]}>
                    {donutData.map((_, i) => <Cell key={i} fill={VIOLATION_COLORS[i % VIOLATION_COLORS.length]} />)}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
              <div className="mt-2 space-y-1">
                {donutData.slice(0, 4).map((d, i) => (
                  <div key={d.name} className="flex items-center gap-2 text-xs">
                    <span className="w-2 h-2 rounded-sm flex-shrink-0" style={{ background: VIOLATION_COLORS[i] }} />
                    <span className="flex-1 text-ink-secondary truncate">{d.name}</span>
                    <span className="text-ink-tertiary font-mono">{d.pct}%</span>
                  </div>
                ))}
              </div>
            </>
          )}
        </div>
      </div>

      {/* Map */}
      <div className="card mb-5 overflow-hidden">
        <div className="flex flex-wrap items-center justify-between gap-2 px-4 sm:px-5 py-3 sm:py-4 border-b border-surface-3">
          <div>
            <div className="text-sm font-semibold text-ink-primary">Карта нарушений</div>
            <div className="text-xs text-ink-tertiary mt-0.5">Объекты с GPS-метками</div>
          </div>
          <div className="flex items-center gap-3 text-xs text-ink-tertiary flex-wrap">
            <span className="flex items-center gap-1.5"><span className="w-2 h-2 rounded-full bg-danger-500" />Нарушения</span>
            <span className="flex items-center gap-1.5"><span className="w-2 h-2 rounded-full bg-success-500" />В норме</span>
          </div>
        </div>
        {/* Map height adapts: shorter on mobile */}
        <div className="h-48 sm:h-64 lg:h-72 relative bg-surface-1">
          {mapKey && mapKey !== 'YOUR_YANDEX_MAPS_KEY'
            ? <div ref={mapRef} className="w-full h-full" />
            : <FallbackMap points={mapPoints} onPointClick={id => navigate(`/results/${id}`)} />
          }
        </div>
        <div className="px-4 sm:px-5 py-2.5 border-t border-surface-3 flex flex-wrap gap-3 sm:gap-5 text-xs text-ink-tertiary">
          <span>Всего: <strong className="text-ink-secondary">{mapPoints.length}</strong></span>
          <span>Нарушения: <strong className="text-danger-600">{mapPoints.filter(p => p.violations > 0).length}</strong></span>
          <span>В норме: <strong className="text-success-600">{mapPoints.filter(p => p.violations === 0).length}</strong></span>
        </div>
      </div>

      {/* Recent table */}
      <div className="card overflow-hidden">
        <div className="flex items-center justify-between px-4 sm:px-5 py-3 sm:py-4 border-b border-surface-3">
          <div className="text-sm font-semibold text-ink-primary">Последние проверки</div>
          <button onClick={() => navigate('/history')} className="btn-ghost text-xs gap-1">
            Все <ExternalLink size={12} />
          </button>
        </div>
        <RecentTable navigate={navigate} />
      </div>
    </div>
  )
}

/* ── Sub-components ── */

function StatCard({ label, value, icon, iconBg, delta, deltaUp }) {
  return (
    <div className="card p-4 sm:p-5">
      <div className={clsx('w-8 h-8 sm:w-9 sm:h-9 rounded-lg flex items-center justify-center mb-3 sm:mb-4', iconBg)}>
        {icon}
      </div>
      <div className="text-xl sm:text-2xl font-bold text-ink-primary font-mono mb-0.5">{value}</div>
      <div className="text-[10px] sm:text-xs text-ink-tertiary uppercase tracking-wide mb-1.5">{label}</div>
      <div className={clsx('text-[10px] sm:text-xs flex items-center gap-1', deltaUp ? 'stat-delta-up' : 'text-ink-tertiary')}>
        {deltaUp && <TrendingUp size={10} />}
        <span className="truncate">{delta}</span>
      </div>
    </div>
  )
}

function FallbackMap({ points, onPointClick }) {
  const w = 800, h = 288
  const lats = points.map(p => p.lat).filter(Boolean)
  const lons = points.map(p => p.lon).filter(Boolean)
  const minLat = Math.min(...lats, 57.1), maxLat = Math.max(...lats, 57.2)
  const minLon = Math.min(...lons, 65.5), maxLon = Math.max(...lons, 65.6)
  const project = (lat, lon) => ({
    x: ((lon - minLon) / (maxLon - minLon + 0.001)) * (w - 60) + 30,
    y: (1 - (lat - minLat) / (maxLat - minLat + 0.001)) * (h - 60) + 30,
  })
  return (
    <div className="relative w-full h-full bg-slate-50 overflow-hidden">
      <svg className="absolute inset-0 w-full h-full opacity-20" viewBox={`0 0 ${w} ${h}`} preserveAspectRatio="none">
        {[...Array(8)].map((_, i) => <line key={`h${i}`} x1="0" y1={i*h/7} x2={w} y2={i*h/7} stroke="#94a3b8" strokeWidth="0.5" />)}
        {[...Array(12)].map((_, i) => <line key={`v${i}`} x1={i*w/11} y1="0" x2={i*w/11} y2={h} stroke="#94a3b8" strokeWidth="0.5" />)}
      </svg>
      <svg className="absolute inset-0 w-full h-full" viewBox={`0 0 ${w} ${h}`}>
        {points.map(p => {
          if (!p.lat || !p.lon) return null
          const { x, y } = project(p.lat, p.lon)
          const c = p.violations > 0 ? '#ef4444' : '#22c55e'
          return (
            <g key={p.id} onClick={() => onPointClick(p.id)} className="cursor-pointer">
              <circle cx={x} cy={y} r={8} fill={c} opacity={0.15} />
              <circle cx={x} cy={y} r={4} fill={c} />
              <title>{p.address} · {p.violations} нарушений</title>
            </g>
          )
        })}
      </svg>
      {points.length === 0 && (
        <div className="absolute inset-0 flex flex-col items-center justify-center gap-2">
          <MapPin size={22} className="text-ink-disabled" />
          <span className="text-xs sm:text-sm text-ink-disabled text-center px-4">Нет объектов с GPS-координатами</span>
        </div>
      )}
      {points.length > 0 && (
        <div className="absolute bottom-2 left-2 text-[10px] text-ink-tertiary bg-white/80 px-2 py-1 rounded">
          Добавьте YANDEX_MAPS_KEY для полной карты
        </div>
      )}
    </div>
  )
}

function RecentTable({ navigate }) {
  const [items, setItems] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    import('../utils/api').then(({ inspectionsAPI }) => {
      inspectionsAPI.list({ limit: 8 })
        .then(r => setItems(r.data))
        .catch(() => {})
        .finally(() => setLoading(false))
    })
  }, [])

  if (loading) return (
    <div className="p-6 flex justify-center">
      <div className="w-5 h-5 border-2 border-brand-600 border-t-transparent rounded-full animate-spin" />
    </div>
  )
  if (!items.length) return (
    <div className="p-6 text-center text-sm text-ink-disabled">
      Нет проверок.{' '}
      <button className="text-brand-600 hover:underline" onClick={() => navigate('/upload')}>
        Загрузить фото →
      </button>
    </div>
  )

  return (
    /* Horizontal scroll on small screens */
    <div className="overflow-x-auto">
      <table className="w-full text-sm min-w-[480px]">
        <thead>
          <tr className="border-b border-surface-3">
            {['Адрес / файл', 'Нарушения', 'Статус', 'Дата', ''].map(h => (
              <th key={h} className="px-4 sm:px-5 py-3 text-left text-[11px] text-ink-tertiary uppercase tracking-wide font-medium whitespace-nowrap">{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {items.map(item => {
            const sm = STATUS_META[item.status] || { label: item.status, cls: 'badge-gray' }
            return (
              <tr key={item.id} onClick={() => navigate(`/results/${item.id}`)}
                className="border-b border-surface-3/50 hover:bg-surface-1 cursor-pointer transition-colors">
                <td className="px-4 sm:px-5 py-3.5">
                  <div className="font-medium text-ink-primary max-w-[180px] sm:max-w-none truncate">
                    {item.address || item.original_filename || 'Без адреса'}
                  </div>
                  <div className="text-[11px] text-ink-tertiary font-mono mt-0.5">{item.id?.slice(0,8).toUpperCase()}</div>
                </td>
                <td className="px-4 sm:px-5 py-3.5">
                  {item.total_violations > 0
                    ? <span className="text-danger-600 font-medium">{item.total_violations}</span>
                    : <span className="text-ink-disabled">—</span>}
                </td>
                <td className="px-4 sm:px-5 py-3.5"><span className={sm.cls}>{sm.label}</span></td>
                <td className="px-4 sm:px-5 py-3.5 text-ink-tertiary text-xs font-mono whitespace-nowrap">
                  {item.created_at ? format(new Date(item.created_at), 'dd.MM.yy HH:mm') : '—'}
                </td>
                <td className="px-4 sm:px-5 py-3.5"><ExternalLink size={13} className="text-ink-disabled" /></td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}

function PageSkeleton() {
  return (
    <div className="p-4 sm:p-6 max-w-screen-xl mx-auto">
      <div className="h-6 w-40 bg-surface-2 rounded mb-2 animate-pulse" />
      <div className="h-4 w-52 bg-surface-2 rounded mb-5 animate-pulse" />
      <div className="grid grid-cols-2 xl:grid-cols-4 gap-3 mb-5">
        {[...Array(4)].map((_, i) => <div key={i} className="card h-28 animate-pulse bg-surface-1" />)}
      </div>
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-4 mb-5">
        <div className="xl:col-span-2 card h-52 animate-pulse bg-surface-1" />
        <div className="card h-52 animate-pulse bg-surface-1" />
      </div>
    </div>
  )
}
