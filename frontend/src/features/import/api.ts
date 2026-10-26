import { useMutation } from '@tanstack/react-query'

import { useInvalidateFinance } from '@/api/hooks'
import { api, unwrap } from '@/api/client'
import type { ColumnMapping, ImportPreview, ImportResult, TransactionDraftOut } from '@/api/types'

export function useUploadStatement() {
  return useMutation({
    mutationFn: ({ file, mapping }: { file: File; mapping?: ColumnMapping }) => {
      const form = new FormData()
      form.append('file', file)
      if (mapping) form.append('mapping', JSON.stringify(mapping))
      return unwrap<ImportPreview>(
        api.POST('/imports/statement', {
          // multipart: отдаём FormData как есть
          body: form as unknown as { file: string },
          bodySerializer: (b) => b as unknown as FormData,
        }),
      )
    },
  })
}

export function useConfirmImport() {
  const invalidate = useInvalidateFinance()
  return useMutation({
    mutationFn: ({ jobId, accountId, newAccountName }: { jobId: number; accountId?: number; newAccountName?: string }) =>
      unwrap<ImportResult>(
        api.POST('/imports/{job_id}/confirm', {
          params: { path: { job_id: jobId } },
          body: { account_id: accountId ?? null, new_account_name: newAccountName ?? null },
        }),
      ),
    onSuccess: invalidate,
  })
}

export function useParseScreenshot() {
  return useMutation({
    mutationFn: (file: File) => {
      const form = new FormData()
      form.append('file', file)
      return unwrap<TransactionDraftOut>(
        api.POST('/imports/receipt/image', {
          body: form as unknown as { file: string },
          bodySerializer: (b) => b as unknown as FormData,
        }),
      )
    },
  })
}
