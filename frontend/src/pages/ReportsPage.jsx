import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { FileText, FileJson, Download, ArrowRight, Clock } from 'lucide-react'
import { inspectionsAPI, reportsAPI } from '../utils/api'
import { useToast } from '../hooks/useToast'
import { format } from 'date-fns'

export default function ReportsPage() {
  const { toast } = useToast()
  const navigate = useNavigate()
  const [inspections, setInspections] = useState([])
  const [loading, setLoading] = useState(true)
  const [selected, setSelected] = useState(null)
  const [generating, setGenerating] = useState(null)

  useEffect(() => {
    inspectionsAPI.list({ limit: 30, status: 'completed' })
      .then(r => {
        const completed = r.data.filter(i => i.status === 'completed')
        setInspections(completed)
        if (completed.length) setSelected(completed[0].id)
      })
      .finally(() => setLoading(false))
  }, [])

  const download = (type) => {
    if (!selected) { toast('Выберите проверку', 'warning'); return }
    setGenerating(type)
    const url = type === 'pdf' ? reportsAPI.pdfUrl(selected) : reportsAPI.jsonUrl(selected)
    const a = document.createElement('a')
    a.href = url
    a.click()
    setTimeout(() => {
      setGenerating(null)
      toast(`${type.toUpperCase()}-отчёт сформирован`, 'success')
    }, 1500)
  }

  const selectedItem = inspections.find(i => i.id === selected)

  return (
    <div className="p-6 max-w-screen-xl mx-auto">
      <div className="mb-6">
        <h1 className="text-xl font-semibold text-ink-primary">Генерация отчётов</h1>
        <p className="text-sm text-ink-tertiary mt-0.5">Экспорт результатов анализа в PDF или JSON</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        {/* Inspection selector */}
        <div className="xl:col-span-2">
          <div className="card overflow-hidden">
            <div className="px-5 py-4 border-b border-surface-3">
              <div className="text-sm font-medium text-ink-primary">Выберите проверку</div>
              <div className="text-xs text-ink-tertiary mt-0.5">Только завершённые проверки</div>
            </div>
            {loading ? (
              <div className="p-4 space-y-2">
                {[...Array(4)].map((_, i) => <div key={i} className="h-14 bg-surface-1 rounded animate-pulse" />)}
              </div>
            ) : inspections.length === 0 ? (
              <div className="p-8 text-center">
                <div className="text-sm text-ink-disabled mb-3">Нет завершённых проверок</div>
                <button onClick={() => navigate('/upload')} className="btn-primary text-xs">
                  Загрузить фото
                </button>
              </div>
            ) : (
              <div className="divide-y divide-surface-3 max-h-[480px] overflow-y-auto">
                {inspections.map(item => (
                  <button
                    key={item.id}
                    onClick={() => setSelected(item.id)}
                    className={`w-full text-left px-5 py-3.5 flex items-start gap-3 hover:bg-surface-1 transition-colors ${selected === item.id ? 'bg-brand-50 border-l-2 border-brand-600' : ''}`}
                  >
                    <div className="flex-1 min-w-0">
                      <div className="text-sm font-medium text-ink-primary truncate">
                        {item.address || item.original_filename || 'Без адреса'}
                      </div>
                      <div className="flex items-center gap-3 mt-0.5">
                        <span className="text-[11px] text-ink-tertiary font-mono">{item.id?.slice(0, 8).toUpperCase()}</span>
                        <span className="text-[11px] text-ink-tertiary flex items-center gap-1">
                          <Clock size={10} />
                          {item.created_at ? format(new Date(item.created_at), 'dd.MM.yyyy HH:mm') : '—'}
                        </span>
                        {item.total_violations > 0 && (
                          <span className="text-[11px] text-danger-600">{item.total_violations} нарушений</span>
                        )}
                      </div>
                    </div>
                    {selected === item.id && <ArrowRight size={14} className="text-brand-600 mt-0.5 flex-shrink-0" />}
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Report options */}
        <div className="space-y-4">
          {/* Selected preview */}
          {selectedItem && (
            <div className="card p-4">
              <div className="text-xs text-ink-tertiary uppercase tracking-wide mb-2">Выбрана проверка</div>
              <div className="text-sm font-medium text-ink-primary truncate mb-1">
                {selectedItem.address || selectedItem.original_filename || 'Без адреса'}
              </div>
              <div className="text-xs text-ink-tertiary font-mono">{selectedItem.id?.slice(0, 12).toUpperCase()}</div>
              <div className="mt-2 flex gap-3 text-xs text-ink-tertiary">
                <span>Объектов: {selectedItem.total_detections ?? '—'}</span>
                <span>Нарушений: <strong className={selectedItem.total_violations > 0 ? 'text-danger-600' : ''}>{selectedItem.total_violations ?? 0}</strong></span>
              </div>
            </div>
          )}

          {/* Download buttons */}
          <div className="card p-4 space-y-3">
            <div className="text-sm font-medium text-ink-primary mb-2">Формат отчёта</div>

            <button
              onClick={() => download('pdf')}
              disabled={!selected || generating === 'pdf'}
              className="w-full flex items-center gap-3 px-4 py-3 rounded-btn border border-surface-3 hover:bg-surface-1 hover:border-brand-300 transition-all text-left disabled:opacity-50"
            >
              <div className="w-9 h-9 bg-danger-50 rounded-lg flex items-center justify-center flex-shrink-0">
                {generating === 'pdf'
                  ? <div className="w-4 h-4 border-2 border-danger-600 border-t-transparent rounded-full animate-spin" />
                  : <FileText size={18} className="text-danger-600" />
                }
              </div>
              <div>
                <div className="text-sm font-medium text-ink-primary">PDF-отчёт</div>
                <div className="text-xs text-ink-tertiary">Для печати и официальной отчётности</div>
              </div>
              <Download size={14} className="ml-auto text-ink-disabled" />
            </button>

            <button
              onClick={() => download('json')}
              disabled={!selected || generating === 'json'}
              className="w-full flex items-center gap-3 px-4 py-3 rounded-btn border border-surface-3 hover:bg-surface-1 hover:border-brand-300 transition-all text-left disabled:opacity-50"
            >
              <div className="w-9 h-9 bg-warn-50 rounded-lg flex items-center justify-center flex-shrink-0">
                {generating === 'json'
                  ? <div className="w-4 h-4 border-2 border-warn-600 border-t-transparent rounded-full animate-spin" />
                  : <FileJson size={18} className="text-warn-600" />
                }
              </div>
              <div>
                <div className="text-sm font-medium text-ink-primary">JSON</div>
                <div className="text-xs text-ink-tertiary">Для интеграций и аналитики</div>
              </div>
              <Download size={14} className="ml-auto text-ink-disabled" />
            </button>
          </div>

          <div className="text-xs text-ink-tertiary text-center">
            Отчёт включает EXIF-метаданные, аннотированное изображение, список нарушений и цепочку логического вывода
          </div>
        </div>
      </div>
    </div>
  )
}
