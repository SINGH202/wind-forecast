const mwFormat = new Intl.NumberFormat('en-GB', {
  maximumFractionDigits: 0,
  minimumFractionDigits: 0,
})

const percentFormat = new Intl.NumberFormat('en-GB', {
  minimumFractionDigits: 1,
  maximumFractionDigits: 1,
})

const hoursFormat = new Intl.NumberFormat('en-GB', {
  minimumFractionDigits: 1,
  maximumFractionDigits: 1,
})

function withSign(text: string, value: number, signed: boolean): string {
  if (signed && value > 0) {
    return `+${text}`
  }
  return text
}

export function formatMw(value: number | null, signed = false): string {
  if (value === null) {
    return '—'
  }
  return withSign(mwFormat.format(value), value, signed)
}

export function formatMwh(value: number | null): string {
  if (value === null) {
    return '—'
  }
  return mwFormat.format(value)
}

export function formatPercent(ratio: number | null): string {
  if (ratio === null) {
    return '—'
  }
  return percentFormat.format(ratio * 100)
}

export function formatHours(value: number | null): string {
  if (value === null) {
    return '—'
  }
  return hoursFormat.format(value)
}
