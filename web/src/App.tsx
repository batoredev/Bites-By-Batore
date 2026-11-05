import { lazy, Suspense, useEffect, useState, type FormEvent } from "react";
import { NavLink, Routes, Route, useNavigate } from "react-router-dom";
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
      const r = await post<{ saved: boolean }>(`/venues/${v.id}/save`);
      setVenues((rows) =>
        rows.map((x) => (x.id === v.id ? { ...x, saved: r.saved } : x)),
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
    { to: "/", label: "Discover", icon: Compass },
    { to: "/places", label: "Explore places", icon: MapTrifold },
    { to: "/saved", label: "Saved for later", icon: BookmarkSimple },
    { to: "/taste", label: "My taste", icon: Heart },
    { to: "/sources", label: "From my feed", icon: FilmStrip },
  ];
  return (
    <div className="app-shell">
      <a className="skip-link" href="#main">
        Skip to content
      </a>
      <aside className={`sidebar ${mobile ? "open" : ""}`}>
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
              {l.label}
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
          <button className="user-button" onClick={() => navigate("/taste")}>
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
          aria-label="Close menu"
          onClick={() => setMobile(false)}
        />
      )}
      <div className="main-shell">
        <header className="topbar">
          <button
            className="icon-button mobile-menu"
            aria-label="Open navigation"
            onClick={() => setMobile(true)}
          >
            <List size={24} />
          </button>
          <span className="topbar-note">
            A little more flavour. A little more life.
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
