export const DISTANCE_BUCKETS = [
  { key: "near", label: "< 0.75 mi", max: 0.75, color: "#4e2a84" },
  { key: "walk", label: "0.75 - 1.5 mi", max: 1.5, color: "#6f54a5" },
  { key: "ride", label: "1.5 - 2.5 mi", max: 2.5, color: "#8f78bc" },
  { key: "far", label: "2.5+ mi", max: Number.POSITIVE_INFINITY, color: "#b7a4dc" },
];

export function bucketDistance(distance) {
  return DISTANCE_BUCKETS.find((bucket) => distance <= bucket.max) ?? DISTANCE_BUCKETS.at(-1);
}

export function formatCurrency(value) {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(value);
}

export function formatDistance(value) {
  return `${Number(value).toFixed(1)} mi from Northwestern Tech`;
}

export function findClosestListing(target, listings, meta) {
  if (!target || !listings?.length) {
    return null;
  }

  const spans = {
    beds: 4,
    baths: 3,
    area: Math.max(1, meta?.x_domain?.[1] - meta?.x_domain?.[0] || 1),
    distance_from_northwestern_tech: Math.max(
      0.5,
      meta?.distance_range?.[1] - meta?.distance_range?.[0] || 0.5
    ),
  };

  let bestListing = listings[0];
  let bestScore = Number.POSITIVE_INFINITY;

  for (const listing of listings) {
    const score =
      Math.abs((listing.beds ?? target.beds) - target.beds) / spans.beds +
      Math.abs((listing.baths ?? target.baths) - target.baths) / spans.baths +
      Math.abs((listing.area ?? target.area) - target.area) / spans.area +
      Math.abs(
        (listing.distance_from_northwestern_tech ?? target.distance_from_northwestern_tech) -
          target.distance_from_northwestern_tech
      ) /
        spans.distance_from_northwestern_tech;

    if (score < bestScore) {
      bestScore = score;
      bestListing = listing;
    }
  }

  return bestListing;
}
