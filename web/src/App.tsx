import {
  lazy,
  Suspense,
  useEffect,
  useRef,
  useState,
  type FormEvent,
} from "react";
import {
  NavLink,
  Routes,
  Route,
  useNavigate,
  useLocation,
} from "react-router-dom";
import {
  Compass,
  MapTrifold,
  BookmarkSimple,
  Heart,
  FilmStrip,
  ShieldCheck,
  SignOut,
  ArrowRight,
  List,
  X,
  WifiSlash,
} from "@phosphor-icons/react";
import { api, post, setupAuth, authClient } from "./api";
import { ErrorBox, Loading, LocationLabel } from "./components";
import Discover, { defaultRequest } from "./Discover";
import { Places, Saved, Taste } from "./Library";
const Sources = lazy(() => import("./Sources"));
const Admin = lazy(() => import("./Admin"));
import { PlanDetail, VenueDetail } from "./Details";
import type {
  Config,
  User,
  Venue,
  Plan,
  OutingRequest,
  PlanResponse,
} from "./types";

let startup: Promise<{ config: Config; user: User | null }> | null = null;
async function initialize() {
  const config = await api<Config>("/config");
  await setupAuth(config);
  if (config.mode !== "live") {
    if (!localStorage.getItem("batore-demo-session")) {
      const result = await post<{ access_token: string }>(
        config.mode === "local" ? "/auth/local" : "/auth/demo",
      );
      localStorage.setItem("batore-demo-session", result.access_token);
    }
    try {
      return { config, user: await api<User>("/me") };
    } catch {
      localStorage.removeItem("batore-demo-session");
      const result = await post<{ access_token: string }>(
        config.mode === "local" ? "/auth/local" : "/auth/demo",
      );
      localStorage.setItem("batore-demo-session", result.access_token);
      return { config, user: await api<User>("/me") };
    }
  }
  try {
    return { config, user: await api<User>("/me") };
  } catch {
    return { config, user: null };
  }
}

function SignIn({ onSignedIn }: { onSignedIn: () => void }) {
  const [email, setEmail] = useState(""),
    [message, setMessage] = useState(""),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false);
  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      const auth = authClient();
      if (!auth) throw new Error("Sign-in is not configured.");
      const { error } = await auth.auth.signInWithOtp({
        email,
        options: { emailRedirectTo: location.origin },
      });
      if (error) throw error;
      setMessage("Check your email for your sign-in link.");
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  async function google() {
    try {
      const auth = authClient();
      if (!auth) throw new Error("Sign-in is not configured.");
      const { error } = await auth.auth.signInWithOAuth({
        provider: "google",
        options: { redirectTo: location.origin },
      });
      if (error) throw error;
    } catch (e) {
      setError((e as Error).message);
    }
  }
  useEffect(() => {
    const sub = authClient()?.auth.onAuthStateChange((event, session) => {
      if (event === "SIGNED_IN" && session) setTimeout(onSignedIn, 0);
    });
    return () => sub?.data.subscription.unsubscribe();
  }, []);
  return (
    <main className="sign-in">
      <div className="brand">
        <span className="brand-mark">
          b<span />
        </span>
        <div>
          bites<span>by Batore</span>
        </div>
      </div>
      <div className="sign-in-copy">
        <div className="eyebrow">YOUR CITY. YOUR KIND OF DAY.</div>
        <h1>
          Good plans start
          <br />
          with a little <em>you.</em>
        </h1>
        <p>
          Food, play, and something different — in the time and budget you have.
        </p>
      </div>
      <form className="panel stack-form" onSubmit={submit}>
        <h2>Welcome to Batore</h2>
        <p className="muted">
          Sign in to keep your plans and preferences private.
        </p>
        <label>
          Email address
          <input
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="you@example.com"
          />
        </label>
        <button className="primary" disabled={busy}>
          {busy ? "Sending…" : "Email me a sign-in link"}
          <ArrowRight />
        </button>
        <button className="secondary" type="button" onClick={google}>
          Continue with Google
        </button>
        <ErrorBox message={error} />
        {message && (
          <div className="success" role="status">
            {message}
          </div>
        )}
      </form>
    </main>
  );
}

export default function App() {
  const [config, setConfig] = useState<Config | null>(null),
    [user, setUser] = useState<User | null>(null),
    [error, setError] = useState(""),
    [ready, setReady] = useState(false),
    [venues, setVenues] = useState<Venue[]>([]),
    [plans, setPlans] = useState<Plan[]>([]),
    [request, setRequest] = useState<OutingRequest | null>(null),
    [venueDetail, setVenueDetail] = useState<Venue | null>(null),
    [planDetail, setPlanDetail] = useState<Plan | null>(null),
    [revision, setRevision] = useState(0),
    [mobile, setMobile] = useState(false),
    [online, setOnline] = useState(navigator.onLine),
    [toast, setToast] = useState("");
  const navigate = useNavigate();
  const routeLocation = useLocation();
  const sidebar = useRef<HTMLElement>(null);
  const menuTrigger = useRef<HTMLButtonElement>(null);
  const [smallScreen, setSmallScreen] = useState(
    () => matchMedia("(max-width: 900px)").matches,
  );
  useEffect(() => {
    const query = matchMedia("(max-width: 900px)");
    const changed = () => {
      setSmallScreen(query.matches);
      setMobile(false);
    };
    query.addEventListener("change", changed);
    return () => query.removeEventListener("change", changed);
  }, []);
  useEffect(() => {
    setMobile(false);
    window.scrollTo({ top: 0, behavior: "instant" });
    const titles: Record<string, string> = {
      "/": "Discover",
      "/places": "Explore places",
      "/saved": "Saved for later",
      "/taste": "My taste",
      "/sources": "From my feed",
      "/admin": "Operations",
    };
    document.title = `${titles[routeLocation.pathname] || "Page"} · Bites by Batore`;
  }, [routeLocation.pathname]);
  useEffect(() => {
    if (!mobile || !smallScreen) return;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    const focusable = () =>
      [
        ...(sidebar.current?.querySelectorAll<HTMLElement>(
          "a[href],button:not([disabled])",
        ) || []),
      ].filter((el) => el.getClientRects().length > 0);
    sidebar.current?.querySelector<HTMLButtonElement>(".mobile-close")?.focus();
    const keys = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        e.preventDefault();
        setMobile(false);
      }
      if (e.key !== "Tab") return;
      const elements = focusable(),
        first = elements[0],
        last = elements.at(-1);
      if (e.shiftKey && document.activeElement === first) {
        e.preventDefault();
        last?.focus();
      } else if (!e.shiftKey && document.activeElement === last) {
        e.preventDefault();
        first?.focus();
      }
    };
    document.addEventListener("keydown", keys);
    return () => {
      document.removeEventListener("keydown", keys);
      document.body.style.overflow = previousOverflow;
      menuTrigger.current?.focus();
    };
  }, [mobile, smallScreen]);
  useEffect(() => {
    startup ||= initialize();
    startup
      .then(({ config, user }) => {
        setConfig(config);
        setUser(user);
        if (user) setRequest(defaultRequest(user));
        setReady(true);
      })
      .catch((e) => {
        setError(e.message);
        setReady(true);
      });
  }, []);
  useEffect(() => {
    const on = () => setOnline(navigator.onLine);
    window.addEventListener("online", on);
    window.addEventListener("offline", on);
    return () => {
      window.removeEventListener("online", on);
      window.removeEventListener("offline", on);
    };
  }, []);
  useEffect(() => {
    if (user) loadVenues();
  }, [user?.id]);
  useEffect(() => {
    if (toast) {
      const timer = setTimeout(() => setToast(""), 4500);
      return () => clearTimeout(timer);
    }
  }, [toast]);
  async function loadVenues() {
    try {
      const rows = await api<Venue[]>("/venues");
      setVenues(rows);
      setVenueDetail((v) => (v ? rows.find((x) => x.id === v.id) || v : null));
    } catch (e) {
      setError((e as Error).message);
    }
  }
  async function reloadUser() {
    try {
      const u = await api<User>("/me");
      setUser(u);
      if (!request) setRequest(defaultRequest(u));
      setRevision((n) => n + 1);
      await loadVenues();
    } catch (e) {
      setError((e as Error).message);
    }
  }
  async function saveVenue(v: Venue) {
    try {
      const r = await api<{ saved: boolean }>(`/venues/${v.id}/save`, {
        method: "PUT",
        body: JSON.stringify({ saved: !v.saved }),
      });
      setVenues((rows) =>
        rows.some((x) => x.id === v.id)
          ? rows.map((x) => (x.id === v.id ? { ...x, saved: r.saved } : x))
          : [...rows, { ...v, saved: r.saved }],
      );
      setVenueDetail((x) => (x?.id === v.id ? { ...x, saved: r.saved } : x));
      setToast(
        r.saved ? "Place saved to your collection" : "Place removed from saved",
      );
      setRevision((n) => n + 1);
    } catch (e) {
      setError((e as Error).message);
    }
  }
  async function savePlan(p: Plan) {
    try {
      const next = await post<Plan>(`/plans/${p.id}/save`);
      setPlans((rows) => rows.map((x) => (x.id === p.id ? next : x)));
      setPlanDetail((x) => (x?.id === p.id ? next : x));
      setRevision((n) => n + 1);
      setToast(
        next.saved
          ? "Plan saved to your collection"
          : "Plan removed from saved",
      );
    } catch (e) {
      setError((e as Error).message);
    }
  }
  async function openVenue(id: string) {
    try {
      const v = await api<Venue>(`/venues/${id}`);
      setPlanDetail(null);
      setVenueDetail(v);
    } catch (e) {
      setError((e as Error).message);
    }
  }
  function revised(result: PlanResponse) {
    setPlans(result.options);
    setPlanDetail(null);
    navigate("/");
    setToast(
      result.options.length ? "Fresh alternatives are ready" : result.message,
    );
  }
  async function logout() {
    if (config?.mode !== "live") {
      localStorage.removeItem("batore-demo-session");
      location.reload();
    } else {
      await authClient()?.auth.signOut();
      setUser(null);
      setPlans([]);
      setVenues([]);
      setPlanDetail(null);
      setVenueDetail(null);
    }
  }
  if (!ready)
    return (
      <div className="boot">
        <Loading label="Opening your city…" />
      </div>
    );
  if (!config)
    return (
      <div className="boot">
        <h1>Let’s reconnect.</h1>
        <ErrorBox message={error} />
        <p>Check that the API is running, then reload the page.</p>
        <button className="primary" onClick={() => location.reload()}>
          Try again
        </button>
      </div>
    );
  if (!user) return <SignIn onSignedIn={reloadUser} />;
  const links = [
    {
      to: "/",
      label: "Discover",
      detail: "Plan a few good hours",
      icon: Compass,
    },
    {
      to: "/places",
      label: "Explore places",
      detail: "Dishes, cafés & things to do",
      icon: MapTrifold,
    },
    {
      to: "/saved",
      label: "Saved for later",
      detail: "Your plans & places",
      icon: BookmarkSimple,
    },
    {
      to: "/taste",
      label: "My taste",
      detail: "Preferences & your diary",
      icon: Heart,
    },
    {
      to: "/sources",
      label: "From my feed",
      detail: "Share a place you found",
      icon: FilmStrip,
    },
  ];
  return (
    <div className="app-shell">
      <a className="skip-link" href="#main">
        Skip to content
      </a>
      <aside
        ref={sidebar}
        id="app-navigation"
        className={`sidebar ${mobile ? "open" : ""}`}
        inert={smallScreen && !mobile}
        role={smallScreen ? "dialog" : undefined}
        aria-modal={smallScreen && mobile ? true : undefined}
        aria-label={smallScreen ? "Main menu" : undefined}
      >
        <NavLink to="/" className="brand" onClick={() => setMobile(false)}>
          <span className="brand-mark">
            b<span />
          </span>
          <div>
            bites<span>by Batore</span>
          </div>
        </NavLink>
        <button
          className="mobile-close icon-button"
          onClick={() => setMobile(false)}
          aria-label="Close menu"
        >
          <X />
        </button>
        <div className="nav-heading">MAKE A LITTLE TIME</div>
        <nav aria-label="Main navigation">
          {links.map((l) => (
            <NavLink
              end={l.to === "/"}
              key={l.to}
              to={l.to}
              onClick={() => setMobile(false)}
            >
              <l.icon size={22} />
              <span>
                {l.label}
                <small aria-hidden="true">{l.detail}</small>
              </span>
            </NavLink>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <div className="city-note">
            <span className="eyebrow">ROOTED IN COIMBATORE</span>
            <p>
              There’s more to your
              <br />
              everyday city.
            </p>
            <span className="city-lines" aria-hidden="true" />
          </div>
          {user.is_admin && (
            <NavLink
              className="admin-link"
              to="/admin"
              onClick={() => setMobile(false)}
            >
              <ShieldCheck size={20} />
              Operations
            </NavLink>
          )}
          <button
            className="user-button"
            onClick={() => {
              setMobile(false);
              navigate("/taste");
            }}
          >
            <span className="avatar">
              {user.name.slice(0, 1).toUpperCase()}
            </span>
            <span>
              <strong>{user.name}</strong>
              <small>
                {config.mode === "demo"
                  ? "Local demo account"
                  : config.mode === "local"
                    ? "Local research operator"
                    : "Your personal space"}
              </small>
            </span>
          </button>
          <button className="text-button logout" onClick={logout}>
            <SignOut size={16} />
            {config.mode === "demo"
              ? "Start a new demo account"
              : config.mode === "local"
                ? "Refresh local session"
                : "Sign out"}
          </button>
        </div>
      </aside>
      {mobile && (
        <button
          className="menu-scrim"
          aria-hidden="true"
          tabIndex={-1}
          onClick={() => setMobile(false)}
        />
      )}
      <div className="main-shell" inert={smallScreen && mobile}>
        <header className="topbar">
          <button
            className="icon-button mobile-menu"
            ref={menuTrigger}
            aria-label="Open navigation"
            aria-expanded={mobile}
            aria-controls="app-navigation"
            onClick={() => setMobile(true)}
          >
            <List size={24} />
          </button>
          <span className="topbar-note">
            <span>bites /</span>{" "}
            {links.find((l) => l.to === routeLocation.pathname)?.label ||
              "Operations"}
          </span>
          <LocationLabel />
        </header>
        {config.mode === "demo" && (
          <div className="demo-banner">
            <span>DEMO</span>Fictional places & simulated estimates. Explore the
            experience; don’t use these plans for travel.
          </div>
        )}
        {config.mode === "local" && (
          <div className="demo-banner">
            <span>LOCAL RESEARCH</span>Real source leads, local models and
            storage. Unverified finds await review.
          </div>
        )}
        {!online && (
          <div className="notice offline">
            <WifiSlash />
            You’re offline. Reconnect to access private plans and current
            information.
          </div>
        )}
        <main id="main" className="main-content">
          <ErrorBox message={error} />
          {error && (
            <button
              className="text-button"
              onClick={() => {
                setError("");
                loadVenues();
              }}
            >
              Retry loading data
            </button>
          )}
          <Suspense fallback={<Loading label="Opening this page?" />}>
            <Routes>
              <Route
                path="/"
                element={
                  request && (
                    <Discover
                      user={user}
                      venues={venues}
                      onVenue={setVenueDetail}
                      onSaveVenue={saveVenue}
                      onPlan={setPlanDetail}
                      onSavePlan={savePlan}
                      plans={plans}
                      setPlans={setPlans}
                      request={request}
                      setRequest={setRequest}
                    />
                  )
                }
              />
              <Route
                path="/places"
                element={
                  <Places
                    venues={venues}
                    onVenue={setVenueDetail}
                    onSave={saveVenue}
                  />
                }
              />
              <Route
                path="/saved"
                element={
                  <Saved
                    venues={venues}
                    onVenue={setVenueDetail}
                    onSaveVenue={saveVenue}
                    onPlan={setPlanDetail}
                    onSavePlan={savePlan}
                    revision={revision}
                  />
                }
              />
              <Route
                path="/taste"
                element={
                  <Taste user={user} onUpdate={reloadUser} venues={venues} />
                }
              />
              <Route path="/sources" element={<Sources config={config} />} />
              <Route
                path="/admin"
                element={
                  user.is_admin ? (
                    <Admin
                      onChanged={() => {
                        loadVenues();
                        setRevision((n) => n + 1);
                      }}
                    />
                  ) : (
                    <ErrorBox message="Administrator access is required." />
                  )
                }
              />
              <Route
                path="*"
                element={
                  <div className="empty">
                    <h1>This path doesn’t lead to a place.</h1>
                    <NavLink className="primary" to="/">
                      Back to discover
                    </NavLink>
                  </div>
                }
              />
            </Routes>
          </Suspense>
          <footer className="footer">
            <span>bites by Batore</span>
            <span>Made for a good few hours.</span>
          </footer>
        </main>
      </div>
      {venueDetail && (
        <VenueDetail
          venue={venueDetail}
          onClose={() => setVenueDetail(null)}
          onSave={() => saveVenue(venueDetail)}
          onFeedback={reloadUser}
        />
      )}{" "}
      {planDetail && (
        <PlanDetail
          plan={planDetail}
          onClose={() => setPlanDetail(null)}
          onSave={() => savePlan(planDetail)}
          onVenue={openVenue}
          onRevised={revised}
        />
      )}{" "}
      {toast && (
        <div className="toast" role="status">
          {toast}
        </div>
      )}
    </div>
  );
}
