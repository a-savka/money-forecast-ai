import { ChevronRight, FileSpreadsheet, ImageUp, Landmark, PencilLine, QrCode, type LucideIcon } from 'lucide-react'
import { useNavigate } from 'react-router-dom'

interface Option {
  icon: LucideIcon
  title: string
  hint: string
  action: () => void
}

/** Способы добавить операции: вручную, выпиской, из банка, по чеку или скриншоту. */
export function AddMenu({ onManual }: { onManual: () => void }) {
  const navigate = useNavigate()
  const options: Option[] = [
    {
      icon: Landmark,
      title: 'Подключить банк',
      hint: 'Т-Банк, Сбер, Альфа и другие — автоматически',
      action: () => navigate('/connect-bank'),
    },
    { icon: PencilLine, title: 'Ввести вручную', hint: 'Сумма, категория — 3 касания', action: onManual },
    {
      icon: QrCode,
      title: 'Сканировать чек',
      hint: 'QR-код на бумажном чеке',
      action: () => navigate('/receipt'),
    },
    {
      icon: ImageUp,
      title: 'Скриншот из банка',
      hint: 'ИИ распознает сумму, дату и магазин',
      action: () => navigate('/screenshot'),
    },
    {
      icon: FileSpreadsheet,
      title: 'Загрузить выписку',
      hint: 'CSV или Excel из банка',
      action: () => navigate('/import'),
    },
  ]
  return (
    <ul className="space-y-2">
      {options.map(({ icon: Icon, title, hint, action }) => (
        <li key={title}>
          <button onClick={action} className="flex w-full items-center gap-3 rounded-xl border border-slate-200 p-3 text-left hover:bg-slate-50">
            <span className="flex h-10 w-10 items-center justify-center rounded-full bg-brand-50 text-brand-600">
              <Icon className="h-5 w-5" />
            </span>
            <span className="flex-1">
              <span className="block font-medium">{title}</span>
              <span className="block text-sm text-slate-500">{hint}</span>
            </span>
            <ChevronRight className="h-5 w-5 text-slate-400" />
          </button>
        </li>
      ))}
    </ul>
  )
}
