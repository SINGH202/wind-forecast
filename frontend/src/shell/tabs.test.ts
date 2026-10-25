import { expect, test } from 'vitest'

import { tabFromHash } from './tabs.ts'

test('hash names map to the three desk tabs', () => {
  expect(tabFromHash('#decision')).toBe('decision')
  expect(tabFromHash('#explorer')).toBe('explorer')
  expect(tabFromHash('accuracy')).toBe('accuracy')
  expect(tabFromHash('#unknown')).toBe('decision')
  expect(tabFromHash('')).toBe('decision')
})
