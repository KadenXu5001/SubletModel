export default function TopBarForm({ form, onChange, onSubmit, loading }) {
  return (
    <form className="topbar" onSubmit={onSubmit}>
      <div className="topbar__brand">
        <span className="topbar__eyebrow">Northwestern Market Map</span>
        <h1 className="topbar__title">Wildcat Apartment finder</h1>
      </div>

      <div className="topbar__controls">
        <label className="control">
          <span>Beds</span>
          <input name="beds" type="number" min="0" step="1" value={form.beds} onChange={onChange} />
        </label>

        <label className="control">
          <span>Baths</span>
          <input name="baths" type="number" min="0" step="0.5" value={form.baths} onChange={onChange} />
        </label>

        <label className="control">
          <span>Square feet</span>
          <input name="area" type="number" min="0" step="1" value={form.area} onChange={onChange} />
        </label>

        <label className="control control--wide">
          <span>Address</span>
          <input
            name="address_query"
            type="text"
            placeholder="810 Clark St, Evanston, IL"
            value={form.address_query}
            onChange={onChange}
          />
        </label>

        <button className="topbar__button" type="submit" disabled={loading}>
          {loading ? "Mapping..." : "Map market"}
        </button>
      </div>
    </form>
  );
}
