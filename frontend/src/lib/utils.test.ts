import { describe, expect, it } from 'vitest'

import { formatMoney } from './utils'

describe('formatMoney', () => {
  it('formats rubles without kopecks', () => {
    expect(formatMoney(45000.4).replace(/\s/g, ' ')).toBe('45 000 ₽')
  })
  it('adds plus sign for income when requested', () => {
    expect(formatMoney(1500, { sign: true }).startsWith('+')).toBe(true)
  })
})
