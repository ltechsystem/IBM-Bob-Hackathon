/**
 * RivalsLogo — geometric 'R' emblem with networking nodes and </> code bracket.
 *
 * Design spec:
 *   • Solid block 'R' (stem + top bar + mid bar + bowl + diagonal leg)
 *   • Networking node cluster dissolving out of the right side of the R
 *   • </> code bracket rendered inside the R bowl's negative space
 *   • Gradient: cyan #06b6d4 → violet #818cf8 → indigo #6366f1 (diagonal)
 *   • Transparent background — works on any surface
 *
 * Each rendered instance uses a unique gradient ID derived from an
 * incrementing counter so multiple logos on the same page never clash.
 */

let _idCounter = 0

export interface RivalsLogoProps {
  /** Pixel size of the square bounding box. Default: 48 */
  size?: number
  className?: string
}

export default function RivalsLogo({ size = 48, className = '' }: RivalsLogoProps) {
  // Stable unique prefix per component instance (assigned once at render)
  const id = `rl${++_idCounter}`

  const grad    = `url(#${id}-g)`
  const gradLt  = `url(#${id}-gl)`

  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 100 100"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-label="Rivals"
      role="img"
      className={className}
    >
      <defs>
        {/* ── Primary gradient: cyan → violet → indigo ── */}
        <linearGradient id={`${id}-g`} x1="0" y1="0" x2="100" y2="100" gradientUnits="userSpaceOnUse">
          <stop offset="0%"   stopColor="#06b6d4" />
          <stop offset="52%"  stopColor="#818cf8" />
          <stop offset="100%" stopColor="#6366f1" />
        </linearGradient>

        {/* ── Light variant for secondary elements ── */}
        <linearGradient id={`${id}-gl`} x1="0" y1="0" x2="100" y2="100" gradientUnits="userSpaceOnUse">
          <stop offset="0%"   stopColor="#67e8f9" />
          <stop offset="100%" stopColor="#c7d2fe" />
        </linearGradient>
      </defs>

      {/* ── Subtle background tile ────────────────────────────────────── */}
      <rect width="100" height="100" rx="22" fill={grad} fillOpacity="0.09" />

      {/* ── Geometric R ──────────────────────────────────────────────── */}

      {/* Vertical stem */}
      <rect x="14" y="12" width="13" height="76" rx="3" fill={grad} />

      {/* Top bar */}
      <rect x="14" y="12" width="44" height="13" rx="3" fill={grad} />

      {/* Mid bar */}
      <rect x="14" y="43" width="40" height="12" rx="3" fill={grad} />

      {/* Bowl — right vertical of the R counter */}
      <rect x="44" y="12" width="13" height="44" rx="6.5" fill={grad} />

      {/* Diagonal leg */}
      <rect
        x="44" y="53"
        width="13" height="40"
        rx="3"
        fill={grad}
        transform="rotate(-21 44 53)"
      />

      {/* ── </> bracket inside the R bowl negative space ─────────────── */}
      <g
        stroke={gradLt}
        strokeWidth="2.8"
        strokeLinecap="round"
        strokeLinejoin="round"
        fill="none"
      >
        {/* < */}
        <polyline points="28,27 23,33 28,39" />
        {/* / */}
        <line x1="33" y1="40" x2="39" y2="26" />
        {/* > */}
        <polyline points="43,27 48,33 43,39" />
      </g>

      {/* ── Networking node structure ─────────────────────────────────── */}

      {/* Edge lines (drawn behind nodes) */}
      <g stroke={grad} strokeWidth="1.5" strokeLinecap="round" opacity="0.65">
        <line x1="72" y1="58" x2="87" y2="43" />
        <line x1="72" y1="58" x2="89" y2="73" />
        <line x1="72" y1="58" x2="91" y2="58" />
        <line x1="61" y1="75" x2="72" y2="58" />
      </g>

      {/* Hub — centre node */}
      <circle cx="72" cy="58" r="5.5" fill={grad} />

      {/* Outer satellite nodes */}
      <circle cx="87" cy="43" r="3.8" fill={gradLt} />
      <circle cx="89" cy="73" r="3.8" fill={gradLt} />
      <circle cx="91" cy="58" r="3.0" fill={gradLt} />

      {/* Leg-tip node — transition from letterform to network */}
      <circle cx="61" cy="75" r="3.2" fill={grad} opacity="0.55" />

      {/* ── Outer border ring ─────────────────────────────────────────── */}
      <rect
        x="1.5" y="1.5" width="97" height="97" rx="21"
        stroke={grad} strokeWidth="1.5" strokeOpacity="0.22"
        fill="none"
      />
    </svg>
  )
}
