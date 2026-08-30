/**
 * RivalsLogo — geometric 'R' emblem with networking nodes and </> code bracket.
 * Gradient: cyan (#06b6d4) → indigo (#6366f1).
 * Transparent background, perfectly balanced at any size.
 */
export interface RivalsLogoProps {
  size?: number
  className?: string
}

export default function RivalsLogo({ size = 48, className = '' }: RivalsLogoProps) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 100 100"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-label="Rivals logo"
      className={className}
    >
      <defs>
        {/* Primary cyan → indigo gradient (left to right) */}
        <linearGradient id="rl-grad" x1="0" y1="0" x2="100" y2="100" gradientUnits="userSpaceOnUse">
          <stop offset="0%"   stopColor="#06b6d4" />
          <stop offset="55%"  stopColor="#818cf8" />
          <stop offset="100%" stopColor="#6366f1" />
        </linearGradient>

        {/* Slightly lighter variant for node rings */}
        <linearGradient id="rl-grad-light" x1="0" y1="0" x2="100" y2="100" gradientUnits="userSpaceOnUse">
          <stop offset="0%"   stopColor="#67e8f9" />
          <stop offset="100%" stopColor="#a5b4fc" />
        </linearGradient>

        {/* Clip path that defines the overall emblem square */}
        <clipPath id="rl-clip">
          <rect x="0" y="0" width="100" height="100" rx="18" />
        </clipPath>
      </defs>

      {/* ── Background pill (very subtle, semi-transparent) ───────────── */}
      <rect x="0" y="0" width="100" height="100" rx="18"
            fill="url(#rl-grad)" fillOpacity="0.08" />

      {/*
        ── Geometric R body ─────────────────────────────────────────────
        Built from three solid rectangles:
          1. Vertical stem (left side)
          2. Top horizontal bar
          3. Mid horizontal bar
        The diagonal leg is a rotated rect.
        All filled with the gradient.
      */}

      {/* Stem — left vertical bar */}
      <rect x="14" y="12" width="14" height="76" rx="3" fill="url(#rl-grad)" />

      {/* Top bar — horizontal crossbar of R */}
      <rect x="14" y="12" width="42" height="13" rx="3" fill="url(#rl-grad)" />

      {/* Midbar — second horizontal crossbar of R */}
      <rect x="14" y="43" width="38" height="12" rx="3" fill="url(#rl-grad)" />

      {/* Bowl curve — right arc of R rendered as a filled rounded rect */}
      <rect x="42" y="12" width="14" height="44" rx="7" fill="url(#rl-grad)" />

      {/* Diagonal leg — the descending right stroke of R */}
      <rect
        x="43" y="52" width="13" height="42" rx="3"
        fill="url(#rl-grad)"
        transform="rotate(-22 43 52)"
      />

      {/*
        ── </> code bracket in the R negative space ─────────────────────
        Sits inside the bowl (upper-right counter of the R).
        Rendered as thin strokes using the light gradient.
      */}
      <g stroke="url(#rl-grad-light)" strokeWidth="2.6" strokeLinecap="round" strokeLinejoin="round" fill="none">
        {/* < */}
        <polyline points="29,28  24,33  29,38" />
        {/* / */}
        <line x1="33" y1="39" x2="38" y2="26" />
        {/* > */}
        <polyline points="41,28  46,33  41,38" />
      </g>

      {/*
        ── Networking node structure (right side) ────────────────────────
        Three nodes connected by thin lines, emanating from the R diagonal,
        giving the impression the letterform "dissolves" into a network.
      */}

      {/* Edge lines first (behind nodes) */}
      <g stroke="url(#rl-grad)" strokeWidth="1.4" strokeLinecap="round" opacity="0.7">
        {/* centre hub → top-right node */}
        <line x1="72" y1="60" x2="86" y2="44" />
        {/* centre hub → bottom-right node */}
        <line x1="72" y1="60" x2="88" y2="74" />
        {/* centre hub → mid-right node */}
        <line x1="72" y1="60" x2="90" y2="60" />
        {/* leg tip → centre hub */}
        <line x1="60" y1="76" x2="72" y2="60" />
      </g>

      {/* Centre hub node */}
      <circle cx="72" cy="60" r="5" fill="url(#rl-grad)" />

      {/* Outer nodes — filled ring style */}
      <circle cx="86" cy="44" r="3.5" fill="url(#rl-grad-light)" />
      <circle cx="88" cy="74" r="3.5" fill="url(#rl-grad-light)" />
      <circle cx="90" cy="60" r="2.8" fill="url(#rl-grad-light)" />

      {/* Leg-tip node */}
      <circle cx="60" cy="76" r="3" fill="url(#rl-grad)" opacity="0.6" />

      {/* ── Outer border ring (very subtle) ──────────────────────────── */}
      <rect x="1" y="1" width="98" height="98" rx="18"
            stroke="url(#rl-grad)" strokeWidth="1.5" strokeOpacity="0.25" fill="none" />
    </svg>
  )
}
