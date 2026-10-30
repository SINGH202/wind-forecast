import { color } from './tokens.ts'

const controlBase = `w-full max-w-full rounded-md border border-line bg-paper py-1 text-sm text-ink sm:w-auto ${color.focus}`

/** Shared control chrome for date inputs and other plain fields. */
export const fieldClass = `${controlBase} px-2`

/**
 * Native arrow is hidden. Chevron is drawn by SelectField at right-2 so the
 * inset matches pl-2 on the left.
 */
export const selectClass = `${controlBase} appearance-none pl-2 pr-7`
