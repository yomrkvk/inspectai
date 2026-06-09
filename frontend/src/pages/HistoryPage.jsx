import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { ExternalLink, Search } from 'lucide-react'
import { inspectionsAPI } from '../utils/api'
import { format } from 'date-fns'
import clsx from 'clsx'

const STATUS_META = {
  completed:  { label: 'Завершена', cls: 'badge-green' },
  processing: { label: 'Обработка', cls: 'badge-blue' },
  pending:    { label: 'Ожидание', cls: 'badge-amber' },
  error:      { label: 'Ошибка', cls: 'badge-red' },
}

const FILTERS = [
  { label: 'Все', value: '' },
  { label: 'Нарушения', value: 'violation' },
  { label: 'Норма', value: 'clean' },
  { label: 'Обработка', value: 'processing' },
]

export default function HistoryPage() {
  const navigate = useNavigate()
  const [items, setItems]   = useState([])
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState('')
  const [search, setSearch] = useState('')

  useEffect(() => {
    inspectionsAPI.list({ limit: 50 })
      .then(r => setItems(r.data))
      .finally(() => setLoading(false))
  }, [])

  const filtered = items.filter(item => {
    const mf = !filter
      || (filter === 'violation' && item.total_violations > 0)
      || (filter === 'clean' && item.total_violations === 0 && item.status === 'completed')
      || (filter === 'processing' && ['processing','pending'].includes(item.status))
    const q = search.toLowerCase()
    const ms = !q
      || (item.address || '').toLowerCase().includes(q)
      || (item.original_filename || '').toLowerCase().includes(q)
    return mf && ms
  })

  return (
    <div className="p-4 sm:p-6 max-w-screen-xl mx-auto">
      <div className="flex flex-col sm:flex-row sm:items-center gap-3 mb-5">
        <div>
          <h1 className="text-lg sm:text-xl font-semibold text-ink-primary">История проверок</h1>
          <p className="text-xs sm:text-sm text-ink-tertiary mt-0.5">Все обработанные изображения</p>
        </div>
        {/* Search — full width on mobile */}
        <div className="sm:ml-auto flex items-center gap-2 border border-surface-3 rounded-btn px-3 py-2 bg-white">
          <Search size={13} className="text-ink-disabled flex-shrink-0" />
          <input className="outline-none bg-transparent text-sm text-ink-primary placeholder-ink-disabled w-full sm:w-44"
            placeholder="Поиск по адресу…"
            value={search} onChange={e => setSearch(e.target.value)} />
        </div>
      </div>

      {/* Filter chips — horizontal scroll on mobile */}
      <div className="flex gap-2 mb-4 overflow-x-auto pb-1 -mx-4 px-4 sm:mx-0 sm:px-0 sm:flex-wrap">
        {FILTERS.map(f => (
          <button key={f.value} onClick={() => setFilter(f.value)}
            className={clsx(
              'px-3 py-1.5 rounded-full text-xs font-medium border transition-all whitespace-nowrap flex-shrink-0',
              filter === f.value
                ? 'bg-brand-600 text-white border-brand-600'
                : 'bg-white text-ink-secondary border-surface-3 hover:border-brand-300'
            )}>{f.label}</button>
        ))}
        <span className="ml-auto text-xs text-ink-tertiary self-center whitespace-nowrap flex-shrink-0 hidden sm:inline">
          {filtered.length} записей
        </span>
      </div>

      {loading ? (
        <div className="space-y-2">
          {[...Array(5)].map((_, i) => <div key={i} className="card h-16 animate-pulse bg-surface-1" />)}
        </div>
      ) : filtered.length === 0 ? (
        <div className="card p-10 text-center">
          <div className="text-ink-disabled text-sm mb-3">Нет записей</div>
          <button onClick={() => navigate('/upload')} className="btn-primary mx-auto">Загрузить фото</button>
        </div>
      ) : (
        <>
          {/* Mobile: card list */}
          <div className="sm:hidden space-y-2">
            {filtered.map(item => {
              const sm = STATUS_META[item.status] || { label: item.status, cls: 'badge-gray' }
              return (
                <div key={item.id} onClick={() => navigate(`/results/${item.id}`)}
                  className="card p-3.5 cursor-pointer hover:shadow-card-hover transition-shadow">
                  <div className="flex items-start justify-between gap-2 mb-2">
                    <div className="font-medium text-ink-primary text-sm truncate flex-1">
                      {item.address || item.original_filename || 'Без адреса'}
                    </div>
                    <span className={sm.cls}>{sm.label}</span>
                  </div>
                  <div className="flex items-center gap-3 text-xs text-ink-tertiary">
                    <span className="font-mono">{item.id?.slice(0,8).toUpperCase()}</span>
                    {item.total_violations > 0 && (
                      <span className="text-danger-600 font-medium">{item.total_violations} нарушений</span>
                    )}
                    <span className="ml-auto font-mono">
                      {item.created_at ? format(new Date(item.created_at), 'dd.MM.yy HH:mm') : '—'}
                    </span>
                  </div>
                </div>
              )
            })}
          </div>

          {/* Desktop: table */}
          <div className="hidden sm:block card overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-surface-3">
                    {['Адрес / файл','Статус','Объектов','Нарушений','Дата',''].map(h => (
                      <th key={h} className="px-5 py-3 text-left text-[11px] text-ink-tertiary uppercase tracking-wide font-medium whitespace-nowrap">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {filtered.map(item => {
                    const sm = STATUS_META[item.status] || { label: item.status, cls: 'badge-gray' }
                    return (
                      <tr key={item.id} onClick={() => navigate(`/results/${item.id}`)}
                        className="border-b border-surface-3/50 hover:bg-surface-1 cursor-pointer transition-colors">
                        <td className="px-5 py-3.5">
                          <div className="font-medium text-ink-primary truncate max-w-[220px]">
                            {item.address || item.original_filename || 'Без адреса'}
                          </div>
                          <div className="text-[11px] text-ink-tertiary font-mono mt-0.5">{item.id?.slice(0,8).toUpperCase()}</div>
                        </td>
                        <td className="px-5 py-3.5"><span className={sm.cls}>{sm.label}</span></td>
                        <td className="px-5 py-3.5 text-ink-secondary">{item.total_detections ?? '—'}</td>
                        <td className="px-5 py-3.5">
                          {item.total_violations > 0
                            ? <span className="text-danger-600 font-medium">{item.total_violations}</span>
                            : <span className="text-ink-disabled">—</span>}
                        </td>
                        <td className="px-5 py-3.5 text-ink-tertiary text-xs font-mono whitespace-nowrap">
                          {item.created_at ? format(new Date(item.created_at), 'dd.MM.yy HH:mm') : '—'}
                        </td>
                        <td className="px-5 py-3.5"><ExternalLink size={13} className="text-ink-disabled" /></td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}
    </div>
  )
}
