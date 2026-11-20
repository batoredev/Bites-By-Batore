// Brand marks and dot effects from the Bites promo.
// The logo files live in public/brand and are painted with CSS masks
// (.logo-star, .logo-batore), so the surrounding colour decides the palette.

const RING_DOTS = 12;

// Twelve dots on a clock face; each lights up in turn (see .dot-ring in style.css).
export function DotRing({ size = 24 }: { size?: number }) {
  return (
    <svg
      className="dot-ring"
      width={size}
      height={size}
      viewBox="-12 -12 24 24"
      aria-hidden="true"
      focusable="false"
    >
      {Array.from({ length: RING_DOTS }, (_, i) => {
        const a = (i / RING_DOTS) * 2 * Math.PI - Math.PI / 2;
        return (
          <circle
            key={i}
            cx={(9 * Math.cos(a)).toFixed(2)}
            cy={(9 * Math.sin(a)).toFixed(2)}
            r={i % 3 === 0 ? 2 : 1.4}
            fill="currentColor"
            style={{ animationDelay: `${(i / RING_DOTS) * 1.2}s` }}
          />
        );
      })}
    </svg>
  );
}

// Brand lockup used in the sidebar and on sign-in.
export function BrandLockup() {
  return (
    <>
      <span className="brand-mark">
        <span className="logo-star" aria-hidden="true" />
      </span>
      <div>
        Bites
        <span>
          by{" "}
          <span className="batore">
            <span className="logo-batore" role="img" aria-label="Batore" />
          </span>
        </span>
      </div>
    </>
  );
}
