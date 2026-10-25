/** Class names tied to the colours and spacing in tokens.css. */

export const color = {
  page: 'bg-surface text-ink',
  paper: 'bg-paper',
  muted: 'text-muted',
  line: 'border-line',
  actual: 'bg-actual',
  forecast: 'border-forecast',
  band: 'bg-band',
  danger: 'text-danger',
  focus:
    'focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-forecast',
} as const

export const space = {
  xs: 'gap-1',
  sm: 'gap-2',
  md: 'gap-4',
  lg: 'gap-6',
  pageX: 'px-4 sm:px-6',
  pageY: 'py-4 sm:py-6',
  stack: 'flex flex-col gap-4',
} as const

export const chart = {
  actual: 'Actual',
  forecast: 'Forecast',
  band: 'Uncertainty band',
} as const

/** Stroke colours for chart libraries. Same hex values as tokens.css. */
export const chartStroke = {
  actual: '#1c1917',
  forecast: '#1d4ed8',
  band: '#dbeafe',
  muted: '#57534e',
  grid: '#e4dfd4',
  paper: '#fffcf7',
} as const
