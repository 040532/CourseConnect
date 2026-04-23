import { useEffect, useMemo, useState } from "react";
import jsPDF from "jspdf";
import autoTable from "jspdf-autotable";

const API_BASE = "http://localhost:8000";
const SUGGESTED_QUERIES = [
  "deep learning for computer vision",
  "distributed cloud systems",
  "privacy in machine learning",
  "robotics and spatial intelligence",
  "cybersecurity data analytics",
  "computational biology and genomics",
];

const RESEARCH_LANES = [
  { label: "AI + Vision", query: "deep learning for computer vision" },
  { label: "Secure Systems", query: "security in distributed systems" },
  { label: "Cloud + Scale", query: "distributed cloud systems" },
  { label: "Robotics", query: "robotics and spatial intelligence" },
  { label: "Data + Health", query: "machine learning for healthcare" },
  { label: "Theory + Optimization", query: "optimization for machine learning" },
];

const initialFilters = {
  department: "",
  minCredits: "",
  maxCredits: "",
};

function scoreTone(score) {
  if (score >= 88) return "bg-tamu-maroon";
  if (score >= 75) return "bg-tamu-gold";
  return "bg-tamu-brick";
}

function scoreLabel(score) {
  if (score >= 90) return "Exceptional fit";
  if (score >= 80) return "Strong fit";
  if (score >= 70) return "Relevant";
  return "Broad match";
}

function extractTerms(query) {
  return [...new Set(query.toLowerCase().match(/[a-z0-9]+/g) || [])].filter((term) => term.length > 2);
}

function highlightText(text, query) {
  if (!query.trim()) return text;
  const terms = extractTerms(query);
  if (!terms.length) return text;

  const escapedTerms = terms.map((term) => term.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"));
  const pattern = new RegExp(`(${escapedTerms.join("|")})`, "ig");
  const parts = text.split(pattern);

  return parts.map((part, index) =>
    terms.includes(part.toLowerCase()) ? (
      <mark key={`${part}-${index}`} className="rounded bg-tamu-gold/35 px-1 text-tamu-ink">
        {part}
      </mark>
    ) : (
      <span key={`${part}-${index}`}>{part}</span>
    ),
  );
}

function parseCredits(credits) {
  const value = Number.parseFloat(credits || "");
  return Number.isFinite(value) ? value : null;
}

function getReadinessBadge(prerequisites) {
  const normalized = (prerequisites || "").trim();
  if (!normalized) {
    return { label: "Open access", tone: "bg-emerald-100 text-emerald-800" };
  }
  if (normalized.length > 90) {
    return { label: "Advanced prep", tone: "bg-amber-100 text-amber-800" };
  }
  return { label: "Some prep", tone: "bg-rose-100 text-rose-800" };
}

function buildQueryCoach(query) {
  const terms = extractTerms(query);
  if (!terms.length) {
    return "Try describing a problem area, method, or application domain rather than a single keyword.";
  }
  if (terms.length < 3) {
    return "Add one more detail such as an application area, method, or systems context to improve semantic ranking.";
  }
  return "Your query has strong intent signals. Use the filter button to narrow by department or credit load when needed.";
}

function summarizeFilters(filters) {
  const active = [];
  if (filters.department) active.push(filters.department);
  if (filters.minCredits) active.push(`min ${filters.minCredits} credits`);
  if (filters.maxCredits) active.push(`max ${filters.maxCredits} credits`);
  return active.length ? active.join(" | ") : "No filters applied";
}

function formatTimestamp() {
  return new Intl.DateTimeFormat("en-US", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date());
}

function wrapText(doc, text, x, y, width, options = {}) {
  const lines = doc.splitTextToSize(text || "", width);
  doc.text(lines, x, y, options);
  return y + lines.length * 6;
}

function downloadResultsPdf({ query, filters, results, searchMeta }) {
  if (!results.length) return;

  const doc = new jsPDF({ unit: "pt", format: "a4" });
  const maroon = [80, 0, 0];
  const gold = [214, 179, 95];
  const ink = [32, 23, 22];
  const slate = [104, 92, 88];
  const cream = [245, 237, 224];
  const pageWidth = doc.internal.pageSize.getWidth();
  const margin = 42;

  doc.setFillColor(...maroon);
  doc.rect(0, 0, pageWidth, 92, "F");

  doc.setTextColor(255, 255, 255);
  doc.setFont("helvetica", "bold");
  doc.setFontSize(24);
  doc.text("CourseConnect Search Report", margin, 42);
  doc.setFontSize(10);
  doc.setFont("helvetica", "normal");
  doc.text("Texas A&M inspired semantic course discovery", margin, 60);

  doc.setFillColor(...gold);
  doc.roundedRect(pageWidth - 190, 24, 148, 28, 14, 14, "F");
  doc.setTextColor(...maroon);
  doc.setFont("helvetica", "bold");
  doc.setFontSize(10);
  doc.text("Graduate Course Search", pageWidth - 176, 42);

  let y = 124;
  doc.setTextColor(...ink);
  doc.setFont("helvetica", "bold");
  doc.setFontSize(16);
  doc.text("Search Summary", margin, y);

  y += 18;
  doc.setFillColor(...cream);
  doc.roundedRect(margin, y, pageWidth - margin * 2, 92, 16, 16, "F");

  doc.setFont("helvetica", "bold");
  doc.setFontSize(11);
  doc.setTextColor(...maroon);
  doc.text("Query", margin + 18, y + 24);
  doc.text("Filters", margin + 18, y + 50);
  doc.text("Generated", margin + 18, y + 76);

  doc.setFont("helvetica", "normal");
  doc.setTextColor(...ink);
  doc.text(query, margin + 82, y + 24);
  doc.text(summarizeFilters(filters), margin + 82, y + 50);
  doc.text(formatTimestamp(), margin + 82, y + 76);

  y += 116;
  doc.setFont("helvetica", "bold");
  doc.setFontSize(15);
  doc.setTextColor(...ink);
  doc.text("Result Snapshot", margin, y);

  y += 18;
  autoTable(doc, {
    startY: y,
    margin: { left: margin, right: margin },
    head: [["Returned", "Threshold", "Top score", "Summary"]],
    body: [[
      `${results.length} / ${searchMeta?.max_results || 10}`,
      searchMeta?.applied_threshold ? `${searchMeta.applied_threshold}%` : "N/A",
      searchMeta?.top_score ? `${searchMeta.top_score}%` : "N/A",
      searchMeta?.message || "Semantic results generated for the current query.",
    ]],
    styles: {
      font: "helvetica",
      fontSize: 10,
      cellPadding: 8,
      textColor: slate,
      lineColor: [225, 215, 205],
      lineWidth: 0.5,
    },
    headStyles: {
      fillColor: maroon,
      textColor: [255, 255, 255],
      fontStyle: "bold",
    },
    bodyStyles: {
      fillColor: [255, 252, 248],
    },
  });

  y = doc.lastAutoTable.finalY + 24;
  doc.setFont("helvetica", "bold");
  doc.setFontSize(15);
  doc.setTextColor(...ink);
  doc.text("Courses Returned", margin, y);

  autoTable(doc, {
    startY: y + 12,
    margin: { left: margin, right: margin },
    head: [["Course", "Title", "Credits", "Score", "Prerequisite signal"]],
    body: results.map((result) => [
      result.code,
      result.title,
      result.credits || "-",
      `${result.score.toFixed(1)}%`,
      result.prerequisites?.trim() ? "Listed" : "None listed",
    ]),
    styles: {
      font: "helvetica",
      fontSize: 10,
      cellPadding: 8,
      textColor: ink,
      lineColor: [231, 223, 214],
      lineWidth: 0.5,
    },
    headStyles: {
      fillColor: [108, 26, 26],
      textColor: [255, 255, 255],
      fontStyle: "bold",
    },
    alternateRowStyles: {
      fillColor: [252, 248, 243],
    },
  });

  results.forEach((result, index) => {
    doc.addPage();
    doc.setFillColor(...maroon);
    doc.rect(0, 0, pageWidth, 74, "F");

    doc.setTextColor(255, 255, 255);
    doc.setFont("helvetica", "bold");
    doc.setFontSize(20);
    doc.text(`${index + 1}. ${result.code}`, margin, 38);
    doc.setFont("helvetica", "normal");
    doc.setFontSize(10);
    doc.text(`Semantic score: ${result.score.toFixed(1)}%`, margin, 56);

    let detailY = 108;
    doc.setTextColor(...ink);
    doc.setFont("helvetica", "bold");
    doc.setFontSize(18);
    detailY = wrapText(doc, result.title, margin, detailY, pageWidth - margin * 2);

    doc.setFillColor(...cream);
    doc.roundedRect(margin, detailY + 12, pageWidth - margin * 2, 54, 14, 14, "F");
    doc.setFont("helvetica", "bold");
    doc.setFontSize(10);
    doc.setTextColor(...maroon);
    doc.text("Department", margin + 16, detailY + 34);
    doc.text("Credits", margin + 176, detailY + 34);
    doc.text("Prerequisites", margin + 286, detailY + 34);
    doc.setFont("helvetica", "normal");
    doc.setTextColor(...ink);
    doc.text(result.department || "-", margin + 16, detailY + 50);
    doc.text(result.credits || "-", margin + 176, detailY + 50);
    doc.text(result.prerequisites?.trim() ? "Listed below" : "None listed", margin + 286, detailY + 50);

    detailY += 92;
    doc.setTextColor(...ink);
    doc.setFont("helvetica", "bold");
    doc.setFontSize(13);
    doc.text("Description", margin, detailY);
    doc.setFont("helvetica", "normal");
    doc.setFontSize(11);
    detailY = wrapText(doc, result.description || "No description available.", margin, detailY + 18, pageWidth - margin * 2);

    detailY += 16;
    doc.setFont("helvetica", "bold");
    doc.setFontSize(13);
    doc.text("Prerequisites", margin, detailY);
    doc.setFont("helvetica", "normal");
    doc.setFontSize(11);
    wrapText(
      doc,
      result.prerequisites?.trim() || "No prerequisites listed in the catalog entry.",
      margin,
      detailY + 18,
      pageWidth - margin * 2,
    );

    doc.setDrawColor(...gold);
    doc.setLineWidth(2);
    doc.line(margin, doc.internal.pageSize.getHeight() - 42, pageWidth - margin, doc.internal.pageSize.getHeight() - 42);
    doc.setFontSize(9);
    doc.setTextColor(...slate);
    doc.text(`Generated by CourseConnect on ${formatTimestamp()}`, margin, doc.internal.pageSize.getHeight() - 26);
  });

  const safeQuery = (query || "course-search").replace(/[^a-z0-9]+/gi, "-").replace(/^-|-$/g, "").toLowerCase();
  doc.save(`courseconnect-${safeQuery || "course-search"}.pdf`);
}

function StatCard({ label, value, note, accent = "maroon" }) {
  const accentClass = {
    maroon: "text-tamu-maroon",
    gold: "text-tamu-gold-dark",
    ink: "text-tamu-ink",
  }[accent] || "text-tamu-maroon";

  return (
    <div className="panel rounded-3xl border border-white/60 p-5 shadow-panel">
      <div className="text-xs uppercase tracking-[0.24em] text-tamu-muted">{label}</div>
      <div className={`mt-3 text-3xl font-semibold ${accentClass}`}>{value}</div>
      <div className="mt-1 text-sm text-tamu-slate">{note}</div>
    </div>
  );
}

function LoadingState() {
  return (
    <div className="panel rounded-[2rem] border border-white/70 px-6 py-12 text-center shadow-panel">
      <div className="mx-auto h-12 w-12 animate-spin rounded-full border-4 border-tamu-maroon/15 border-t-tamu-maroon" />
      <p className="mt-4 text-lg font-medium text-tamu-ink">Searching the catalog semantically...</p>
      <p className="mt-2 text-sm text-tamu-slate">
        CourseConnect is mapping your research intent to graduate course descriptions.
      </p>
    </div>
  );
}

function EmptyState({ query, onSuggestion }) {
  return (
    <div className="panel rounded-[2rem] border border-dashed border-tamu-maroon/20 px-6 py-12 text-center shadow-panel">
      <h3 className="display-serif text-3xl text-tamu-maroon">No strong matches found</h3>
      <p className="mx-auto mt-3 max-w-2xl text-tamu-slate">
        Try broadening the topic, removing one filter, or exploring nearby research directions.
      </p>
      <div className="mt-6 flex flex-wrap justify-center gap-3">
        {SUGGESTED_QUERIES.filter((item) => item !== query).slice(0, 4).map((item) => (
          <button
            key={item}
            type="button"
            onClick={() => onSuggestion(item)}
            className="rounded-full border border-tamu-maroon/15 bg-white px-4 py-2 text-sm text-tamu-ink transition hover:border-tamu-maroon hover:text-tamu-maroon"
          >
            {item}
          </button>
        ))}
      </div>
    </div>
  );
}

function SearchResultCard({ result, query, isSaved, onToggleSave }) {
  const [expanded, setExpanded] = useState(false);
  const progressWidth = `${Math.max(12, Math.min(result.score, 100))}%`;
  const readiness = getReadinessBadge(result.prerequisites);

  return (
    <article className="result-enter panel rounded-[2rem] border border-white/70 p-6 shadow-panel">
      <div className="flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
        <div className="max-w-3xl">
          <div className="flex flex-wrap items-center gap-3">
            <span className="rounded-full bg-tamu-maroon px-3 py-1 text-xs font-semibold uppercase tracking-[0.18em] text-white">
              {result.code}
            </span>
            <span className="rounded-full bg-tamu-maroon/10 px-3 py-1 text-xs font-medium uppercase tracking-[0.18em] text-tamu-maroon">
              {result.department}
            </span>
            {result.credits ? (
              <span className="rounded-full border border-tamu-maroon/15 px-3 py-1 text-xs font-medium text-tamu-slate">
                {result.credits} credits
              </span>
            ) : null}
            <span className={`rounded-full px-3 py-1 text-xs font-semibold ${readiness.tone}`}>{readiness.label}</span>
          </div>

          <h3 className="display-serif mt-4 text-3xl text-tamu-ink">{result.title}</h3>
          <p className="mt-2 text-sm font-medium uppercase tracking-[0.18em] text-tamu-muted">{scoreLabel(result.score)}</p>
        </div>

        <div className="w-full max-w-sm rounded-3xl bg-white/70 p-4">
          <div className="flex items-center justify-between text-sm">
            <span className="font-medium text-tamu-slate">Semantic relevance</span>
            <span className="font-semibold text-tamu-ink">{result.score.toFixed(1)}%</span>
          </div>
          <div className="mt-3 h-3 rounded-full bg-tamu-stone">
            <div className={`h-3 rounded-full ${scoreTone(result.score)}`} style={{ width: progressWidth }} />
          </div>
          <div className="mt-4 flex gap-3">
            <button
              type="button"
              onClick={() => onToggleSave(result)}
              className="rounded-full border border-tamu-maroon/20 px-4 py-2 text-sm font-medium text-tamu-ink transition hover:border-tamu-maroon"
            >
              {isSaved ? "Saved" : "Save course"}
            </button>
          </div>
        </div>
      </div>

      <div className="mt-5 text-[15px] leading-7 text-tamu-slate">
        <div className={expanded ? "" : "line-clamp-4"}>{highlightText(result.description, query)}</div>
        {result.description.length > 260 ? (
          <button
            type="button"
            onClick={() => setExpanded((current) => !current)}
            className="mt-2 text-sm font-semibold text-tamu-maroon transition hover:text-tamu-ink"
          >
            {expanded ? "Show less" : "Expand description"}
          </button>
        ) : null}
      </div>

      <div className="mt-5 grid gap-4 lg:grid-cols-[1.2fr_0.8fr]">
        <div className="rounded-3xl bg-white/70 p-4">
          <div className="text-xs uppercase tracking-[0.18em] text-tamu-muted">Prerequisites</div>
          <div className="mt-2 text-sm leading-6 text-tamu-ink">
            {result.prerequisites?.trim() ? result.prerequisites : "No prerequisites listed in the catalog entry."}
          </div>
        </div>
        <div className="rounded-3xl bg-tamu-cream p-4">
          <div className="text-xs uppercase tracking-[0.18em] text-tamu-muted">Planner note</div>
          <div className="mt-2 text-sm leading-6 text-tamu-ink">
            {result.prerequisites?.trim()
              ? "Good candidate if you want a course with more structure or prior preparation."
              : "Strong choice for exploration when you want a lower-friction entry point into the topic."}
          </div>
        </div>
      </div>
    </article>
  );
}

function SpotlightCard({ topResult, query }) {
  if (!topResult) return null;

  return (
    <div className="panel rounded-[2rem] border border-white/70 p-6 shadow-panel">
      <div className="flex items-center gap-3">
        <span className="rounded-full bg-tamu-maroon px-3 py-1 text-xs font-semibold uppercase tracking-[0.2em] text-white">
          Best match
        </span>
        <span className="text-xs uppercase tracking-[0.18em] text-tamu-muted">For "{query}"</span>
      </div>
      <h2 className="display-serif mt-4 text-4xl text-tamu-maroon">{topResult.title}</h2>
      <p className="mt-2 text-sm font-semibold uppercase tracking-[0.18em] text-tamu-muted">{topResult.code}</p>
      <p className="mt-4 text-base leading-7 text-tamu-slate">{topResult.description.slice(0, 240)}...</p>
      <div className="mt-5 flex flex-wrap gap-3">
        <span className="rounded-full bg-white px-4 py-2 text-sm font-medium text-tamu-ink">
          {topResult.score.toFixed(1)}% semantic fit
        </span>
        <span className="rounded-full bg-white px-4 py-2 text-sm font-medium text-tamu-ink">
          {topResult.department} department
        </span>
        {topResult.credits ? (
          <span className="rounded-full bg-white px-4 py-2 text-sm font-medium text-tamu-ink">
            {topResult.credits} credits
          </span>
        ) : null}
      </div>
    </div>
  );
}

export default function App() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState([]);
  const [searchMeta, setSearchMeta] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [filters, setFilters] = useState(initialFilters);
  const [appliedFilters, setAppliedFilters] = useState(initialFilters);
  const [history, setHistory] = useState([]);
  const [savedCourses, setSavedCourses] = useState([]);
  const [lastQuery, setLastQuery] = useState("");

  useEffect(() => {
    setHistory(JSON.parse(window.localStorage.getItem("courseconnect-history") || "[]"));
    setSavedCourses(JSON.parse(window.localStorage.getItem("courseconnect-saved") || "[]"));
  }, []);

  useEffect(() => {
    window.localStorage.setItem("courseconnect-history", JSON.stringify(history));
  }, [history]);

  useEffect(() => {
    window.localStorage.setItem("courseconnect-saved", JSON.stringify(savedCourses));
  }, [savedCourses]);

  const savedCodes = useMemo(() => new Set(savedCourses.map((course) => course.code)), [savedCourses]);
  const topResult = results[0] || null;
  const activeQueryTerms = useMemo(() => extractTerms(lastQuery || query), [lastQuery, query]);
  const queryCoach = useMemo(() => buildQueryCoach(query || lastQuery), [query, lastQuery]);

  const insightStats = useMemo(() => {
    const departments = [...new Set(results.map((item) => item.department))];
    const averageScore =
      results.length > 0 ? (results.reduce((sum, item) => sum + item.score, 0) / results.length).toFixed(1) : "0.0";
    const creditValues = results.map((item) => parseCredits(item.credits)).filter((value) => value !== null);
    const averageCredits = creditValues.length
      ? (creditValues.reduce((sum, value) => sum + value, 0) / creditValues.length).toFixed(1)
      : "0.0";

    return {
      departments: departments.length,
      averageScore,
      averageCredits,
      strongestDepartment: departments[0] || "None yet",
    };
  }, [results]);

  async function runSearch(nextQuery = query, filterSource = appliedFilters) {
    const trimmedQuery = nextQuery.trim();
    if (!trimmedQuery) {
      setError("Enter a research interest or topic to begin.");
      setResults([]);
      setSearchMeta(null);
      return;
    }

    setLoading(true);
    setError("");
    setLastQuery(trimmedQuery);

    const params = new URLSearchParams({
      q: trimmedQuery,
      top_k: "10",
    });

    if (filterSource.department) params.set("department", filterSource.department);
    if (filterSource.minCredits) params.set("min_credits", filterSource.minCredits);
    if (filterSource.maxCredits) params.set("max_credits", filterSource.maxCredits);

    try {
      const response = await fetch(`${API_BASE}/search?${params.toString()}`);
      if (!response.ok) {
        const payload = await response.json().catch(() => ({}));
        throw new Error(payload.detail || "Search failed.");
      }

      const data = await response.json();
      setResults(data.results || []);
      setSearchMeta(data);
      setHistory((current) => [trimmedQuery, ...current.filter((item) => item !== trimmedQuery)].slice(0, 6));
    } catch (searchError) {
      setResults([]);
      setSearchMeta(null);
      setError(searchError.message || "Unable to reach the backend right now.");
    } finally {
      setLoading(false);
    }
  }

  function applySuggestion(suggestion) {
    setQuery(suggestion);
    runSearch(suggestion, appliedFilters);
  }

  function applyFilters() {
    const nextFilters = { ...filters };
    setAppliedFilters(nextFilters);
    if ((query || lastQuery).trim()) {
      runSearch(query || lastQuery, nextFilters);
    }
  }

  function toggleSavedCourse(course) {
    setSavedCourses((current) =>
      current.some((item) => item.code === course.code)
        ? current.filter((item) => item.code !== course.code)
        : [course, ...current].slice(0, 12),
    );
  }

  function clearFilters() {
    setFilters(initialFilters);
    setAppliedFilters(initialFilters);
    if ((query || lastQuery).trim()) {
      runSearch(query || lastQuery, initialFilters);
    }
  }

  function handleDownloadPdf() {
    downloadResultsPdf({
      query: lastQuery || query,
      filters: appliedFilters,
      results,
      searchMeta,
    });
  }

  return (
    <div className="min-h-screen bg-tamu-page px-4 py-8 text-tamu-ink sm:px-6 lg:px-10">
      <div className="mx-auto max-w-7xl">
        <div className="mb-6 rounded-full bg-tamu-maroon px-5 py-3 text-xs font-semibold uppercase tracking-[0.24em] text-white shadow-panel">
          Texas A&M inspired semantic course discovery
        </div>

        <header className="grid gap-6 lg:grid-cols-[1.4fr_0.9fr]">
          <section className="hero-panel rounded-[2.25rem] p-8 shadow-panel sm:p-10">
            <div className="flex flex-wrap items-center gap-3">
              <span className="rounded-full bg-white/12 px-4 py-2 text-xs font-semibold uppercase tracking-[0.22em] text-white">
                Course project
              </span>
              <span className="rounded-full bg-tamu-gold px-4 py-2 text-xs font-semibold uppercase tracking-[0.22em] text-tamu-maroon">
                Semantic retrieval
              </span>
            </div>

            <h1 className="display-serif mt-6 max-w-4xl text-5xl leading-tight text-white sm:text-6xl">
              CourseConnect helps TAMU students discover the right graduate courses faster.
            </h1>
            <p className="mt-5 max-w-3xl text-lg leading-8 text-white/82">
              Search by research intent, not catalog guessing. Describe the problem space you care about and get ranked
              graduate courses with meaningful relevance signals, prerequisites, and planning context.
            </p>

            <form
              className="mt-8 rounded-[1.75rem] border border-white/10 bg-white/95 p-4 shadow-sm"
              onSubmit={(event) => {
                event.preventDefault();
                runSearch();
              }}
            >
              <div className="flex flex-col gap-4 xl:flex-row">
                <input
                  value={query}
                  onChange={(event) => setQuery(event.target.value)}
                  placeholder="Try: deep learning for computer vision"
                  className="min-h-14 flex-1 rounded-2xl border border-tamu-maroon/10 bg-tamu-cream px-5 text-base text-tamu-ink outline-none transition placeholder:text-tamu-slate/70 focus:border-tamu-maroon"
                />
                <button
                  type="submit"
                  className="min-h-14 rounded-2xl bg-tamu-maroon px-8 text-base font-semibold text-white transition hover:bg-tamu-maroon-dark"
                >
                  Search Courses
                </button>
              </div>

              <div className="mt-4 flex flex-wrap gap-3">
                {SUGGESTED_QUERIES.map((suggestion) => (
                  <button
                    key={suggestion}
                    type="button"
                    onClick={() => applySuggestion(suggestion)}
                    className="rounded-full border border-tamu-maroon/12 bg-white px-4 py-2 text-sm text-tamu-slate transition hover:border-tamu-maroon hover:text-tamu-maroon"
                  >
                    {suggestion}
                  </button>
                ))}
              </div>
            </form>
          </section>

          <aside className="grid gap-4">
            <StatCard label="Saved courses" value={savedCourses.length} note="Build a shortlist for advising or registration." />
            <StatCard label="Active filters" value={summarizeFilters(appliedFilters)} note="Filters apply only when you click the button below." />
            <StatCard label="Search coach" value="Intent-aware" note={queryCoach} />
          </aside>
        </header>

        <section className="mt-8 grid gap-4 lg:grid-cols-[1.05fr_1.2fr]">
          <div className="panel rounded-[2rem] border border-white/70 p-6 shadow-panel">
            <div className="flex items-center justify-between">
              <h2 className="display-serif text-3xl text-tamu-maroon">Search filters</h2>
              <button type="button" onClick={clearFilters} className="text-sm font-medium text-tamu-maroon">
                Reset
              </button>
            </div>

            <div className="mt-6 grid gap-5 md:grid-cols-2">
              <div>
                <label className="mb-2 block text-sm font-semibold text-tamu-ink">Department</label>
                <input
                  value={filters.department}
                  onChange={(event) => setFilters((current) => ({ ...current, department: event.target.value.toUpperCase() }))}
                  placeholder="Example: CSCE"
                  className="w-full rounded-2xl border border-tamu-maroon/12 bg-white px-4 py-3 text-sm outline-none transition focus:border-tamu-maroon"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="mb-2 block text-sm font-semibold text-tamu-ink">Min credits</label>
                  <input
                    type="number"
                    min="0"
                    step="1"
                    value={filters.minCredits}
                    onChange={(event) => setFilters((current) => ({ ...current, minCredits: event.target.value }))}
                    className="w-full rounded-2xl border border-tamu-maroon/12 bg-white px-4 py-3 text-sm outline-none transition focus:border-tamu-maroon"
                  />
                </div>
                <div>
                  <label className="mb-2 block text-sm font-semibold text-tamu-ink">Max credits</label>
                  <input
                    type="number"
                    min="0"
                    step="1"
                    value={filters.maxCredits}
                    onChange={(event) => setFilters((current) => ({ ...current, maxCredits: event.target.value }))}
                    className="w-full rounded-2xl border border-tamu-maroon/12 bg-white px-4 py-3 text-sm outline-none transition focus:border-tamu-maroon"
                  />
                </div>
              </div>
            </div>

            <div className="mt-5 flex flex-wrap gap-3">
              <button
                type="button"
                onClick={applyFilters}
                className="rounded-2xl bg-tamu-maroon px-5 py-3 text-sm font-semibold text-white transition hover:bg-tamu-maroon-dark"
              >
                Apply search filters
              </button>
              <div className="rounded-2xl border border-tamu-maroon/12 bg-tamu-cream px-4 py-3 text-sm text-tamu-slate">
                {summarizeFilters(appliedFilters)}
              </div>
            </div>

            <div className="mt-6">
              <div className="text-sm font-semibold text-tamu-ink">Research lanes</div>
              <div className="mt-3 flex flex-wrap gap-2">
                {RESEARCH_LANES.map((lane) => (
                  <button
                    key={lane.label}
                    type="button"
                    onClick={() => applySuggestion(lane.query)}
                    className="rounded-full border border-tamu-maroon/12 bg-white px-4 py-2 text-sm text-tamu-slate transition hover:border-tamu-maroon hover:text-tamu-maroon"
                  >
                    {lane.label}
                  </button>
                ))}
              </div>
            </div>
          </div>

          <div className="grid gap-4 md:grid-cols-3">
            <StatCard
              label="Returned results"
              value={results.length}
              note={searchMeta?.message || (lastQuery ? `For "${lastQuery}"` : "Run a search to begin.")}
            />
            <StatCard label="Departments represented" value={insightStats.departments} note={`Top coverage: ${insightStats.strongestDepartment}`} />
            <StatCard
              label="Average match score"
              value={`${insightStats.averageScore}%`}
              note={
                searchMeta?.applied_threshold
                  ? `Threshold: ${searchMeta.applied_threshold}% | Average credits: ${insightStats.averageCredits}`
                  : `Average credits: ${insightStats.averageCredits}`
              }
            />
          </div>
        </section>

        <main className="mt-8 grid gap-8 lg:grid-cols-[320px_minmax(0,1fr)]">
          <aside className="space-y-5">
            <div className="panel rounded-[2rem] border border-white/70 p-6 shadow-panel">
              <h2 className="display-serif text-3xl text-tamu-maroon">Query strategy</h2>
              <p className="mt-3 text-sm leading-6 text-tamu-slate">{queryCoach}</p>
              <div className="mt-4 flex flex-wrap gap-2">
                {activeQueryTerms.length ? (
                  activeQueryTerms.map((term) => (
                    <span
                      key={term}
                      className="rounded-full bg-tamu-maroon/8 px-3 py-1 text-xs font-semibold uppercase tracking-[0.14em] text-tamu-maroon"
                    >
                      {term}
                    </span>
                  ))
                ) : (
                  <span className="text-sm text-tamu-slate">Your query signals will appear here.</span>
                )}
              </div>
            </div>

            <div className="panel rounded-[2rem] border border-white/70 p-6 shadow-panel">
              <h2 className="display-serif text-3xl text-tamu-maroon">Saved shortlist</h2>
              <div className="mt-4 space-y-3">
                {savedCourses.length ? (
                  savedCourses.slice(0, 5).map((course) => (
                    <div key={course.code} className="rounded-2xl bg-white/85 p-4">
                      <div className="text-xs uppercase tracking-[0.16em] text-tamu-muted">{course.code}</div>
                      <div className="mt-1 text-sm font-semibold text-tamu-ink">{course.title}</div>
                      <div className="mt-2 text-xs text-tamu-slate">{course.department || "Graduate course"}</div>
                    </div>
                  ))
                ) : (
                  <p className="text-sm text-tamu-slate">Save courses to create a shortlist for comparison or advising.</p>
                )}
              </div>
            </div>

            <div className="panel rounded-[2rem] border border-white/70 p-6 shadow-panel">
              <h2 className="display-serif text-3xl text-tamu-maroon">Recent searches</h2>
              <div className="mt-4 flex flex-wrap gap-2">
                {history.length ? (
                  history.map((item) => (
                    <button
                      key={item}
                      type="button"
                      onClick={() => applySuggestion(item)}
                      className="rounded-full border border-tamu-maroon/12 bg-white px-3 py-2 text-xs text-tamu-slate transition hover:border-tamu-maroon hover:text-tamu-maroon"
                    >
                      {item}
                    </button>
                  ))
                ) : (
                  <p className="text-sm text-tamu-slate">Your search history will appear here.</p>
                )}
              </div>
            </div>
          </aside>

          <section className="space-y-6">
            {topResult && !loading && !error ? <SpotlightCard topResult={topResult} query={lastQuery} /> : null}

            {searchMeta?.message && results.length > 0 && !loading && !error ? (
              <div className="flex flex-col gap-4 rounded-3xl border border-tamu-maroon/15 bg-white/80 px-5 py-4 text-sm text-tamu-slate md:flex-row md:items-center md:justify-between">
                <div>{searchMeta.message}</div>
                <button
                  type="button"
                  onClick={handleDownloadPdf}
                  className="rounded-2xl bg-tamu-maroon px-4 py-3 text-sm font-semibold text-white transition hover:bg-tamu-maroon-dark"
                >
                  Download course list PDF
                </button>
              </div>
            ) : null}

            {error ? (
              <div className="rounded-3xl border border-red-200 bg-red-50 px-5 py-4 text-sm text-red-700">{error}</div>
            ) : null}

            {loading ? <LoadingState /> : null}

            {!loading && !error && results.length === 0 && lastQuery ? (
              <EmptyState query={lastQuery} onSuggestion={applySuggestion} />
            ) : null}

            {!loading && !lastQuery ? (
              <div className="panel rounded-[2rem] border border-white/70 px-6 py-10 shadow-panel">
                <h2 className="display-serif text-3xl text-tamu-maroon">Start with a research direction</h2>
                <p className="mt-3 max-w-3xl text-tamu-slate">
                  Search by problem area, technique, or application domain. CourseConnect works best with intent-rich
                  prompts such as `large-scale optimization for machine learning` or `wireless mobile systems`.
                </p>
              </div>
            ) : null}

            <div className="space-y-5">
              {results.map((result) => (
                <SearchResultCard
                  key={result.code}
                  result={result}
                  query={lastQuery}
                  isSaved={savedCodes.has(result.code)}
                  onToggleSave={toggleSavedCourse}
                />
              ))}
            </div>
          </section>
        </main>
      </div>
    </div>
  );
}
