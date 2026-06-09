import { useState, useRef, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { Upload, FileImage, X, MapPin, Camera, CheckCircle2, Info } from 'lucide-react'
import { inspectionsAPI } from '../utils/api'
import { useToast } from '../hooks/useToast'
import clsx from 'clsx'

const PIPELINE_STEPS = [
  'Загрузка и валидация',
  'Детекция объектов (YOLOv8)',
  'Распознавание текста (OCR)',
  'Классификация (EfficientNet)',
  'Логический вывод',
  'Сохранение результатов',
]

export default function UploadPage() {
  const navigate = useNavigate()
  const { toast } = useToast()
  const fileRef = useRef()
  const [drag, setDrag]           = useState(false)
  const [file, setFile]           = useState(null)
  const [preview, setPreview]     = useState(null)
  const [exifData, setExifData]   = useState(null)
  const [exifLoading, setExifLoading] = useState(false)
  const [showExifDialog, setShowExifDialog] = useState(false)
  const [form, setForm]           = useState({ address: '', city: 'Тюмень', use_exif_gps: true, manual_lat: '', manual_lon: '' })
  const [uploading, setUploading] = useState(false)
  const [step, setStep]           = useState(0)

  const handleFile = useCallback(async (f) => {
    if (!f) return
    const ok = /\.(jpg|jpeg|png|webp|heic|tif|tiff)$/i.test(f.name)
    if (!ok) { toast('Неподдерживаемый формат', 'error'); return }
    if (f.size > 50 * 1024 * 1024) { toast('Файл > 50 МБ', 'error'); return }
    setFile(f)
    setPreview(URL.createObjectURL(f))
    setExifLoading(true)
    try {
      const r = await inspectionsAPI.exifPreview(f)
      setExifData(r.data)
      setShowExifDialog(true)
    } catch { setExifData(null) }
    finally { setExifLoading(false) }
  }, [toast])

  const onDrop = (e) => {
    e.preventDefault(); setDrag(false)
    const f = e.dataTransfer.files[0]
    if (f) handleFile(f)
  }

  const upload = async () => {
    if (!file) return
    setUploading(true); setStep(0)
    const interval = setInterval(() => setStep(s => s < PIPELINE_STEPS.length - 1 ? s + 1 : s), 800)
    try {
      const params = {
        address: form.address || undefined, city: form.city,
        use_exif_gps: form.use_exif_gps,
        manual_lat: form.manual_lat ? parseFloat(form.manual_lat) : undefined,
        manual_lon: form.manual_lon ? parseFloat(form.manual_lon) : undefined,
      }
      const r = await inspectionsAPI.upload(file, params)
      clearInterval(interval); setStep(PIPELINE_STEPS.length - 1)
      toast('Анализ запущен…', 'success')
      setTimeout(() => navigate(`/results/${r.data.id}`), 500)
    } catch (e) {
      clearInterval(interval)
      toast(e.response?.data?.detail || 'Ошибка загрузки', 'error')
      setUploading(false); setStep(0)
    }
  }

  const reset = () => {
    setFile(null); setPreview(null); setExifData(null)
    setShowExifDialog(false); setUploading(false); setStep(0)
    setForm({ address: '', city: 'Тюмень', use_exif_gps: true, manual_lat: '', manual_lon: '' })
  }

  return (
    <div className="p-4 sm:p-6 max-w-2xl mx-auto">
      <div className="mb-5">
        <h1 className="text-lg sm:text-xl font-semibold text-ink-primary">Загрузка и анализ</h1>
        <p className="text-xs sm:text-sm text-ink-tertiary mt-0.5">Загрузите фото объекта для автоматического анализа</p>
      </div>

      {!file ? (
        /* Drop zone — tap-friendly on mobile */
        <div
          className={clsx(
            'border-2 border-dashed rounded-card p-8 sm:p-14 text-center cursor-pointer transition-all duration-200',
            drag ? 'border-brand-500 bg-brand-50' : 'border-surface-3 hover:border-brand-300 hover:bg-surface-1'
          )}
          onDragOver={e => { e.preventDefault(); setDrag(true) }}
          onDragLeave={() => setDrag(false)}
          onDrop={onDrop}
          onClick={() => fileRef.current?.click()}
        >
          <input ref={fileRef} type="file" accept="image/*" className="hidden"
            onChange={e => e.target.files[0] && handleFile(e.target.files[0])} />
          <div className="w-12 h-12 sm:w-14 sm:h-14 mx-auto mb-4 rounded-xl bg-surface-2 flex items-center justify-center">
            {exifLoading
              ? <div className="w-5 h-5 border-2 border-brand-600 border-t-transparent rounded-full animate-spin" />
              : <FileImage size={24} className="text-ink-tertiary" />}
          </div>
          <div className="text-sm sm:text-base font-medium text-ink-primary mb-1">
            Нажмите или перетащите фото
          </div>
          <div className="text-xs sm:text-sm text-ink-tertiary mb-4">
            JPG, PNG, WEBP, HEIC · до 50 МБ
          </div>
          {/* Big tap target on mobile */}
          <div className="flex gap-2 justify-center flex-wrap">
            <button
              type="button"
              className="btn-primary text-sm px-5 py-2.5"
              onClick={e => { e.stopPropagation(); fileRef.current?.click() }}
            >
              <Upload size={15} /> Выбрать файл
            </button>
          </div>
          <div className="flex gap-1.5 justify-center flex-wrap mt-4">
            {['JPG','PNG','WEBP','HEIC'].map(f => (
              <span key={f} className="badge badge-gray font-mono text-[10px]">{f}</span>
            ))}
          </div>
        </div>
      ) : (
        <div className="space-y-4">
          {/* Preview card */}
          <div className="card overflow-hidden">
            <div className="flex items-start gap-3 p-4">
              <div className="w-16 h-16 sm:w-20 sm:h-20 rounded-lg overflow-hidden bg-surface-2 flex-shrink-0">
                <img src={preview} alt="" className="w-full h-full object-cover" />
              </div>
              <div className="flex-1 min-w-0">
                <div className="font-medium text-ink-primary text-sm truncate">{file.name}</div>
                <div className="text-xs text-ink-tertiary mt-1 font-mono">
                  {(file.size / 1024 / 1024).toFixed(1)} МБ
                  {exifData?.exif?.width && ` · ${exifData.exif.width}×${exifData.exif.height}`}
                </div>
                {exifData?.has_gps && (
                  <div className="flex items-center gap-1 mt-1.5 text-xs text-success-700 bg-success-50 rounded px-2 py-1 w-fit">
                    <MapPin size={11} /> GPS найден
                  </div>
                )}
                {exifData?.exif?.camera_model && (
                  <div className="flex items-center gap-1 mt-1 text-xs text-ink-tertiary">
                    <Camera size={11} /> {exifData.exif.camera_make} {exifData.exif.camera_model}
                  </div>
                )}
              </div>
              {!uploading && (
                <button onClick={reset} className="text-ink-disabled hover:text-ink-tertiary flex-shrink-0">
                  <X size={16} />
                </button>
              )}
            </div>
          </div>

          {/* Form */}
          {!uploading && (
            <div className="card p-4 sm:p-5 space-y-4">
              <div className="text-sm font-medium text-ink-primary">Параметры проверки</div>

              <div>
                <label className="label">Адрес объекта</label>
                <input className="input" placeholder="ул. Ленина, 28, Тюмень"
                  value={form.address} onChange={e => setForm(p => ({ ...p, address: e.target.value }))} />
              </div>
              <div>
                <label className="label">Город</label>
                <input className="input" value={form.city}
                  onChange={e => setForm(p => ({ ...p, city: e.target.value }))} />
              </div>

              {exifData?.has_gps && (
                <label className="flex items-center gap-2.5 cursor-pointer select-none text-sm text-ink-secondary">
                  <input type="checkbox" checked={form.use_exif_gps}
                    onChange={e => setForm(p => ({ ...p, use_exif_gps: e.target.checked }))}
                    className="w-4 h-4 accent-brand-600 rounded" />
                  Использовать GPS из EXIF
                </label>
              )}

              {(!exifData?.has_gps || !form.use_exif_gps) && (
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="label">Широта</label>
                    <input className="input font-mono text-sm" placeholder="57.152900"
                      value={form.manual_lat} onChange={e => setForm(p => ({ ...p, manual_lat: e.target.value }))} />
                  </div>
                  <div>
                    <label className="label">Долгота</label>
                    <input className="input font-mono text-sm" placeholder="65.534300"
                      value={form.manual_lon} onChange={e => setForm(p => ({ ...p, manual_lon: e.target.value }))} />
                  </div>
                </div>
              )}

              {exifData?.exif_summary?.length > 0 && (
                <div className="bg-surface-1 rounded-lg border border-surface-3 p-3">
                  <div className="flex items-center gap-1.5 text-xs font-medium text-ink-secondary mb-2">
                    <Info size={12} /> EXIF-метаданные
                  </div>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-4 gap-y-1">
                    {exifData.exif_summary.map(s => (
                      <div key={s.key} className="flex gap-2 text-xs">
                        <span className="text-ink-disabled whitespace-nowrap">{s.key}:</span>
                        <span className="text-ink-secondary font-mono truncate">{s.value}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              <button onClick={upload} className="btn-primary w-full justify-center py-3 text-sm">
                <Upload size={15} /> Запустить анализ
              </button>
            </div>
          )}

          {/* Pipeline progress */}
          {uploading && (
            <div className="card p-4 sm:p-5">
              <div className="text-sm font-medium text-ink-primary mb-4">Анализ изображения</div>
              <div className="space-y-3">
                {PIPELINE_STEPS.map((label, i) => (
                  <div key={label} className="flex items-center gap-3">
                    <div className={clsx(
                      'w-5 h-5 rounded-full flex items-center justify-center flex-shrink-0 transition-all',
                      i < step ? 'bg-success-500' : i === step ? 'bg-brand-600' : 'bg-surface-2'
                    )}>
                      {i < step
                        ? <CheckCircle2 size={11} className="text-white" />
                        : i === step
                          ? <div className="w-2 h-2 bg-white rounded-full animate-pulse" />
                          : null}
                    </div>
                    <span className={clsx('text-sm transition-colors',
                      i < step ? 'text-success-700' : i === step ? 'text-brand-700 font-medium' : 'text-ink-disabled')}>
                      {label}
                    </span>
                    {i === step && <div className="ml-auto w-3 h-3 border-2 border-brand-600 border-t-transparent rounded-full animate-spin" />}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* EXIF Dialog */}
      {showExifDialog && exifData && (
        <div className="fixed inset-0 bg-black/30 backdrop-blur-sm flex items-end sm:items-center justify-center z-50 p-4">
          <div className="bg-white rounded-t-2xl sm:rounded-card shadow-modal w-full sm:max-w-md animate-slide-up">
            <div className="flex items-center justify-between p-4 sm:p-5 border-b border-surface-3">
              <div className="flex items-center gap-2">
                <Info size={15} className="text-brand-600" />
                <span className="font-medium text-ink-primary text-sm">Метаданные найдены</span>
              </div>
              <button onClick={() => setShowExifDialog(false)} className="text-ink-disabled hover:text-ink-tertiary p-1">
                <X size={16} />
              </button>
            </div>
            <div className="p-4 sm:p-5">
              <p className="text-sm text-ink-secondary mb-4">Изображение содержит EXIF-данные. Они будут сохранены в отчёте.</p>
              <div className="space-y-2 mb-5">
                {exifData.exif_summary?.map(s => (
                  <div key={s.key} className="flex items-start gap-3 text-sm">
                    <span className="text-ink-disabled w-28 flex-shrink-0 text-xs">{s.key}</span>
                    <span className="text-ink-primary font-mono text-xs">{s.value}</span>
                  </div>
                ))}
                {exifData.has_gps && (
                  <div className="flex items-center gap-2 mt-3 p-2.5 bg-success-50 rounded-lg border border-success-100">
                    <CheckCircle2 size={13} className="text-success-600" />
                    <span className="text-xs text-success-700">GPS будет добавлен на карту</span>
                  </div>
                )}
              </div>
              <div className="flex gap-2">
                <button onClick={() => setShowExifDialog(false)} className="btn-secondary flex-1 justify-center py-2.5">Отмена</button>
                <button onClick={() => setShowExifDialog(false)} className="btn-primary flex-1 justify-center py-2.5">Продолжить</button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
