import { useEffect, useMemo, useState } from "react";

const API_BASE = "http://localhost:8000";
const SUGGESTED_QUERIES = [
  "deep learning for computer vision",
  "distributed cloud systems",
  "privacy in machine learning",
  "robotics and spatial intelligence",
  "cybersecurity data analytics",
  "computational biology and genomics",
];

const initialFilters = {
  department: "",
  minCredits: "",
  maxCredits: "",
};

function scoreTone(score) {
  if (score >= 88) return "bg-emerald-600";
  if (score >= 75) return "bg-amber-500";
  return "bg-roseclay";
}

function highlightText(text, query) {
  if (!query.trim()) return text;
  const terms = [...new Set(query.toLowerCase().match(/[a-z0-9]+/g) || [])].filter((term) => term.length > 2);
  if (!terms.length) return text;

  const escapedTerms = terms.map((term) => term.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"));
  const pattern = new RegExp(`(${escapedTerms.join("|")})`, "ig");
  const parts = text.split(pattern);

  return parts.map((part, index) =>
    terms.includes(part.toLowerCase()) ? (
      <mark key={`${part}-${index}`} className="rounded bg-amber-200 px-1 text-ink">
        {part}
      </mark>
    ) : (
      <span key={`${part}-${index}`}>{part}</span>
    ),
  );
}

function StatCard({ label, value, note }) {
  return (
    <div className="glass-panel rounded-3xl border border-white/60 p-5 shadow-panel">
      <div className="text-xs uppercase tracking-[0.22em] text-slate">{label}</div>
      <div className="mt-3 text-3xl font-semibold text-ink">{value}</div>
      <div className="mt-1 text-sm text-slate">{note}</div>
    </div>
  );
}

function FilterChip({ active, label, onClick }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`rounded-full border px-4 py-2 text-sm transition ${
        active
          ? "border-ink bg-ink text-white"
          : "border-slate/20 bg-white/70 text-slate hover:border-slate/40 hover:text-ink"
      }`}
    >
      {label}
    </button>
  );
}

function LoadingState() {
  return (
    <div className="glass-panel rounded-4xl border border-white/70 px-6 py-12 text-center shadow-panel">
      <div className="mx-auto h-12 w-12 animate-spin rounded-full border-4 border-ink/15 border-t-evergreen" />
      <p className="mt-4 text-lg font-medium text-ink">Searching the catalog semantically...</p>
      <p className="mt-2 text-sm text-slate">
        CourseConnect is comparing your intent against graduate course descriptions.
      </p>
    </div>
  );
}

function EmptyState({ query, onSuggestion }) {
  return (
    <div className="glass-panel rounded-4xl border border-dashed border-slate/25 px-6 py-12 text-center shadow-panel">
      <h3 className="display-serif text-3xl text-ink">No strong matches found</h3>
      <p className="mx-auto mt-3 max-w-2xl text-slate">
        Try broadening the topic, removing one constraint, or exploring adjacent research themes below.
      </p>
      <div className="mt-6 flex flex-wrap justify-center gap-3">
        {SUGGESTED_QUERIES.filter((item) => item !== query).slice(0, 4).map((item) => (
          <button
            key={item}
            type="button"
            onClick={() => onSuggestion(item)}
            className="rounded-full border border-slate/20 bg-white px-4 py-2 text-sm text-ink transition hover:border-evergreen hover:text-evergreen"
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

  return (
    <article className="result-enter glass-panel rounded-4xl border border-white/70 p-6 shadow-panel">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div className="max-w-3xl">
          <div className="flex flex-wrap items-center gap-3">
            <span className="rounded-full bg-ink px-3 py-1 text-xs font-semibold uppercase tracking-[0.18em] text-white">
              {result.code}
            </span>
            <span className="rounded-full bg-mist px-3 py-1 text-xs font-medium uppercase tracking-[0.18em] text-evergreen">
              {result.department}
            </span>
            {result.credits ? (
              <span className="rounded-full border border-slate/20 px-3 py-1 text-xs font-medium text-slate">
                {result.credits} credits
              </span>
            ) : null}
          </div>

          <h3 className="display-serif mt-4 text-3xl text-ink">{result.title}</h3>
        </div>

        <div className="w-full max-w-xs">
          <div className="flex items-center justify-between text-sm">
            <span className="font-medium text-slate">Relevance</span>
            <span className="font-semibold text-ink">{result.score.toFixed(1)}%</span>
          </div>
          <div className="mt-2 h-3 rounded-full bg-slate/10">
            <div className={`h-3 rounded-full ${scoreTone(result.score)}`} style={{ width: progressWidth }} />
          </div>
          <button
            type="button"
            onClick={() => onToggleSave(result)}
            className="mt-4 rounded-full border border-slate/20 px-4 py-2 text-sm font-medium text-ink transition hover:border-ink"
          >
            {isSaved ? "Saved course" : "Save course"}
          </button>
        </div>
      </div>

      <div className="mt-5 text-[15px] leading-7 text-slate">
        <div className={expanded ? "" : "line-clamp-4"}>{highlightText(result.description, query)}</div>
        {result.description.length > 260 ? (
          <button
            type="button"
            onClick={() => setExpanded((current) => !current)}
            className="mt-2 text-sm font-semibold text-evergreen transition hover:text-ink"
          >
            {expanded ? "Show less" : "Expand description"}
          </button>
        ) : null}
      </div>

      <div className="mt-5 rounded-3xl bg-white/70 p-4">
        <div className="text-xs uppercase tracking-[0.18em] text-slate">Prerequisites</div>
        <div className="mt-2 text-sm leading-6 text-ink">
          {result.prerequisites?.trim() ? result.prerequisites : "No prerequisites listed in the catalog entry."}
        </div>
      </div>
    </article>
  );
}

export default function App() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [filters, setFilters] = useState(initialFilters);
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

  const insightStats = useMemo(() => {
    const departments = [...new Set(results.map((item) => item.department))];
    const averageScore =
      results.length > 0 ? (results.reduce((sum, item) => sum + item.score, 0) / results.length).toFixed(1) : "0.0";
    const averageCredits = results.length
      ? (
          results.reduce((sum, item) => sum + Number.parseFloat(item.credits || "0"), 0) /
          results.filter((item) => item.credits).length
        ).toFixed(1)
      : "0.0";

    return {
      departments: departments.length,
      averageScore,
      averageCredits: averageCredits === "NaN" ? "0.0" : averageCredits,
    };
  }, [results]);

  async function runSearch(nextQuery = query) {
    const trimmedQuery = nextQuery.trim();
    if (!trimmedQuery) {
      setError("Enter a research interest or topic to begin.");
      setResults([]);
      return;
    }

    setLoading(true);
    setError("");
    setLastQuery(trimmedQuery);

    const params = new URLSearchParams({
      q: trimmedQuery,
      top_k: "10",
    });

    if (filters.department) params.set("department", filters.department);
    if (filters.minCredits) params.set("min_credits", filters.minCredits);
    if (filters.maxCredits) params.set("max_credits", filters.maxCredits);

    try {
      const response = await fetch(`${API_BASE}/search?${params.toString()}`);
      if (!response.ok) {
        const payload = await response.json().catch(() => ({}));
        throw new Error(payload.detail || "Search failed.");
      }

      const data = await response.json();
      setResults(data);
      setHistory((current) => [trimmedQuery, ...current.filter((item) => item !== trimmedQuery)].slice(0, 6));
    } catch (searchError) {
      setResults([]);
      setError(searchError.message || "Unable to reach the backend right now.");
    } finally {
      setLoading(false);
    }
  }

  function applySuggestion(suggestion) {
    setQuery(suggestion);
    runSearch(suggestion);
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
  }

  return (
    <div className="min-h-screen bg-grain px-4 py-8 text-ink sm:px-6 lg:px-10">
      <div className="mx-auto max-w-7xl">
        <header className="grid gap-6 lg:grid-cols-[1.45fr_0.9fr]">
          <section className="glass-panel rounded-[2.25rem] border border-white/70 p-8 shadow-panel sm:p-10">
            <div className="flex flex-wrap items-center gap-3">
              <span className="rounded-full bg-evergreen/10 px-4 py-2 text-xs font-semibold uppercase tracking-[0.22em] text-evergreen">
                Semantic course discovery
              </span>
              <span className="rounded-full bg-white px-4 py-2 text-xs font-semibold uppercase tracking-[0.22em] text-slate">
                Graduate students
              </span>
            </div>

            <h1 className="display-serif mt-6 max-w-4xl text-5xl leading-tight text-ink sm:text-6xl">
              CourseConnect helps research interests find the right classroom.
            </h1>
            <p className="mt-5 max-w-3xl text-lg leading-8 text-slate">
              Describe the kind of work you want to do, not just the words you expect in a catalog. CourseConnect uses
              semantic search to surface graduate courses that align with your intent.
            </p>

            <form
              className="mt-8 rounded-[1.75rem] border border-slate/15 bg-white/80 p-4 shadow-sm"
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
                  className="min-h-14 flex-1 rounded-2xl border border-slate/15 bg-parchment px-5 text-base text-ink outline-none ring-0 transition placeholder:text-slate/70 focus:border-evergreen"
                />
                <button
                  type="submit"
                  className="min-h-14 rounded-2xl bg-ink px-8 text-base font-semibold text-white transition hover:bg-evergreen"
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
                    className="rounded-full border border-slate/15 bg-white px-4 py-2 text-sm text-slate transition hover:border-evergreen hover:text-evergreen"
                  >
                    {suggestion}
                  </button>
                ))}
              </div>
            </form>
          </section>

          <aside className="grid gap-4">
            <StatCard label="Saved courses" value={savedCourses.length} note="Keep a shortlist of promising options." />
            <StatCard label="Recent searches" value={history.length} note="Jump back into prior research directions." />
            <StatCard
              label="Smart filtering"
              value="Dept + Credits"
              note="Narrow results without giving up semantic relevance."
            />
          </aside>
        </header>

        <main className="mt-8 grid gap-8 lg:grid-cols-[320px_minmax(0,1fr)]">
          <section className="glass-panel rounded-[2rem] border border-white/70 p-6 shadow-panel">
            <div className="flex items-center justify-between">
              <h2 className="display-serif text-3xl text-ink">Refine the search</h2>
              <button type="button" onClick={clearFilters} className="text-sm font-medium text-evergreen">
                Reset
              </button>
            </div>

            <div className="mt-6 space-y-5">
              <div>
                <label className="mb-2 block text-sm font-semibold text-ink">Department</label>
                <input
                  value={filters.department}
                  onChange={(event) => setFilters((current) => ({ ...current, department: event.target.value.toUpperCase() }))}
                  placeholder="Example: CSCE"
                  className="w-full rounded-2xl border border-slate/15 bg-white px-4 py-3 text-sm outline-none transition focus:border-evergreen"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="mb-2 block text-sm font-semibold text-ink">Min credits</label>
                  <input
                    type="number"
                    min="0"
                    step="1"
                    value={filters.minCredits}
                    onChange={(event) => setFilters((current) => ({ ...current, minCredits: event.target.value }))}
                    className="w-full rounded-2xl border border-slate/15 bg-white px-4 py-3 text-sm outline-none transition focus:border-evergreen"
                  />
                </div>
                <div>
                  <label className="mb-2 block text-sm font-semibold text-ink">Max credits</label>
                  <input
                    type="number"
                    min="0"
                    step="1"
                    value={filters.maxCredits}
                    onChange={(event) => setFilters((current) => ({ ...current, maxCredits: event.target.value }))}
                    className="w-full rounded-2xl border border-slate/15 bg-white px-4 py-3 text-sm outline-none transition focus:border-evergreen"
                  />
                </div>
              </div>

              <div>
                <div className="text-sm font-semibold text-ink">Quick themes</div>
                <div className="mt-3 flex flex-wrap gap-2">
                  {["AI", "systems", "security", "robotics", "visualization", "biology"].map((theme) => (
                    <FilterChip
                      key={theme}
                      label={theme}
                      active={query.toLowerCase().includes(theme.toLowerCase())}
                      onClick={() => setQuery(theme)}
                    />
                  ))}
                </div>
              </div>

              <div>
                <div className="text-sm font-semibold text-ink">Recent searches</div>
                <div className="mt-3 flex flex-wrap gap-2">
                  {history.length ? (
                    history.map((item) => (
                      <button
                        key={item}
                        type="button"
                        onClick={() => applySuggestion(item)}
                        className="rounded-full border border-slate/15 bg-white px-3 py-2 text-xs text-slate transition hover:border-ink hover:text-ink"
                      >
                        {item}
                      </button>
                    ))
                  ) : (
                    <p className="text-sm text-slate">Your search history will appear here.</p>
                  )}
                </div>
              </div>

              <div>
                <div className="text-sm font-semibold text-ink">Saved shortlist</div>
                <div className="mt-3 space-y-3">
                  {savedCourses.length ? (
                    savedCourses.slice(0, 4).map((course) => (
                      <div key={course.code} className="rounded-2xl bg-white/80 p-3">
                        <div className="text-xs uppercase tracking-[0.16em] text-slate">{course.code}</div>
                        <div className="mt-1 text-sm font-semibold text-ink">{course.title}</div>
                      </div>
                    ))
                  ) : (
                    <p className="text-sm text-slate">Save courses to keep a comparison set while you explore.</p>
                  )}
                </div>
              </div>
            </div>
          </section>

          <section className="space-y-6">
            <div className="grid gap-4 sm:grid-cols-3">
              <StatCard label="Returned results" value={results.length} note={lastQuery ? `For "${lastQuery}"` : "Run a search to begin."} />
              <StatCard label="Departments represented" value={insightStats.departments} note="Semantic matches can span adjacent fields." />
              <StatCard label="Average match score" value={`${insightStats.averageScore}%`} note={`Average credits: ${insightStats.averageCredits}`} />
            </div>

            {error ? (
              <div className="rounded-3xl border border-roseclay/30 bg-white/80 px-5 py-4 text-sm text-roseclay">{error}</div>
            ) : null}

            {loading ? <LoadingState /> : null}

            {!loading && !error && results.length === 0 && lastQuery ? (
              <EmptyState query={lastQuery} onSuggestion={applySuggestion} />
            ) : null}

            {!loading && !lastQuery ? (
              <div className="glass-panel rounded-4xl border border-white/70 px-6 py-10 shadow-panel">
                <h2 className="display-serif text-3xl text-ink">Start with a research direction</h2>
                <p className="mt-3 max-w-3xl text-slate">
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
