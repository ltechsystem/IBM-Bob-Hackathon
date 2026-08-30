/**
 * StatusIcon — inline SVG icons for test pass / fail / warning states.
 * Uses /icons/ public assets via <img> with proper alt + aria-hidden.
 *
 * BobAvatar — the Bob Debug Agent persona icon.
 */

// ---------------------------------------------------------------------------
// StatusIcon
// ---------------------------------------------------------------------------

export type StatusIconKind = 'success' | 'failure' | 'warning'

const ICON_SRC: Record<StatusIconKind, string> = {
  success: '/icons/status-success.svg',
  failure: '/icons/status-failure.svg',
  warning: '/icons/status-warning.svg',
}

const ICON_ALT: Record<StatusIconKind, string> = {
  success: 'Test passed',
  failure: 'Test failed',
  warning: 'Confidence gate warning',
}

export interface StatusIconProps {
  kind: StatusIconKind
  /** Tailwind size class pair, default "h-4 w-4" */
  size?: string
  /** When true the icon is purely decorative — hides from screen readers */
  decorative?: boolean
}

export function StatusIcon({ kind, size = 'h-4 w-4', decorative = false }: StatusIconProps) {
  return (
    <img
      src={ICON_SRC[kind]}
      alt={decorative ? '' : ICON_ALT[kind]}
      aria-hidden={decorative ? true : undefined}
      width={20}
      height={20}
      className={`${size} shrink-0 select-none`}
      style={{ display: 'inline-block' }}
    />
  )
}

// ---------------------------------------------------------------------------
// BobAvatar
// ---------------------------------------------------------------------------

export interface BobAvatarProps {
  size?: string
}

export function BobAvatar({ size = 'h-8 w-8' }: BobAvatarProps) {
  return (
    <img
      src="/icons/agent-bob-avatar.svg"
      alt="Bob Debug Agent"
      width={40}
      height={40}
      className={`${size} shrink-0 rounded-full`}
      style={{ display: 'inline-block' }}
    />
  )
}
