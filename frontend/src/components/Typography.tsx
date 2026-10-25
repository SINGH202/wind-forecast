import type { ReactNode } from 'react'

type Variant =
  'h1' | 'h2' | 'h3' | 'bodyMedium' | 'small' | 'li' | 'button' | 'link'

const tagByVariant = {
  h1: 'h1',
  h2: 'h2',
  h3: 'h3',
  bodyMedium: 'p',
  small: 'small',
  li: 'li',
  button: 'span',
  link: 'span',
} as const

const styleByVariant: Record<Variant, string> = {
  h1: 'text-xl font-semibold tracking-tight text-ink',
  h2: 'text-base font-semibold text-ink',
  h3: 'text-2xl font-semibold tabular-nums text-ink',
  bodyMedium: 'text-sm leading-6 text-ink',
  small: 'text-xs leading-5 text-muted',
  li: 'text-sm leading-6 text-ink',
  button: 'text-sm font-medium',
  link: 'text-sm font-medium text-forecast underline',
}

type TypographyProps = {
  variant: Variant
  className?: string
  children: ReactNode
  id?: string
}

export function Typography({
  variant,
  className,
  children,
  id,
}: TypographyProps) {
  const Tag = tagByVariant[variant]
  const classes = [styleByVariant[variant], className].filter(Boolean).join(' ')
  return (
    <Tag id={id} className={classes}>
      {children}
    </Tag>
  )
}
