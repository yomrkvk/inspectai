import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ScanSearch, Eye, EyeOff, AlertCircle } from 'lucide-react'
import { useAuth } from '../hooks/useAuth'

export default function LoginPage() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const [form, setForm] = useState({ username: '', password: '' })
  const [showPwd, setShowPwd] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const submit = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      await login(form.username, form.password)
      navigate('/')
    } catch {
      setError('Неверный логин или пароль')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-surface-1 flex">
      {/* Left panel */}
      <div className="hidden lg:flex lg:w-1/2 bg-brand-600 flex-col justify-between p-12">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 bg-white/20 rounded-lg flex items-center justify-center">
            <ScanSearch size={20} className="text-white" />
          </div>
          <span className="text-white font-semibold text-lg tracking-tight">InspectAI</span>
        </div>
        <div>
          <h1 className="text-white text-4xl font-bold leading-tight mb-4">
            Интеллектуальный контроль городской среды
          </h1>
          <p className="text-blue-200 text-base leading-relaxed max-w-md">
            Автоматический анализ изображений рекламных конструкций на основе YOLOv8, OCR и продукционных правил.
          </p>
          <div className="mt-10 grid grid-cols-3 gap-4">
            {[
              { label: 'Точность', value: '94%' },
              { label: 'Объектов', value: '48+' },
              { label: 'Правил вывода', value: '12' },
            ].map(s => (
              <div key={s.label} className="bg-white/10 rounded-lg px-4 py-3">
                <div className="text-white text-2xl font-bold">{s.value}</div>
                <div className="text-blue-200 text-xs mt-0.5">{s.label}</div>
              </div>
            ))}
          </div>
        </div>
        <div className="text-blue-300 text-xs">© 2026 InspectAI · Тюменский Индустриальный Университет</div>
      </div>

      {/* Right panel */}
      <div className="flex-1 flex items-center justify-center p-8">
        <div className="w-full max-w-sm">
          <div className="flex items-center gap-2 mb-8 lg:hidden">
            <div className="w-8 h-8 bg-brand-600 rounded-lg flex items-center justify-center">
              <ScanSearch size={16} className="text-white" />
            </div>
            <span className="font-semibold text-ink-primary">InspectAI</span>
          </div>

          <h2 className="text-2xl font-bold text-ink-primary mb-1">Войти в систему</h2>
          <p className="text-sm text-ink-tertiary mb-8">Введите учётные данные для доступа</p>

          <form onSubmit={submit} className="space-y-4">
            <div>
              <label className="label">Имя пользователя</label>
              <input
                className="input"
                placeholder="inspector"
                value={form.username}
                onChange={e => setForm(p => ({ ...p, username: e.target.value }))}
                autoComplete="username"
                required
              />
            </div>
            <div>
              <label className="label">Пароль</label>
              <div className="relative">
                <input
                  className="input pr-10"
                  type={showPwd ? 'text' : 'password'}
                  placeholder="••••••••"
                  value={form.password}
                  onChange={e => setForm(p => ({ ...p, password: e.target.value }))}
                  autoComplete="current-password"
                  required
                />
                <button
                  type="button"
                  onClick={() => setShowPwd(p => !p)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-ink-disabled hover:text-ink-tertiary"
                >
                  {showPwd ? <EyeOff size={15} /> : <Eye size={15} />}
                </button>
              </div>
            </div>

            {error && (
              <div className="flex items-center gap-2 text-danger-600 bg-danger-50 border border-danger-100 rounded-btn px-3 py-2.5 text-sm">
                <AlertCircle size={14} className="flex-shrink-0" />
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={loading}
              className="btn-primary w-full justify-center py-2.5"
            >
              {loading ? (
                <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
              ) : 'Войти'}
            </button>
          </form>

          <div className="mt-6 p-3 bg-surface-1 rounded-btn border border-surface-3 text-xs text-ink-tertiary">
            <div className="font-medium text-ink-secondary mb-1">Тестовый доступ</div>
            <div>Логин: <code className="font-mono text-brand-600">admin</code> · Пароль: <code className="font-mono text-brand-600">admin123</code></div>
          </div>
        </div>
      </div>
    </div>
  )
}
