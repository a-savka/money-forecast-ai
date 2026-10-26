import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { renderWithProviders } from '@/test/utils'

import { TransactionForm } from './TransactionForm'

beforeEach(() => {
  vi.stubGlobal('fetch', vi.fn(async () => new Response('[]', { status: 200, headers: { 'Content-Type': 'application/json' } })))
})

describe('TransactionForm', () => {
  it('enables submit only after a positive amount is entered', async () => {
    renderWithProviders(<TransactionForm onDone={() => {}} />)
    const submit = screen.getByRole('button', { name: 'Добавить' })
    expect(submit).toBeDisabled()
    await userEvent.type(screen.getByLabelText('Сумма, ₽'), '450')
    expect(submit).toBeEnabled()
  })

  it('prefills an existing income transaction', () => {
    renderWithProviders(
      <TransactionForm
        onDone={() => {}}
        transaction={{
          id: 1,
          account_id: 1,
          date: '2026-10-10',
          amount: 52000,
          description: 'Зарплата',
          merchant: null,
          mcc: null,
          category_id: null,
          category_source: 'user',
          source: 'manual',
          is_recurring: true,
        }}
      />,
    )
    expect(screen.getByLabelText('Сумма, ₽')).toHaveValue('52000')
    expect(screen.getByRole('button', { name: 'Сохранить' })).toBeEnabled()
  })
})
