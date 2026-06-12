import { BEDROOM_BUCKETS } from "../lib/marketMap";

export default function DistanceLegend() {
  return (
    <div className="legend">
      <span className="legend__label">Color by bedroom count</span>
      <div className="legend__items">
        {BEDROOM_BUCKETS.map((bucket) => (
          <div className="legend__item" key={bucket.key}>
            <span className="legend__swatch" style={{ backgroundColor: bucket.color }} />
            <span>{bucket.label}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
