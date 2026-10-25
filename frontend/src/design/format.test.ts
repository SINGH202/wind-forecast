import { expect, test } from 'vitest'

import { formatHours, formatMwh, formatMw, formatPercent } from './format.ts'

test('megawatts use thousands separators and no decimal places', () => {
  expect(formatMw(2127.482)).toBe('2,127')
  expect(formatMw(1851.528, true)).toBe('+1,852')
  expect(formatMw(-426.4, true)).toBe('-426')
  expect(formatMw(null)).toBe('—')
})

test('megawatt-hours use the same whole-number format', () => {
  expect(formatMwh(88618.6)).toBe('88,619')
  expect(formatMwh(null)).toBe('—')
})

test('percentages keep one decimal place', () => {
  expect(formatPercent(0.1837)).toBe('18.4')
  expect(formatPercent(0.1)).toBe('10.0')
  expect(formatPercent(null)).toBe('—')
})

test('hours keep one decimal place', () => {
  expect(formatHours(1.5)).toBe('1.5')
  expect(formatHours(null)).toBe('—')
})
