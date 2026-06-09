import { useState, useEffect, useRef } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  AlertTriangle, CheckCircle2, Clock, RefreshCw, Download,
  FileJson, FileText, ChevronDown, ChevronUp, Info, Camera, MapPin
} from 'lucide-react'
import { inspectionsAPI, reportsAPI } from '../utils/api'
import { useToast } from '../hooks/useToast'
import { format } from 'date-fns'
import clsx from 'clsx'

const SEVERITY_META = {
  high: { label: 'Критическое', cls: 'badge-red', bar: 'bg-danger-500' },
  medium: { label: 'Среднее', cls: 'badge-amber', bar: 'bg-warn-500' },
  low: { label: 'Незначительное', cls: 'badge-green', bar: 'bg-success-500' },
}

const VIOLATION_LABELS = {
  size_mismatch: 'Несоответствие размера',
  forbidden_content: 'Запрещённый контент',
  illegal_sign: 'Незаконная вывеска',
  no_permit: 'Нет разрешения',
  text_error: 'Ошибка в тексте',
  other: 'Прочее',
}

const STATUS_POLL_MS = 2500

export default function ResultsPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const { toast } = useToast()
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [polling, setPolling] = useState(false)
  const [imgError, setImgError] = useState(false)
  const [showOriginal, setShowOriginal] = useState(false)
  const [exifOpen, setExifOpen] = useState(false)
  const pollRef = useRef(null)

  const load = async () => {
    try {
      const r = await inspectionsAPI.get(id)
      setData(r.data)
      const s = r.data.status
      if (s === 'pending' || s === 'processing') {
        setPolling(true)
        if (!pollRef.current) {
          pollRef.current = setInterval(async () => {
            const sr = await inspectionsAPI.status(id)
            if (sr.data.status === 'completed' || sr.data.status === 'error') {
              clearInterval(pollRef.current); pollRef.current = null
              setPolling(false)
              const full = await inspectionsAPI.get(id)
              setData(full.data)
            }
          }, STATUS_POLL_MS)
        }
      }
    } catch {
      toast('Ошибка загрузки', 'error')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [id])
  useEffect(() => () => { if (pollRef.current) clearInterval(pollRef.current) }, [])

  const downloadPdf = () => {
    window.open(reportsAPI.pdfUrl(id), '_blank')
    toast('Генерация PDF…', 'info')
  }
  const downloadJson = () => {
    window.open(reportsAPI.jsonUrl(id), '_blank')
  }

  if (loading) return <ResultsSkeleton />

  if (!data) return (
    <div className="p-6 text-center text-ink-tertiary">Проверка не найдена</div>
  )

  const allViolations = data.detections?.flatMap(d => d.violations || []) || []
  const isProcessing = data.status === 'pending' || data.status === 'processing'
  const imgSrc = showOriginal ? data.image_url : (data.annotated_url || data.image_url)

  return (
    <div className="p-6 max-w-screen-xl mx-auto">
      {/* Header */}
      <div className="flex items-start justify-between mb-6">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <h1 className="text-xl font-semibold text-ink-primary">Результаты анализа</h1>
            {isProcessing && (
              <div className="flex items-center gap-1.5 text-xs text-brand-600 bg-brand-50 px-2 py-1 rounded-full">
                <div className="w-2 h-2 border border-brand-600 border-t-transparent rounded-full animate-spin" />
                Обрабатывается…
              </div>
            )}
          </div>
          <div className="text-sm text-ink-tertiary">
            {data.address || data.original_filename} ·{' '}
            {data.created_at ? format(new Date(data.created_at), 'dd.MM.yyyy HH:mm') : '—'}
          </div>
        </div>
        <div className="flex gap-2 flex-wrap">
          <button onClick={downloadJson} className="btn-secondary text-xs gap-1.5">
            <FileJson size={13} /> JSON
          </button>
          <button onClick={downloadPdf} className="btn-primary text-xs gap-1.5">
            <FileText size={13} /> PDF-отчёт
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 grid-cols-1 xl:grid-cols-5 gap-5">
        {/* Image panel */}
        <div className="xl:col-span-3 space-y-4">
          <div className="card overflow-hidden">
            <div className="flex items-center justify-between px-4 py-3 border-b border-surface-3">
              <span className="text-sm font-medium text-ink-primary">
                {showOriginal ? 'Оригинал' : 'С аннотациями'}
              </span>
              <button
                onClick={() => setShowOriginal(p => !p)}
                className="btn-ghost text-xs gap-1"
              >
                {showOriginal ? <><CheckCircle2 size={12} /> Аннотации</> : <><Camera size={12} /> Оригинал</>}
              </button>
            </div>
            <div className="relative bg-slate-100 aspect-[4/3] overflow-hidden">
              {isProcessing ? (
                <div className="absolute inset-0 flex flex-col items-center justify-center gap-3">
                  <div className="w-10 h-10 border-2 border-brand-600 border-t-transparent rounded-full animate-spin" />
                  <div className="text-sm text-ink-tertiary">Анализ изображения…</div>
                </div>
              ) : imgError ? (
                <div className="absolute inset-0 flex items-center justify-center">
                  <img src={data.image_url} alt="" className="max-h-full max-w-full object-contain" />
                </div>
              ) : (
                <img
                  src={imgSrc}
                  alt="Результат анализа"
                  className="w-full h-full object-contain"
                  onError={() => { setImgError(true); setShowOriginal(true) }}
                />
              )}
            </div>
            <div className="px-4 py-2.5 flex items-center gap-4 text-xs text-ink-tertiary border-t border-surface-3">
              {data.model_version && <span className="font-mono">{data.model_version}</span>}
              {data.processing_time_ms && <span>{data.processing_time_ms} мс</span>}
              {data.image_width && <span>{data.image_width}×{data.image_height} px</span>}
            </div>
          </div>

          {/* EXIF / metadata block */}
          {(data.exif_summary?.length > 0 || data.gps_lat) && (
            <div className="card overflow-hidden">
              <button
                onClick={() => setExifOpen(p => !p)}
                className="w-full flex items-center justify-between px-4 py-3 hover:bg-surface-1 transition-colors"
              >
                <div className="flex items-center gap-2 text-sm font-medium text-ink-primary">
                  <Info size={14} className="text-ink-tertiary" />
                  Метаданные изображения (EXIF)
                </div>
                {exifOpen ? <ChevronUp size={14} className="text-ink-tertiary" /> : <ChevronDown size={14} className="text-ink-tertiary" />}
              </button>
              {exifOpen && (
                <div className="px-4 pb-4 border-t border-surface-3">
                  <div className="mt-3 grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-2">
                    {data.exif_summary?.map(s => (
                      <div key={s.key} className="flex gap-2 text-xs">
                        <span className="text-ink-disabled whitespace-nowrap">{s.key}:</span>
                        <span className="text-ink-secondary font-mono truncate">{s.value}</span>
                      </div>
                    ))}
                  </div>
                  {data.gps_lat && (
                    <div className="mt-3 flex items-center gap-2 text-xs text-success-700 bg-success-50 rounded-lg px-3 py-2">
                      <MapPin size={12} />
                      GPS: {data.gps_lat.toFixed(6)}, {data.gps_lon.toFixed(6)}
                    </div>
                  )}
                </div>
              )}
            </div>
          )}

          {/* Detections list */}
          {data.detections?.length > 0 && (
            <div className="card p-5">
              <div className="text-sm font-medium text-ink-primary mb-4">
                Обнаружено объектов: <span className="text-brand-600">{data.detections.length}</span>
              </div>
              <div className="space-y-3">
                {data.detections.map((det, i) => (
                  <DetectionCard key={det.id || i} det={det} />
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Violations panel */}
        <div className="xl:col-span-2 space-y-4">
          {/* Summary */}
          <div className="card p-5">
            <div className="flex items-center justify-between mb-4">
              <div className="text-sm font-medium text-ink-primary">Итог проверки</div>
              {allViolations.length > 0 ? (
                <span className="badge badge-red">{allViolations.length} нарушений</span>
              ) : !isProcessing ? (
                <span className="badge badge-green">Нарушений нет</span>
              ) : null}
            </div>
            {isProcessing ? (
              <div className="py-6 text-center">
                <div className="w-8 h-8 border-2 border-brand-600 border-t-transparent rounded-full animate-spin mx-auto mb-3" />
                <div className="text-sm text-ink-tertiary">Идёт анализ…</div>
              </div>
            ) : allViolations.length === 0 ? (
              <div className="flex flex-col items-center py-6 gap-2">
                <CheckCircle2 size={32} className="text-success-500" />
                <div className="text-sm font-medium text-success-700">Нарушений не выявлено</div>
                <div className="text-xs text-ink-tertiary text-center">Объект соответствует требованиям нормативной базы</div>
              </div>
            ) : (
              <div className="space-y-3">
                {allViolations.map((v, i) => (
                  <ViolationCard key={v.id || i} v={v} idx={i} />
                ))}
              </div>
            )}
          </div>

          {/* Inference chain */}
          {allViolations.length > 0 && (
            <div className="card p-5">
              <div className="text-sm font-medium text-ink-primary mb-3">Цепочка логического вывода</div>
              <div className="font-mono text-xs space-y-1.5 text-ink-tertiary">
                <div className="text-brand-600">→ Получены факты от YOLOv8 / OCR</div>
                {allViolations.map((v, i) => (
                  <div key={i}>
                    <div className="text-ink-secondary">→ Правило <span className="text-brand-600">{v.rule_id}</span>: условие ИСТИНА</div>
                    <div className="text-danger-600 ml-2">→ Assert: нарушение({VIOLATION_LABELS[v.violation_type?.split('.').pop()] || v.violation_type})</div>
                  </div>
                ))}
                <div className="text-success-600">→ Вывод завершён · {allViolations.length} нарушений</div>
              </div>
            </div>
          )}

          {/* Object info */}
          <div className="card p-5 text-xs space-y-2">
            <div className="text-sm font-medium text-ink-primary mb-2">Сведения об объекте</div>
            <Row label="Адрес" value={data.address || '—'} />
            <Row label="Город" value={data.city || '—'} />
            <Row label="ID проверки" value={data.id?.slice(0, 12).toUpperCase()} mono />
            <Row label="Статус" value={data.status} />
            {data.file_size && <Row label="Размер файла" value={`${(data.file_size / 1024).toFixed(0)} КБ`} />}
            {data.camera_model && <Row label="Камера" value={`${data.camera_make || ''} ${data.camera_model}`} />}
          </div>
        </div>
      </div>
    </div>
  )
}

function DetectionCard({ det }) {
  return (
    <div className="border border-surface-3 rounded-lg p-3 text-xs space-y-1">
      <div className="flex items-center gap-2">
        <span className="font-medium text-ink-secondary">{det.class_name}</span>
        {det.banner_type && <span className="badge badge-blue text-[10px]">{det.banner_type}</span>}
        <span className="ml-auto text-ink-tertiary font-mono">{Math.round((det.confidence || 0) * 100)}%</span>
      </div>
      {det.ocr_text && (
        <div className="text-ink-tertiary truncate">«{det.ocr_text}»</div>
      )}
      {det.violations?.length > 0 && (
        <div className="text-danger-600">{det.violations.length} нарушений</div>
      )}
    </div>
  )
}

function ViolationCard({ v, idx }) {
  const sm = SEVERITY_META[v.severity?.split('.').pop()] || SEVERITY_META.medium
  const conf = Math.round((v.confidence || 0) * 100)
  return (
    <div className="border border-surface-3 rounded-lg p-3 animate-slide-up" style={{ animationDelay: `${idx * 80}ms` }}>
      <div className="flex items-start gap-2 mb-2">
        <AlertTriangle size={13} className="text-warn-500 mt-0.5 flex-shrink-0" />
        <div className="flex-1">
          <div className="text-sm font-medium text-ink-primary">
            {VIOLATION_LABELS[v.violation_type?.split('.').pop()] || v.violation_type}
          </div>
          <div className="flex items-center gap-2 mt-1">
            <span className={sm.cls}>{sm.label}</span>
            {v.rule_id && <code className="text-[10px] text-ink-tertiary">{v.rule_id}</code>}
          </div>
        </div>
      </div>
      {v.explanation && (
        <p className="text-xs text-ink-tertiary mb-2 leading-relaxed">{v.explanation}</p>
      )}
      {/* Confidence bar */}
      <div className="flex items-center gap-2">
        <div className="flex-1 h-1 bg-surface-2 rounded-full overflow-hidden">
          <div className={clsx('h-full rounded-full conf-bar', sm.bar)} style={{ width: `${conf}%` }} />
        </div>
        <span className="text-[10px] text-ink-tertiary font-mono w-8 text-right">{conf}%</span>
      </div>
    </div>
  )
}

function Row({ label, value, mono }) {
  return (
    <div className="flex gap-2 flex-wrap">
      <span className="text-ink-disabled w-28 flex-shrink-0">{label}</span>
      <span className={clsx('text-ink-secondary', mono && 'font-mono')}>{value}</span>
    </div>
  )
}

function ResultsSkeleton() {
  return (
    <div className="p-6 max-w-screen-xl mx-auto">
      <div className="h-6 w-56 bg-surface-2 rounded mb-2 animate-pulse" />
      <div className="h-4 w-72 bg-surface-2 rounded mb-6 animate-pulse" />
      <div className="grid grid-cols-1 grid-cols-1 xl:grid-cols-5 gap-5">
        <div className="xl:col-span-3 card h-96 animate-pulse bg-surface-1" />
        <div className="xl:col-span-2 card h-96 animate-pulse bg-surface-1" />
      </div>
    </div>
  )
}
