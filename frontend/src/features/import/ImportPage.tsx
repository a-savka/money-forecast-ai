import { ArrowLeft, CheckCircle2, FileSpreadsheet, Upload } from 'lucide-react'
import { useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'

import { useAccounts, useCategoryMap } from '@/api/hooks'
import type { ColumnMapping, ImportPreview, ImportResult } from '@/api/types'
import { CategoryIcon } from '@/components/CategoryIcon'
import { Button } from '@/components/ui/button'
import { Card, CardTitle } from '@/components/ui/card'
import { Badge, ErrorMessage } from '@/components/ui/feedback'
import { Input, Label, Select } from '@/components/ui/input'
import { formatDate, formatMoney } from '@/lib/utils'

import { useConfirmImport, useUploadStatement } from './api'

const NEW_ACCOUNT = 'new'

export function ImportPage() {
  const [file, setFile] = useState<File | null>(null)
  const [preview, setPreview] = useState<ImportPreview | null>(null)
  const [result, setResult] = useState<ImportResult | null>(null)
  const upload = useUploadStatement()

  const send = async (f: File, mapping?: ColumnMapping) => {
    setFile(f)
    setPreview(await upload.mutateAsync({ file: f, mapping }))
  }

  return (
    <div className="mx-auto min-h-full max-w-md bg-slate-50 px-4 pb-10">
      <header className="pt-safe flex items-center gap-2 py-4">
        <Link to="/transactions" className="rounded-full p-1 hover:bg-slate-200" aria-label="Назад">
          <ArrowLeft className="h-6 w-6" />
        </Link>
        <h1 className="text-xl font-bold">Импорт выписки</h1>
      </header>

      {result ? (
        <Done result={result} />
      ) : (
        <div className="space-y-4">
          <FilePicker onPick={(f) => send(f)} busy={upload.isPending} fileName={file?.name} />
          {upload.error && <ErrorMessage error={upload.error} />}
          {preview && !preview.mapping && file && (
            <MappingWizard headers={preview.headers} busy={upload.isPending} onSubmit={(m) => send(file, m)} />
          )}
          {preview?.mapping && preview.job_id && <PreviewCard preview={preview} onDone={setResult} />}
          {preview?.mapping && !preview.job_id && <ErrorMessage error={new Error('В файле не найдено операций')} />}
        </div>
      )}
    </div>
  )
}

function FilePicker({ onPick, busy, fileName }: { onPick: (f: File) => void; busy: boolean; fileName?: string }) {
  return (
    <Card>
      <label className="flex cursor-pointer flex-col items-center gap-2 rounded-xl border-2 border-dashed border-slate-200 p-6 text-center hover:border-brand-500">
        {fileName ? <FileSpreadsheet className="h-8 w-8 text-brand-600" /> : <Upload className="h-8 w-8 text-slate-400" />}
        <span className="font-medium">{busy ? 'Читаем файл…' : (fileName ?? 'Выберите файл выписки')}</span>
        <span className="text-sm text-slate-500">CSV или Excel. Т-Банк распознаётся автоматически</span>
        <input
          type="file"
          accept=".csv,.xlsx,text/csv"
          className="hidden"
          onChange={(e) => {
            const f = e.target.files?.[0]
            if (f) onPick(f)
            e.target.value = ''
          }}
        />
      </label>
    </Card>
  )
}

type MappingField = 'date' | 'description' | 'amount' | 'expense' | 'income'

function MappingWizard({
  headers,
  busy,
  onSubmit,
}: {
  headers: string[]
  busy: boolean
  onSubmit: (m: ColumnMapping) => void
}) {
  const [twoColumns, setTwoColumns] = useState(false)
  const [m, setM] = useState<Partial<Record<MappingField, number>>>({})
  const fields: [MappingField, string][] = [
    ['date', 'Дата'],
    ['description', 'Описание'],
    ...(twoColumns
      ? ([
          ['expense', 'Расход'],
          ['income', 'Приход'],
        ] as [MappingField, string][])
      : ([['amount', 'Сумма (со знаком)']] as [MappingField, string][])),
  ]
  const ready = m.date !== undefined && (twoColumns ? m.expense !== undefined || m.income !== undefined : m.amount !== undefined)

  return (
    <Card className="space-y-3">
      <h2 className="font-semibold">Сопоставьте колонки</h2>
      <p className="text-sm text-slate-500">Формат файла не распознан автоматически. Укажите, где какие данные.</p>
      <label className="flex items-center gap-2 text-sm">
        <input type="checkbox" checked={twoColumns} onChange={(e) => setTwoColumns(e.target.checked)} />
        Расход и приход в разных колонках
      </label>
      {fields.map(([key, label]) => (
        <div key={key}>
          <Label htmlFor={`map-${key}`}>{label}</Label>
          <Select
            id={`map-${key}`}
            value={m[key] ?? ''}
            onChange={(e) => setM({ ...m, [key]: e.target.value === '' ? undefined : Number(e.target.value) })}
          >
            <option value="">— не выбрано —</option>
            {headers.map((h, i) => (
              <option key={i} value={i}>
                {h || `Колонка ${i + 1}`}
              </option>
            ))}
          </Select>
        </div>
      ))}
      <Button className="w-full" disabled={!ready || busy} onClick={() => onSubmit(m as ColumnMapping)}>
        Применить
      </Button>
    </Card>
  )
}

function PreviewCard({ preview, onDone }: { preview: ImportPreview; onDone: (r: ImportResult) => void }) {
  const categories = useCategoryMap()
  const { data: accounts = [] } = useAccounts()
  const [account, setAccount] = useState<string>(NEW_ACCOUNT)
  const [newName, setNewName] = useState(preview.bank_name ? `Карта ${preview.bank_name}` : 'Импортированный счёт')
  const confirm = useConfirmImport()
  const fresh = preview.rows_total - preview.duplicates

  return (
    <>
      <Card className="space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="font-semibold">{preview.file_name}</h2>
          {preview.bank_name && <Badge tone="brand">{preview.bank_name}</Badge>}
        </div>
        {preview.period_start && preview.period_end && (
          <p className="text-sm text-slate-500">
            {formatDate(preview.period_start)} — {formatDate(preview.period_end)}
          </p>
        )}
        <div className="grid grid-cols-3 gap-2 text-center">
          <Stat label="Операций" value={String(preview.rows_total)} />
          <Stat label="Доходы" value={formatMoney(preview.total_income)} />
          <Stat label="Расходы" value={formatMoney(preview.total_expense)} />
        </div>
        {preview.duplicates > 0 && (
          <p className="rounded-xl bg-amber-50 p-2 text-sm text-amber-800">
            {preview.duplicates} операций уже есть в приложении — они будут пропущены
          </p>
        )}
        {preview.errors.length > 0 && (
          <details className="text-sm text-red-700">
            <summary>Ошибок в строках: {preview.errors.length}</summary>
            <ul className="mt-1 list-disc pl-5">
              {preview.errors.map((e) => (
                <li key={e}>{e}</li>
              ))}
            </ul>
          </details>
        )}
      </Card>

      <Card>
        <CardTitle className="mb-2">Первые операции</CardTitle>
        <ul className="divide-y divide-slate-100">
          {preview.sample.slice(0, 8).map((r) => (
            <li key={r.line} className="flex items-center gap-3 py-2">
              <CategoryIcon category={r.category_id ? categories.get(r.category_id) : undefined} size="sm" />
              <span className="min-w-0 flex-1">
                <span className="block truncate text-sm font-medium">{r.description}</span>
                <span className="block text-xs text-slate-500">
                  {formatDate(r.date)} · {r.category_id ? categories.get(r.category_id)?.name : '—'}
                </span>
              </span>
              <span className="text-sm font-semibold tabular-nums">{formatMoney(r.amount, { sign: true })}</span>
              {r.duplicate && <Badge tone="amber">дубль</Badge>}
            </li>
          ))}
        </ul>
      </Card>

      <Card className="space-y-3">
        <div>
          <Label htmlFor="account">Куда загрузить</Label>
          <Select id="account" value={account} onChange={(e) => setAccount(e.target.value)}>
            <option value={NEW_ACCOUNT}>Новый счёт</option>
            {accounts.map((a) => (
              <option key={a.id} value={a.id}>
                {a.name}
              </option>
            ))}
          </Select>
        </div>
        {account === NEW_ACCOUNT && (
          <div>
            <Label htmlFor="new-name">Название счёта</Label>
            <Input id="new-name" value={newName} onChange={(e) => setNewName(e.target.value)} />
          </div>
        )}
        {confirm.error && <ErrorMessage error={confirm.error} />}
        <Button
          className="w-full"
          disabled={confirm.isPending || fresh === 0}
          onClick={async () =>
            onDone(
              await confirm.mutateAsync({
                jobId: preview.job_id!,
                accountId: account === NEW_ACCOUNT ? undefined : Number(account),
                newAccountName: account === NEW_ACCOUNT ? newName : undefined,
              }),
            )
          }
        >
          {fresh === 0 ? 'Новых операций нет' : `Загрузить ${fresh} операций`}
        </Button>
      </Card>
    </>
  )
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl bg-slate-50 p-2">
      <div className="text-xs text-slate-500">{label}</div>
      <div className="text-sm font-semibold">{value}</div>
    </div>
  )
}

function Done({ result }: { result: ImportResult }) {
  const navigate = useNavigate()
  // Из онбординга возвращаемся на экран первого прогноза
  const next = useSearchParams()[0].get('next') ?? '/'
  return (
    <Card className="flex flex-col items-center gap-3 py-8 text-center">
      <CheckCircle2 className="h-12 w-12 text-emerald-500" />
      <h2 className="text-lg font-semibold">Выписка загружена</h2>
      <p className="text-slate-500">
        Добавлено операций: {result.imported}
        {result.skipped > 0 && `, пропущено дублей: ${result.skipped}`}
      </p>
      <Button className="w-full" onClick={() => navigate(next)}>
        Посмотреть прогноз
      </Button>
      <Button className="w-full" variant="secondary" onClick={() => navigate('/transactions')}>
        К операциям
      </Button>
    </Card>
  )
}
