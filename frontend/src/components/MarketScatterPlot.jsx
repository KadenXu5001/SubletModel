import { useEffect, useMemo, useState } from "react";
import {
  CartesianGrid,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { bucketBedrooms, formatCurrency } from "../lib/marketMap";

function clampDomain(nextDomain, fullDomain) {
  const [fullMin, fullMax] = fullDomain;
  let [nextMin, nextMax] = nextDomain;

  const span = nextMax - nextMin;
  const fullSpan = fullMax - fullMin;

  if (span >= fullSpan) {
    return [...fullDomain];
  }

  if (nextMin < fullMin) {
    nextMax += fullMin - nextMin;
    nextMin = fullMin;
  }

  if (nextMax > fullMax) {
    nextMin -= nextMax - fullMax;
    nextMax = fullMax;
  }

  return [Math.max(fullMin, nextMin), Math.min(fullMax, nextMax)];
}

function zoomAxis(domain, fullDomain, center, factor) {
  const [currentMin, currentMax] = domain;
  const currentSpan = currentMax - currentMin;
  const nextSpan = currentSpan * factor;
  const safeCenter = Math.min(currentMax, Math.max(currentMin, center));
  const ratio = currentSpan === 0 ? 0.5 : (safeCenter - currentMin) / currentSpan;
  const nextMin = safeCenter - nextSpan * ratio;
  const nextMax = safeCenter + nextSpan * (1 - ratio);
  return clampDomain([nextMin, nextMax], fullDomain);
}

function ListingDot({ cx, cy, payload, onSelect, selectedId }) {
  const bucket = bucketBedrooms(payload.beds);
  const isSelected = payload.id === selectedId;

  return (
    <circle
      cx={cx}
      cy={cy}
      r={isSelected ? 8 : 6}
      fill={bucket.color}
      stroke={isSelected ? "#f7f4fb" : "#281247"}
      strokeWidth={isSelected ? 3 : 1.5}
      style={{ cursor: "pointer" }}
      onClick={() => onSelect(payload)}
    />
  );
}

function TargetDot({ cx, cy }) {
  return (
    <g>
      <circle cx={cx} cy={cy} r={11} fill="#f5c24b" stroke="#341c59" strokeWidth={3} />
      <circle cx={cx} cy={cy} r={4} fill="#341c59" />
    </g>
  );
}

function CustomTooltip({ active, payload }) {
  if (!active || !payload?.length) {
    return null;
  }

  const node = payload[0].payload;
  const isTarget = node.id === "target";

  return (
    <div className="tooltip">
      <strong>{isTarget ? "Your target" : node.address}</strong>
      <span>{formatCurrency(node.price)}</span>
      <span>{node.beds} bd / {node.baths} ba</span>
      <span>{node.area} sq ft</span>
    </div>
  );
}

export default function MarketScatterPlot({ marketMap, selectedListing, onSelectListing }) {
  const [xDomain, setXDomain] = useState(null);
  const [yDomain, setYDomain] = useState(null);
  const [zoomHistory, setZoomHistory] = useState([]);

  const fullDomains = useMemo(() => {
    if (!marketMap) {
      return null;
    }
    return {
      x: [...marketMap.meta.x_domain],
      y: [...marketMap.meta.y_domain],
    };
  }, [marketMap]);

  useEffect(() => {
    if (!fullDomains) {
      return;
    }
    setXDomain(fullDomains.x);
    setYDomain(fullDomains.y);
    setZoomHistory([]);
  }, [fullDomains]);

  if (!marketMap || !fullDomains || !xDomain || !yDomain) {
    return <div className="chart-empty">Run a query to plot the Evanston market.</div>;
  }

  const { listings, target } = marketMap;
  const focusNode = selectedListing ?? target;
  const canZoomOut = zoomHistory.length > 0;

  function applyZoom(factor) {
    const nextX = zoomAxis(xDomain, fullDomains.x, focusNode.area, factor);
    const nextY = zoomAxis(yDomain, fullDomains.y, focusNode.price, factor);

    if (
      nextX[0] === xDomain[0] &&
      nextX[1] === xDomain[1] &&
      nextY[0] === yDomain[0] &&
      nextY[1] === yDomain[1]
    ) {
      return;
    }

    setZoomHistory((current) => [...current, { xDomain, yDomain }]);
    setXDomain(nextX);
    setYDomain(nextY);
  }

  function handleZoomIn() {
    applyZoom(0.7);
  }

  function handleZoomOut() {
    if (zoomHistory.length === 0) {
      return;
    }

    const previous = zoomHistory[zoomHistory.length - 1];
    setZoomHistory((current) => current.slice(0, -1));
    setXDomain(previous.xDomain);
    setYDomain(previous.yDomain);
  }

  function handleReset() {
    setXDomain(fullDomains.x);
    setYDomain(fullDomains.y);
    setZoomHistory([]);
  }

  function handleWheel(event) {
    event.preventDefault();
    if (event.deltaY < 0) {
      handleZoomIn();
    } else {
      handleZoomOut();
    }
  }

  return (
    <div className="chart-shell">
      <div className="chart-toolbar">
        <div className="chart-toolbar__hint">Scroll to zoom. Click a node to inspect it.</div>
        <div className="chart-toolbar__actions">
          <button
            className="chart-toolbar__button chart-toolbar__button--ghost"
            type="button"
            onClick={handleReset}
            disabled={!canZoomOut}
          >
            Reset
          </button>
        </div>
      </div>

      <div className="chart-canvas" onWheel={handleWheel}>
        <ResponsiveContainer width="100%" height={520}>
          <ScatterChart margin={{ top: 20, right: 20, bottom: 24, left: 12 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(78,42,132,0.12)" />
            <XAxis
              type="number"
              dataKey="area"
              name="Square Footage"
              domain={xDomain}
              tickLine={false}
              axisLine={false}
              tick={{ fill: "#5a4a79", fontSize: 12 }}
              label={{ value: "Square Footage", position: "insideBottom", offset: -8, fill: "#5a4a79" }}
            />
            <YAxis
              type="number"
              dataKey="price"
              name="Price"
              domain={yDomain}
              tickLine={false}
              axisLine={false}
              tick={{ fill: "#5a4a79", fontSize: 12 }}
              tickFormatter={(value) => `$${Math.round(value / 100) / 10}k`}
              label={{ value: "Monthly Rent", angle: -90, position: "insideLeft", fill: "#5a4a79" }}
            />
            <Tooltip content={<CustomTooltip />} cursor={{ stroke: "rgba(78,42,132,0.18)" }} />
            <Scatter
              data={listings}
              shape={(props) => (
                <ListingDot
                  {...props}
                  selectedId={selectedListing?.id}
                  onSelect={onSelectListing}
                />
              )}
            />
            <Scatter data={[target]} shape={<TargetDot />} />
          </ScatterChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
