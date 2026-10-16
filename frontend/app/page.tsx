
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
  "Reports",
];

type Company = {
  id: number;
  name: string;
  legal_name: string | null;
  description: string | null;
  website: string | null;
  created_at: string;
  updated_at: string;
};

type Recruiter = {
  id: number;
  name: string;
  email: string | null;
  phone: string | null;
  company_name: string | null;
  profile_url: string | null;
  description: string | null;
  created_at: string;
  updated_at: string;
};

type Job = {
  id: number;
  job_url: string;
  title: string | null;
  company_name: string | null;
  description: string | null;
  created_at: string;
  updated_at: string;
};

type Message = {
  id: number;
  message_text: string;
  created_at: string;
  updated_at: string;
};

type Report = {
  id: number;
  report_type: string;
  target_value: string;
  description: string;
  status: string;
  created_at: string;
  updated_at: string;
};

type ReportListResponse = {
  items: Report[];
  total: number;
  limit: number;
  offset: number;
};

type SearchResponse = {
  status: string;
  search_type: string;
  query: string;
  message: string;
  companies?: Company[];
  recruiters?: Recruiter[];
  jobs?: Job[];
  messages?: Message[];
  reports?: Report[];
};

export default function Home() {
  const [searchType, setSearchType] = useState("Company");
  const [query, setQuery] = useState("");
  const [result, setResult] = useState<SearchResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const [reportType, setReportType] = useState("message");
  const [reportTarget, setReportTarget] = useState("");
  const [reportDescription, setReportDescription] = useState("");
  const [reportSubmitting, setReportSubmitting] = useState(false);
  const [reportSubmitMessage, setReportSubmitMessage] = useState("");
  const [reportError, setReportError] = useState("");

  async function handleAnalyze() {
    if (!query.trim() && searchType !== "Reports") {
      return;
    }

    setLoading(true);
    setError("");
    setResult(null);

    try {
      if (searchType === "Reports") {
        const params = new URLSearchParams({
          limit: "20",
          offset: "0",
        });

        if (query.trim()) {
          params.set("search", query.trim());
        }

        const response = await fetch(
          `http://127.0.0.1:8000/api/reports?${params.toString()}`
        );

        if (!response.ok) {
          throw new Error("Report search failed.");
        }

        const data: ReportListResponse = await response.json();

        setResult({
          status: "success",
          search_type: "Reports",
          query: query.trim() || "All reports",
          message:
            data.total > 0
              ? `${data.total} report${data.total === 1 ? "" : "s"} found.`
              : "No matching reports found.",
          reports: data.items,
        });

        return;
      }

      if (searchType === "Company") {
        const response = await fetch(
          `http://127.0.0.1:8000/api/companies?search=${encodeURIComponent(
            query.trim()
          )}&limit=20&offset=0`
        );

        if (!response.ok) {
          throw new Error("Company search failed.");
        }

        const data = await response.json();

        setResult({
          status: "success",
          search_type: searchType,
          query: query.trim(),
          message:
            data.total > 0
              ? `${data.total} company result${
                  data.total === 1 ? "" : "s"
                } found.`
              : "No matching companies found.",
          companies: data.items,
        });

        return;
      }

      if (searchType === "Recruiter") {
        const response = await fetch(
          `http://127.0.0.1:8000/api/recruiters?search=${encodeURIComponent(
            query.trim()
          )}&limit=20&offset=0`
        );

        if (!response.ok) {
          throw new Error("Recruiter search failed.");
        }

        const data = await response.json();

        setResult({
          status: "success",
          search_type: searchType,
          query: query.trim(),
          message:
            data.total > 0
              ? `${data.total} recruiter result${
                  data.total === 1 ? "" : "s"
                } found.`
              : "No matching recruiters found.",
          recruiters: data.items,
        });

        return;
      }

      if (searchType === "Phone") {
        const response = await fetch(
          `http://127.0.0.1:8000/api/phone-numbers?search=${encodeURIComponent(
            query.trim()
          )}&limit=20&offset=0`
        );

        if (!response.ok) {
          throw new Error("Phone search failed.");
        }

        const data = await response.json();

        setResult({
          status: "success",
          search_type: searchType,
          query: query.trim(),
          message:
            data.total > 0
              ? `${data.total} phone result${
                  data.total === 1 ? "" : "s"
                } found.`
              : "No matching phone numbers found.",
        });

        return;
      }

      if (searchType === "Email") {
        const response = await fetch(
          `http://127.0.0.1:8000/api/emails?search=${encodeURIComponent(
            query.trim()
          )}&limit=20&offset=0`
        );

        if (!response.ok) {
          throw new Error("Email search failed.");
        }

        const data = await response.json();

        setResult({
          status: "success",
          search_type: searchType,
          query: query.trim(),
          message:
            data.total > 0
              ? `${data.total} email result${
                  data.total === 1 ? "" : "s"
                } found.`
              : "No matching email addresses found.",
        });

        return;
      }

      if (searchType === "Website") {
        const response = await fetch(
          `http://127.0.0.1:8000/api/websites?search=${encodeURIComponent(
            query.trim()
          )}&limit=20&offset=0`
        );

        if (!response.ok) {
          throw new Error("Website search failed.");
        }

        const data = await response.json();

        setResult({
          status: "success",
          search_type: searchType,
          query: query.trim(),
          message:
            data.total > 0
              ? `${data.total} website result${
                  data.total === 1 ? "" : "s"
                } found.`
              : "No matching websites found.",
        });

        return;
      }

      if (searchType === "Job URL") {
        const response = await fetch(
          `http://127.0.0.1:8000/api/jobs?search=${encodeURIComponent(
            query.trim()
          )}&limit=20&offset=0`
        );

        if (!response.ok) {
          throw new Error("Job URL search failed.");
        }

        const data = await response.json();

        setResult({
          status: "success",
          search_type: searchType,
          query: query.trim(),
          message:
            data.total > 0
              ? `${data.total} job result${
                  data.total === 1 ? "" : "s"
                } found.`
              : "No matching job URLs found.",
          jobs: data.items,
        });

        return;
      }

      if (searchType === "Message") {
        const response = await fetch(
          `http://127.0.0.1:8000/api/messages?search=${encodeURIComponent(
            query.trim()
          )}&limit=20&offset=0`
        );

        if (!response.ok) {
          throw new Error("Message search failed.");
        }

        const data = await response.json();

        setResult({
          status: "success",
          search_type: searchType,
          query: query.trim(),
          message:
            data.total > 0
              ? `${data.total} message result${
                  data.total === 1 ? "" : "s"
                } found.`
              : "No matching messages found.",
          messages: data.items,
        });

        return;
      }

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

  async function handleSubmitReport() {
    if (!reportTarget.trim() || !reportDescription.trim()) {
      setReportError("Please complete the target value and description.");
      setReportSubmitMessage("");
      return;
    }

    setReportSubmitting(true);
    setReportError("");
    setReportSubmitMessage("");

    try {
      const response = await fetch("http://127.0.0.1:8000/api/reports", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          report_type: reportType,
          target_value: reportTarget.trim(),
          description: reportDescription.trim(),
        }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => null);
        const detail =
          typeof errorData?.detail === "string"
            ? errorData.detail
            : "Report submission failed. Please check your details and try again.";
        throw new Error(detail);
      }

      const createdReport: Report = await response.json();
      setReportSubmitMessage(
        `Report #${createdReport.id} submitted successfully. Current status: ${createdReport.status}.`
      );
      setReportTarget("");
      setReportDescription("");

      // Refresh the visible report results after a successful submission.
      if (searchType === "Reports") {
        const params = new URLSearchParams({ limit: "20", offset: "0" });
        if (query.trim()) {
          params.set("search", query.trim());
        }
        const listResponse = await fetch(
          `http://127.0.0.1:8000/api/reports?${params.toString()}`
        );
        if (listResponse.ok) {
          const data: ReportListResponse = await listResponse.json();
          setResult({
            status: "success",
            search_type: "Reports",
            query: query.trim() || "All reports",
            message:
              data.total > 0
                ? `${data.total} report${data.total === 1 ? "" : "s"} found.`
                : "No matching reports found.",
            reports: data.items,
          });
        }
      }
    } catch (caughtError) {
      setReportError(
        caughtError instanceof Error
          ? caughtError.message
          : "Report submission failed. Please try again."
      );
    } finally {
      setReportSubmitting(false);
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

          {searchType === "Reports" && (
            <div className="mt-8 rounded-xl border border-slate-800 bg-slate-950 p-5 sm:p-6">
              <h3 className="text-lg font-semibold">Submit a report</h3>
              <p className="mt-2 text-sm leading-6 text-slate-400">
                Submit factual details about a job, recruiter, company, website,
                contact detail, or message you are concerned about. A submitted
                report is an allegation for review, not proof of wrongdoing.
              </p>

              <div className="mt-5">
                <label htmlFor="report-type" className="mb-2 block text-sm font-medium text-slate-300">
                  Report category
                </label>
                <select
                  id="report-type"
                  value={reportType}
                  onChange={(event) => setReportType(event.target.value)}
                  className="w-full rounded-xl border border-slate-700 bg-slate-900 px-4 py-3 text-white outline-none focus:border-blue-500"
                >
                  <option value="company">Company</option>
                  <option value="recruiter">Recruiter</option>
                  <option value="phone">Phone number</option>
                  <option value="email">Email address</option>
                  <option value="website">Website</option>
                  <option value="job">Job URL / listing</option>
                  <option value="internship">Internship</option>
                  <option value="message">Message / job offer</option>
                  <option value="other">Other</option>
                </select>
              </div>

              <div className="mt-4">
                <label htmlFor="report-target" className="mb-2 block text-sm font-medium text-slate-300">
                  Target value
                </label>
                <textarea
                  id="report-target"
                  value={reportTarget}
                  onChange={(event) => setReportTarget(event.target.value)}
                  placeholder="Company name, recruiter contact, URL, or suspicious message..."
                  rows={3}
                  maxLength={1000}
                  className="w-full resize-y rounded-xl border border-slate-700 bg-slate-900 px-4 py-3 text-white outline-none placeholder:text-slate-600 focus:border-blue-500"
                />
                <p className="mt-1 text-right text-xs text-slate-500">{reportTarget.length}/1000</p>
              </div>

              <div className="mt-4">
                <label htmlFor="report-description" className="mb-2 block text-sm font-medium text-slate-300">
                  Description / what happened
                </label>
                <textarea
                  id="report-description"
                  value={reportDescription}
                  onChange={(event) => setReportDescription(event.target.value)}
                  placeholder="Describe what you observed, such as a request for a registration fee before employment."
                  rows={4}
                  className="w-full resize-y rounded-xl border border-slate-700 bg-slate-900 px-4 py-3 text-white outline-none placeholder:text-slate-600 focus:border-blue-500"
                />
              </div>

              {reportError && (
                <div role="alert" className="mt-4 rounded-xl border border-red-900 bg-red-950/40 p-4 text-sm text-red-300">
                  {reportError}
                </div>
              )}

              {reportSubmitMessage && (
                <div role="status" className="mt-4 rounded-xl border border-emerald-900 bg-emerald-950/30 p-4 text-sm text-emerald-300">
                  {reportSubmitMessage}
                </div>
              )}

              <button
                onClick={handleSubmitReport}
                disabled={reportSubmitting || !reportTarget.trim() || !reportDescription.trim()}
                className="mt-5 w-full rounded-xl bg-blue-500 px-5 py-3.5 font-semibold text-white transition hover:bg-blue-400 disabled:cursor-not-allowed disabled:opacity-40"
              >
                {reportSubmitting ? "Submitting report..." : "Submit report"}
              </button>
            </div>
          )}

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
              placeholder={
                searchType === "Reports"
                  ? "Optional: search reports by target or description. Leave blank to load recent reports."
                  : `Enter ${searchType.toLowerCase()} information...`
              }
              rows={searchType === "Message" ? 6 : 3}
              className="w-full resize-none rounded-xl border border-slate-700 bg-slate-950 px-4 py-4 text-white outline-none placeholder:text-slate-600 focus:border-blue-500"
            />
          </div>

          <button
            onClick={handleAnalyze}
            disabled={(!query.trim() && searchType !== "Reports") || loading}
            className="mt-5 w-full rounded-xl bg-blue-500 px-5 py-3.5 font-semibold text-white transition hover:bg-blue-400 disabled:cursor-not-allowed disabled:opacity-40"
          >
            {loading
              ? "Connecting to JobShield..."
              : searchType === "Reports"
                ? "Search / load reports"
                : "Analyze with JobShield"}
          </button>

          {error && (
            <div className="mt-6 rounded-xl border border-red-900 bg-red-950/40 p-5">
              <div className="text-sm font-semibold text-red-400">
                Connection error
              </div>

              <p className="mt-2 text-sm leading-6 text-red-300">{error}</p>
            </div>
          )}

          {result && (
            <div className="mt-6 rounded-xl border border-slate-700 bg-slate-950 p-5">
              <div className="text-sm font-medium text-slate-400">
                Search request
              </div>

              {result.companies?.map((company) => (
                <div
                  key={company.id}
                  className="mt-4 rounded-xl border border-slate-800 bg-slate-900 p-4"
                >
                  <div className="text-lg font-semibold text-white">
                    {company.name}
                  </div>

                  {company.legal_name && (
                    <div className="mt-1 text-sm text-slate-400">
                      {company.legal_name}
                    </div>
                  )}

                  {company.description && (
                    <p className="mt-3 text-sm leading-6 text-slate-300">
                      {company.description}
                    </p>
                  )}

                  {company.website && (
                    <p className="mt-3 text-sm text-blue-400">
                      {company.website}
                    </p>
                  )}
                </div>
              ))}

              {result.recruiters?.map((recruiter) => (
                <div
                  key={recruiter.id}
                  className="mt-4 rounded-xl border border-slate-800 bg-slate-900 p-4"
                >
                  <div className="text-lg font-semibold text-white">
                    {recruiter.name}
                  </div>

                  {recruiter.company_name && (
                    <div className="mt-1 text-sm text-slate-400">
                      Company: {recruiter.company_name}
                    </div>
                  )}

                  {recruiter.email && (
                    <div className="mt-3 text-sm text-slate-300">
                      Email: {recruiter.email}
                    </div>
                  )}

                  {recruiter.phone && (
                    <div className="mt-1 text-sm text-slate-300">
                      Phone: {recruiter.phone}
                    </div>
                  )}

                  {recruiter.profile_url && (
                    <div className="mt-3 text-sm text-blue-400">
                      Profile: {recruiter.profile_url}
                    </div>
                  )}

                  {recruiter.description && (
                    <p className="mt-3 text-sm leading-6 text-slate-300">
                      {recruiter.description}
                    </p>
                  )}
                </div>
              ))}

              {result.jobs?.map((job) => (
                <div
                  key={job.id}
                  className="mt-4 rounded-xl border border-slate-800 bg-slate-900 p-4"
                >
                  <div className="text-lg font-semibold text-white">
                    {job.title || "Job Listing"}
                  </div>

                  {job.company_name && (
                    <div className="mt-1 text-sm text-slate-400">
                      Company: {job.company_name}
                    </div>
                  )}

                  <div className="mt-3 break-all text-sm text-blue-400">
                    Job URL: {job.job_url}
                  </div>

                  {job.description && (
                    <p className="mt-3 text-sm leading-6 text-slate-300">
                      {job.description}
                    </p>
                  )}
                </div>
              ))}

              {result.messages?.map((message) => (
                <div
                  key={message.id}
                  className="mt-4 rounded-xl border border-slate-800 bg-slate-900 p-4"
                >
                  <div className="text-lg font-semibold text-white">
                    Message Result
                  </div>

                  <div className="mt-3 whitespace-pre-wrap break-words text-sm leading-6 text-slate-300">
                    {message.message_text}
                  </div>
                </div>
              ))}

              {result.reports?.map((report) => (
                <article
                  key={report.id}
                  className="mt-4 rounded-xl border border-slate-800 bg-slate-900 p-4"
                >
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div className="text-lg font-semibold text-white">
                      Report #{report.id} · {report.report_type}
                    </div>
                    <span className="rounded-full border border-amber-700/60 bg-amber-950/40 px-3 py-1 text-xs font-medium text-amber-300">
                      {report.status}
                    </span>
                  </div>
                  <p className="mt-3 break-words text-sm text-slate-200">
                    <span className="font-semibold text-slate-400">Target: </span>
                    {report.target_value}
                  </p>
                  <p className="mt-2 whitespace-pre-wrap break-words text-sm leading-6 text-slate-300">
                    {report.description}
                  </p>
                  <p className="mt-3 text-xs text-slate-500">
                    Submitted: {new Date(report.created_at).toLocaleString()}
                  </p>
                </article>
              ))}

              {result.search_type === "Phone" && (
                <div className="mt-4 rounded-xl border border-slate-800 bg-slate-900 p-4">
                  <div className="text-lg font-semibold text-white">
                    Phone Search
                  </div>

                  <div className="mt-2 text-sm text-slate-300">
                    Number: {result.query}
                  </div>

                  <div className="mt-3 text-sm text-slate-400">
                    {result.message}
                  </div>
                </div>
              )}

              {result.search_type === "Email" && (
                <div className="mt-4 rounded-xl border border-slate-800 bg-slate-900 p-4">
                  <div className="text-lg font-semibold text-white">
                    Email Search
                  </div>

                  <div className="mt-2 text-sm text-slate-300">
                    Email: {result.query}
                  </div>

                  <div className="mt-3 text-sm text-slate-400">
                    {result.message}
                  </div>
                </div>
              )}

              {result.search_type === "Website" && (
                <div className="mt-4 rounded-xl border border-slate-800 bg-slate-900 p-4">
                  <div className="text-lg font-semibold text-white">
                    Website Search
                  </div>

                  <div className="mt-2 text-sm text-slate-300">
                    Website: {result.query}
                  </div>

                  <div className="mt-3 text-sm text-slate-400">
                    {result.message}
                  </div>
                </div>
              )}

              {result.search_type === "Job URL" && (
                <div className="mt-4 rounded-xl border border-slate-800 bg-slate-900 p-4">
                  <div className="text-lg font-semibold text-white">
                    Job URL Search
                  </div>

                  <div className="mt-2 break-all text-sm text-slate-300">
                    URL: {result.query}
                  </div>

                  <div className="mt-3 text-sm text-slate-400">
                    {result.message}
                  </div>
                </div>
              )}

              {result.search_type === "Message" && (
                <div className="mt-4 rounded-xl border border-slate-800 bg-slate-900 p-4">
                  <div className="text-lg font-semibold text-white">
                    Message Search
                  </div>

                  <div className="mt-2 whitespace-pre-wrap break-words text-sm leading-6 text-slate-300">
                    Message: {result.query}
                  </div>

                  <div className="mt-3 text-sm text-slate-400">
                    {result.message}
                  </div>
                </div>
              )}

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
