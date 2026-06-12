import { formatCurrency, formatDistance } from "../lib/marketMap";

export default function SelectedListingCard({ listing }) {
  if (!listing) {
    return (
      <aside className="detail-card detail-card--empty">
        <div className="detail-card__placeholder">Pick a node to inspect a listing.</div>
      </aside>
    );
  }

  return (
    <aside className="detail-card">
      {listing.image_url ? (
        <img className="detail-card__image" src={listing.image_url} alt={listing.address} />
      ) : (
        <div className="detail-card__image detail-card__image--placeholder">No Zillow photo</div>
      )}

      <div className="detail-card__body">
        <span className="detail-card__eyebrow">Selected listing</span>
        <h2 className="detail-card__title">{listing.address}</h2>
        <div className="detail-card__price">{formatCurrency(listing.price)}</div>

        <div className="detail-card__chips">
          <span>{listing.beds} bd</span>
          <span>{listing.baths} ba</span>
          <span>{listing.area} sq ft</span>
        </div>

        <p className="detail-card__distance">
          {formatDistance(listing.distance_from_northwestern_tech)}
        </p>

        <a className="detail-card__link" href={listing.url} target="_blank" rel="noreferrer">
          View on Zillow
        </a>
      </div>
    </aside>
  );
}
