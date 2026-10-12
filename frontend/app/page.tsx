"use client";

import { useState } from "react";

const searchTypes = [
  "Company",
  "Recruiter",
  "Phone",
  "Email",
  "Website",
  "Job URL",
  "Message",
];

type SearchResponse = {
  status: string;
  search_type: string;
  query: string;
  message: string;
};

export default function Home() {
  const [searchType, setSearchType] = useState("Company");
  const [query, setQuery] = useState("");
  const [result, setResult] = useState<SearchResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleAnalyze() {
    if (!query.trim()) {
      return;
    }

    setLoading(true);
    setError("");
    setResult(null);

    try {
      const response = await fetch("http://127.0.0.1:8000/api/search", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          search_type: searchType,
          query: query.trim(),
        }),
      });

      if (!response.ok) {
        throw new Error("Search request failed.");
      }

      const data: SearchResponse = await response.json();

      setResult(data);
    } catch {
      setError(
        "Could not connect to the JobShield backend. Make sure the FastAPI server is running."
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="min-h-screen bg-slate-950 text-white">
      <div className="mx-auto flex min-h-screen max-w-5xl flex-col px-6 py-16">
        <header className="mb-16">
          <div className="mb-3 text-sm font-semibold tracking-widest text-blue-400">
            JOBSHIELD
          </div>

          <h1 className="max-w-3xl text-4xl font-bold tracking-tight sm:text-6xl">
            Check before you trust a job opportunity.
          </h1>

          <p className="mt-6 max-w-2xl text-lg leading-8 text-slate-400">
            Analyze recruiters, companies, job offers, websites and other
            recruitment information for potential warning signs.
          </p>
        </header>

        <section className="rounded-2xl border border-slate-800 bg-slate-900 p-6 shadow-2xl sm:p-8">
          <h2 className="text-xl font-semibold">
            What do you want to check?
          </h2>

          <p className="mt-2 text-sm text-slate-400">
            Select a type and provide the information you want JobShield to
            analyze.
          </p>

          <div className="mt-6 flex flex-wrap gap-2">
            {searchTypes.map((type) => (
              <button
                key={type}
                onClick={() => {
                  setSearchType(type);
                  setResult(null);
                  setError("");
                }}
                className={`rounded-full px-4 py-2 text-sm font-medium transition ${
                  searchType === type
                    ? "bg-blue-500 text-white"
                    : "bg-slate-800 text-slate-300 hover:bg-slate-700"
                }`}
              >
                {type}
              </button>
            ))}
          </div>

          <div className="mt-6">
            <label className="mb-2 block text-sm font-medium text-slate-300">
              {searchType}
            </label>

            <textarea
              value={query}
              onChange={(event) => {
                setQuery(event.target.value);
                setResult(null);
                setError("");
              }}
              placeholder={`Enter ${searchType.toLowerCase()} information...`}
              rows={searchType === "Message" ? 6 : 3}
              className="w-full resize-none rounded-xl border border-slate-700 bg-slate-950 px-4 py-4 text-white outline-none placeholder:text-slate-600 focus:border-blue-500"
            />
          </div>

          <button
            onClick={handleAnalyze}
            disabled={!query.trim() || loading}
            className="mt-5 w-full rounded-xl bg-blue-500 px-5 py-3.5 font-semibold text-white transition hover:bg-blue-400 disabled:cursor-not-allowed disabled:opacity-40"
          >
            {loading ? "Connecting to JobShield..." : "Analyze with JobShield"}
          </button>

          {error && (
            <div className="mt-6 rounded-xl border border-red-900 bg-red-950/40 p-5">
              <div className="text-sm font-semibold text-red-400">
                Connection error
              </div>

              <p className="mt-2 text-sm leading-6 text-red-300">
                {error}
              </p>
            </div>
          )}

          {result && (
            <div className="mt-6 rounded-xl border border-slate-700 bg-slate-950 p-5">
              <div className="text-sm font-medium text-slate-400">
                Search request
              </div>

              <div className="mt-2 text-lg font-semibold text-green-400">
                Request received successfully
              </div>

              <div className="mt-4 space-y-2 text-sm text-slate-300">
                <p>
                  <span className="font-semibold text-white">Type:</span>{" "}
                  {result.search_type}
                </p>

                <p>
                  <span className="font-semibold text-white">Query:</span>{" "}
                  {result.query}
                </p>

                <p className="pt-2 text-slate-400">{result.message}</p>
              </div>
            </div>
          )}
        </section>

        <section className="mt-12 grid gap-4 sm:grid-cols-3">
          <div className="rounded-xl border border-slate-800 p-5">
            <div className="font-semibold">Evidence first</div>
            <p className="mt-2 text-sm text-slate-400">
              JobShield should explain why a result receives its risk level.
            </p>
          </div>

          <div className="rounded-xl border border-slate-800 p-5">
            <div className="font-semibold">Unknown stays unknown</div>
            <p className="mt-2 text-sm text-slate-400">
              No reports does not automatically mean an opportunity is safe.
            </p>
          </div>

          <div className="rounded-xl border border-slate-800 p-5">
            <div className="font-semibold">Transparent analysis</div>
            <p className="mt-2 text-sm text-slate-400">
              Users should be able to understand the signals behind a result.
            </p>
          </div>
        </section>
      </div>
    </main>
  );
}