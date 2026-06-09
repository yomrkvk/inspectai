import { useState, useEffect } from 'react'
import { MessageSquare, Plus, MapPin, Clock, Send } from 'lucide-react'
import { commentsAPI } from '../utils/api'
import { useToast } from '../hooks/useToast'
import { useAuth } from '../hooks/useAuth'
import { format } from 'date-fns'
import clsx from 'clsx'

const SEVERITY_OPTIONS = [
  { value: 'low', label: 'Незначительное', cls: 'text-success-600 bg-success-50 border-success-200' },
  { value: 'medium', label: 'Среднее', cls: 'text-warn-600 bg-warn-50 border-warn-200' },
  { value: 'high', label: 'Критическое', cls: 'text-danger-600 bg-danger-50 border-danger-200' },
]

const VIOLATION_OPTIONS = [
  { value: 'size_mismatch', label: 'Несоответствие размера' },
  { value: 'forbidden_content', label: 'Запрещённый контент' },
  { value: 'illegal_sign', label: 'Незаконная вывеска' },
  { value: 'no_permit', label: 'Отсутствие разрешения' },
  { value: 'text_error', label: 'Ошибка в тексте' },
  { value: 'other', label: 'Прочее' },
]

const STATUS_META = {
  pending: { label: 'Ожидает', cls: 'badge-amber' },
  review: { label: 'На рассмотрении', cls: 'badge-blue' },
  resolved: { label: 'Решено', cls: 'badge-green' },
}

const ROLE_COLORS = {
  admin: 'bg-brand-100 text-brand-700',
  inspector: 'bg-success-100 text-success-700',
  analyst: 'bg-warn-100 text-warn-700',
  resident: 'bg-surface-2 text-ink-secondary',
}

export default function CommentsPage() {
  const { user } = useAuth()
  const { toast } = useToast()
  const [comments, setComments] = useState([])
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [form, setForm] = useState({
    text: '', address: '', severity: 'medium',
    violation_type: 'other', lat: '', lon: '', tags: '',
  })

  const load = () => {
    commentsAPI.list({ limit: 30 })
      .then(r => setComments(r.data))
      .finally(() => setLoading(false))
  }

  useEffect(load, [])

  const submit = async (e) => {
    e.preventDefault()
    if (!form.text.trim()) return
    setSubmitting(true)
    try {
      await commentsAPI.create({
        text: form.text,
        address: form.address || undefined,
        lat: form.lat ? parseFloat(form.lat) : undefined,
        lon: form.lon ? parseFloat(form.lon) : undefined,
        severity: form.severity,
        violation_type: form.violation_type,
        tags: form.tags ? form.tags.split(',').map(t => t.trim()).filter(Boolean) : [],
      })
      toast('Заявка отправлена', 'success')
      setForm({ text: '', address: '', severity: 'medium', violation_type: 'other', lat: '', lon: '', tags: '' })
      setShowForm(false)
      load()
    } catch {
      toast('Ошибка отправки', 'error')
    } finally {
      setSubmitting(false)
    }
  }

  const initials = (author) => {
    if (!author) return '?'
    const n = author.full_name || author.username || ''
    return n.split(' ').map(w => w[0]).slice(0, 2).join('').toUpperCase() || '?'
  }

  return (
    <div className="p-6 max-w-screen-xl mx-auto">
      <div className="flex items-start justify-between mb-6">
        <div>
          <h1 className="text-xl font-semibold text-ink-primary">Заявки</h1>
          <p className="text-sm text-ink-tertiary mt-0.5">Обращения от жителей и инспекторов</p>
        </div>
        <button onClick={() => setShowForm(p => !p)} className="btn-primary text-xs gap-1.5">
          <Plus size={13} /> Новая заявка
        </button>
      </div>

      {/* Form */}
      {showForm && (
        <div className="card p-5 mb-5 animate-slide-up">
          <div className="text-sm font-medium text-ink-primary mb-4">Подать заявку</div>
          <form onSubmit={submit} className="space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div className="col-span-2">
                <label className="label">Описание нарушения</label>
                <textarea
                  className="input resize-none h-24"
                  placeholder="Опишите нарушение подробно…"
                  value={form.text}
                  onChange={e => setForm(p => ({ ...p, text: e.target.value }))}
                  required
                />
              </div>
              <div>
                <label className="label">Адрес</label>
                <input className="input" placeholder="ул. Ленина, 28" value={form.address}
                  onChange={e => setForm(p => ({ ...p, address: e.target.value }))} />
              </div>
              <div>
                <label className="label">Тип нарушения</label>
                <select className="input" value={form.violation_type}
                  onChange={e => setForm(p => ({ ...p, violation_type: e.target.value }))}>
                  {VIOLATION_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
                </select>
              </div>
              <div>
                <label className="label">Широта</label>
                <input className="input font-mono" placeholder="57.152900" value={form.lat}
                  onChange={e => setForm(p => ({ ...p, lat: e.target.value }))} />
              </div>
              <div>
                <label className="label">Долгота</label>
                <input className="input font-mono" placeholder="65.534300" value={form.lon}
                  onChange={e => setForm(p => ({ ...p, lon: e.target.value }))} />
              </div>
              <div>
                <label className="label">Теги (через запятую)</label>
                <input className="input" placeholder="Незаконно, Баннер" value={form.tags}
                  onChange={e => setForm(p => ({ ...p, tags: e.target.value }))} />
              </div>
            </div>

            {/* Severity */}
            <div>
              <label className="label">Степень серьёзности</label>
              <div className="flex gap-2">
                {SEVERITY_OPTIONS.map(s => (
                  <button
                    key={s.value}
                    type="button"
                    onClick={() => setForm(p => ({ ...p, severity: s.value }))}
                    className={clsx(
                      'flex-1 py-2 text-xs font-medium rounded-btn border transition-all',
                      form.severity === s.value ? s.cls : 'bg-white text-ink-tertiary border-surface-3 hover:bg-surface-1'
                    )}
                  >{s.label}</button>
                ))}
              </div>
            </div>

            <div className="flex gap-2 pt-1">
              <button type="button" onClick={() => setShowForm(false)} className="btn-secondary flex-1 justify-center">Отмена</button>
              <button type="submit" disabled={submitting} className="btn-primary flex-1 justify-center gap-1.5">
                {submitting
                  ? <div className="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                  : <Send size={13} />
                }
                Отправить
              </button>
            </div>
          </form>
        </div>
      )}

      {/* List */}
      {loading ? (
        <div className="space-y-3">
          {[...Array(4)].map((_, i) => <div key={i} className="card h-28 animate-pulse bg-surface-1" />)}
        </div>
      ) : comments.length === 0 ? (
        <div className="card p-12 text-center">
          <MessageSquare size={28} className="text-ink-disabled mx-auto mb-2" />
          <div className="text-sm text-ink-disabled">Заявок пока нет</div>
        </div>
      ) : (
        <div className="space-y-3">
          {comments.map(c => {
            const sm = STATUS_META[c.status] || { label: c.status, cls: 'badge-gray' }
            const roleColor = ROLE_COLORS[c.author?.role] || ROLE_COLORS.resident
            const ROLE_LABELS = { admin: 'Администратор', inspector: 'Инспектор', analyst: 'Аналитик', resident: 'Житель' }
            return (
              <div key={c.id} className="card p-4">
                <div className="flex items-start gap-3">
                  <div className={clsx('w-9 h-9 rounded-full flex items-center justify-center text-xs font-semibold flex-shrink-0', roleColor)}>
                    {initials(c.author)}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap mb-1">
                      <span className="text-sm font-medium text-ink-primary">{c.author?.full_name || c.author?.username}</span>
                      <span className="text-xs text-ink-tertiary bg-surface-1 border border-surface-3 rounded px-1.5 py-0.5">
                        {ROLE_LABELS[c.author?.role] || c.author?.role}
                      </span>
                      <span className={sm.cls}>{sm.label}</span>
                      <span className="ml-auto flex items-center gap-1 text-xs text-ink-disabled">
                        <Clock size={11} />
                        {c.created_at ? format(new Date(c.created_at), 'dd.MM.yyyy HH:mm') : '—'}
                      </span>
                    </div>
                    <p className="text-sm text-ink-secondary leading-relaxed mb-2">{c.text}</p>
                    <div className="flex items-center gap-3 flex-wrap">
                      {c.address && (
                        <span className="flex items-center gap-1 text-xs text-ink-tertiary">
                          <MapPin size={11} />{c.address}
                        </span>
                      )}
                      {c.tags?.map(t => (
                        <span key={t} className="badge badge-gray text-[10px]">{t}</span>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
