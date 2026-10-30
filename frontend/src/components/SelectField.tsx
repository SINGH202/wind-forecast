import type { SelectHTMLAttributes } from 'react'

import { selectClass } from '../design/fields.ts'

type SelectFieldProps = SelectHTMLAttributes<HTMLSelectElement>

/** Select with a chevron inset the same distance as the left text padding. */
export function SelectField({
  className,
  children,
  ...props
}: SelectFieldProps) {
  const classes = [selectClass, className].filter(Boolean).join(' ')
  return (
    <div className="relative inline-grid w-full max-w-full sm:w-auto">
      <select className={classes} {...props}>
        {children}
      </select>
      <span
        className="pointer-events-none absolute inset-y-0 right-2 flex items-center"
        aria-hidden="true"
      >
        <svg
          width="12"
          height="12"
          viewBox="0 0 12 12"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
          className="text-muted"
        >
          <path
            d="M3 4.5 6 7.5 9 4.5"
            stroke="currentColor"
            strokeWidth="1.5"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      </span>
    </div>
  )
}
