import { startTransition, useState } from "react";
import DistanceLegend from "./components/DistanceLegend";
import MarketScatterPlot from "./components/MarketScatterPlot";
import SelectedListingCard from "./components/SelectedListingCard";
import TopBarForm from "./components/TopBarForm";
import { findClosestListing } from "./lib/marketMap";

const initialForm = {
  beds: "2",
  baths: "1",
  area: "850",
  address_query: "",
};

export default function App() {
  const [form, setForm] = useState(initialForm);
  const [marketMap, setMarketMap] = useState(null);
  const [selectedListing, setSelectedListing] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  function handleChange(event) {
    const { name, value } = event.target;
    setForm((current) => ({ ...current, [name]: value }));
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setLoading(true);
    setError("");

    try {
      const response = await fetch("/api/market-map", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(form),
      });
      const data = await response.json();
      if (!response.ok || data.error) {
        throw new Error(data.error || "Failed to load market map.");
      }

      const nextSelected = findClosestListing(data.target, data.listings, data.meta);

      startTransition(() => {
        setMarketMap(data);
        setSelectedListing(nextSelected);
      });
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="page">
      <TopBarForm form={form} onChange={handleChange} onSubmit={handleSubmit} loading={loading} />

      {error ? <div className="error-banner">{error}</div> : null}

      <main className="market-layout">
        <section className="market-panel">
          <div className="market-panel__header">
            <div>
              <span className="market-panel__eyebrow">Market map</span>
              <h2>See your target against real listings.</h2>
            </div>
            <DistanceLegend />
          </div>

          <MarketScatterPlot
            marketMap={marketMap}
            selectedListing={selectedListing}
            onSelectListing={setSelectedListing}
          />
        </section>

        <SelectedListingCard listing={selectedListing} />
      </main>
    </div>
  );
}
