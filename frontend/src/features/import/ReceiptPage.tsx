import { useMutation } from '@tanstack/react-query'
import { ArrowLeft, Camera, QrCode } from 'lucide-react'
import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'

import { api, unwrap } from '@/api/client'
import type { TransactionDraftOut } from '@/api/types'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { ErrorMessage } from '@/components/ui/feedback'
import { Label } from '@/components/ui/input'
import { TransactionForm } from '@/features/transactions/TransactionForm'
import { decodeQrFromFile } from '@/lib/qr'

const SAMPLE_QR = 't=20261025T1942&s=1245.50&fn=7380440700076549&i=41975&fp=2026408802&n=1'

export function ReceiptPage() {
  const navigate = useNavigate()
  const [qr, setQr] = useState('')
  const [scanError, setScanError] = useState<string | null>(null)
  const [scanning, setScanning] = useState(false)

  const parse = useMutation({
    mutationFn: (raw: string) => unwrap<TransactionDraftOut>(api.POST('/imports/receipt/qr', { body: { qr: raw } })),
  })

  const onPhoto = async (file: File) => {
    setScanError(null)
    setScanning(true)
    try {
      const text = await decodeQrFromFile(file)
      if (!text) {
        setScanError('QR-код не найден. Сфотографируйте его крупнее и при хорошем освещении.')
        return
      }
      setQr(text)
      parse.mutate(text)
    } finally {
      setScanning(false)
    }
  }

  return (
    <div className="mx-auto min-h-full max-w-md bg-slate-50 px-4 pb-10">
      <header className="pt-safe flex items-center gap-2 py-4">
        <Link to="/transactions" className="rounded-full p-1 hover:bg-slate-200" aria-label="Назад">
          <ArrowLeft className="h-6 w-6" />
        </Link>
        <h1 className="text-xl font-bold">Чек по QR-коду</h1>
      </header>

      {parse.data ? (
        <Card>
          <p className="mb-3 text-sm text-slate-500">Проверьте данные из чека и выберите категорию</p>
          <TransactionForm draft={parse.data} onDone={() => navigate('/transactions')} />
        </Card>
      ) : (
        <div className="space-y-4">
          <Card>
            <label className="flex cursor-pointer flex-col items-center gap-2 rounded-xl border-2 border-dashed border-slate-200 p-6 text-center hover:border-brand-500">
              <Camera className="h-8 w-8 text-brand-600" />
              <span className="font-medium">{scanning ? 'Ищем QR-код…' : 'Сфотографировать чек'}</span>
              <span className="text-sm text-slate-500">QR-код внизу кассового чека: сумма и дата подставятся сами</span>
              <input
                type="file"
                accept="image/*"
                capture="environment"
                className="hidden"
                onChange={(e) => {
                  const f = e.target.files?.[0]
                  if (f) void onPhoto(f)
                  e.target.value = ''
                }}
              />
            </label>
          </Card>
          {scanError && <ErrorMessage error={new Error(scanError)} />}

          <Card className="space-y-2">
            <Label htmlFor="qr">Или вставьте строку из QR-кода</Label>
            <textarea
              id="qr"
              rows={3}
              value={qr}
              onChange={(e) => setQr(e.target.value)}
              className="w-full rounded-xl border border-slate-200 p-3 font-mono text-xs outline-none focus:border-brand-500"
              placeholder="t=20261025T1942&s=1245.50&fn=…"
            />
            <div className="flex gap-2">
              <Button variant="secondary" size="sm" onClick={() => setQr(SAMPLE_QR)}>
                <QrCode className="h-4 w-4" /> Пример
              </Button>
              <Button size="sm" className="flex-1" disabled={!qr || parse.isPending} onClick={() => parse.mutate(qr)}>
                Распознать
              </Button>
            </div>
          </Card>
          {parse.error && <ErrorMessage error={parse.error} />}
        </div>
      )}
    </div>
  )
}
