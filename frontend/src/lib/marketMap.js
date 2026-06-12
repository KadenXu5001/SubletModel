export const BEDROOM_BUCKETS = [
  { key: "studio", label: "Studio", match: (beds) => Number(beds) === 0, color: "#d94b4b" },
  { key: "one", label: "1 bed", match: (beds) => Number(beds) === 1, color: "#4e2a84" },
  { key: "two", label: "2 bed", match: (beds) => Number(beds) === 2, color: "#d16ba5" },
  { key: "threePlus", label: "3+ bed", match: (beds) => Number(beds) >= 3, color: "#8e44ad" },
];

export function bucketBedrooms(beds) {
  return BEDROOM_BUCKETS.find((bucket) => bucket.match(beds)) ?? BEDROOM_BUCKETS.at(-1);
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
