import { createContext, useContext, useState, useCallback, useRef } from 'react'
import { CheckCircle, XCircle, AlertTriangle, Info, X } from 'lucide-react'

const ToastContext = createContext(null)

const ICONS = {
  success: CheckCircle,
  error: XCircle,
  warning: AlertTriangle,
  info: Info,
}
const COLORS = {
  success: 'text-success-600',
  error: 'text-danger-600',
  warning: 'text-warn-600',
  info: 'text-brand-600',
}

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([])
  const idRef = useRef(0)

  const toast = useCallback((message, type = 'info', duration = 4000) => {
    const id = ++idRef.current
    setToasts(p => [...p, { id, message, type }])
    setTimeout(() => setToasts(p => p.filter(t => t.id !== id)), duration)
    return id
  }, [])

  const dismiss = useCallback((id) => {
    setToasts(p => p.filter(t => t.id !== id))
  }, [])

  return (
    <ToastContext.Provider value={{ toast }}>
      {children}
      <div className="fixed bottom-5 right-5 z-50 flex flex-col gap-2 pointer-events-none">
        {toasts.map(t => {
          const Icon = ICONS[t.type] || Info
          return (
            <div
              key={t.id}
              className="pointer-events-auto toast-enter flex items-start gap-3 bg-white border border-surface-3 rounded-card shadow-dropdown px-4 py-3 min-w-[280px] max-w-[380px]"
            >
              <Icon size={16} className={`mt-0.5 flex-shrink-0 ${COLORS[t.type]}`} />
              <span className="flex-1 text-sm text-ink-secondary leading-snug">{t.message}</span>
              <button onClick={() => dismiss(t.id)} className="text-ink-disabled hover:text-ink-tertiary transition-colors">
                <X size={14} />
              </button>
            </div>
          )
        })}
      </div>
    </ToastContext.Provider>
  )
}

export const useToast = () => useContext(ToastContext)
