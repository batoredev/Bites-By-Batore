import { useEffect, useRef, type ReactNode } from "react";
import {
  ArrowUpRight,
  BookmarkSimple,
  Coffee,
  CookingPot,
  GameController,
  Leaf,
  Popcorn,
  X,
  MapPin,
  Clock,
  Users,
  BowlingBall,
  Mountains,
  CheckCircle,
  Storefront,
  IceCream,
  Wine,
  Ticket,
  PaintBrush,
  Bank,
  SoccerBall,
} from "@phosphor-icons/react";
import type { Category, Venue, Plan } from "./types";
import { money } from "./api";
export const categories: {
  id: Category;
  label: string;
  icon: typeof Coffee;
}[] = [
  { id: "food", label: "Restaurants", icon: CookingPot },
  { id: "street_food", label: "Street food", icon: Storefront },
  { id: "cafe", label: "Cafés", icon: Coffee },
  { id: "dessert", label: "Desserts", icon: IceCream },
  { id: "nightlife", label: "Bars & lounges", icon: Wine },
  { id: "cinema", label: "Movies", icon: Popcorn },
  { id: "gaming", label: "Gaming", icon: GameController },
  { id: "bowling", label: "Bowling", icon: BowlingBall },
  { id: "adventure", label: "Adventure", icon: Mountains },
  { id: "amusement", label: "Theme parks", icon: Ticket },
  { id: "park", label: "Parks & lakes", icon: Leaf },
  { id: "workshop", label: "Workshops", icon: PaintBrush },
  { id: "attraction", label: "Museums & sights", icon: Bank },
  { id: "sports", label: "Turfs & courts", icon: SoccerBall },
];
export function Art({
  category,
  small = false,
}: {
  category: Category;
  small?: boolean;
}) {
  const Icon = categories.find((c) => c.id === category)?.icon || Coffee;
  return (
    <div
      className={`place-art art-${category} ${small ? "small" : ""}`}
      aria-hidden="true"
    >
      <span className="art-orbit" />
      <span className="art-dot" />
      <Icon weight="duotone" />
      <span className="art-caption">
        a little more{" "}
        {category === "food"
          ? "flavour"
          : category === "cafe"
            ? "pause"
            : "play"}
      </span>
    </div>
  );
}
export function Empty({
  title,
  children,
}: {
  title: string;
  children: ReactNode;
}) {
  return (
    <div className="empty">
      <Leaf size={32} />
      <h3>{title}</h3>
      <p>{children}</p>
    </div>
  );
}
export function ErrorBox({ message }: { message: string }) {
  return message ? (
    <div className="error" role="alert">
      {message}
    </div>
  ) : null;
}
export function Loading({
  label = "Finding your next good plan…",
}: {
  label?: string;
}) {
  return (
    <div className="loading" role="status">
      <span className="spinner" />
      {label}
    </div>
  );
}
export function Modal({
  title,
  onClose,
  children,
  wide = false,
}: {
  title: string;
  onClose: () => void;
  children: ReactNode;
  wide?: boolean;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    const d = ref.current!;
    const trigger =
      document.activeElement instanceof HTMLElement
        ? document.activeElement
        : null;
    d.showModal();
    const previous = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      d.close();
      document.body.style.overflow = previous;
      if (trigger?.isConnected) trigger.focus({ preventScroll: true });
    };
  }, []);
  return (
    <dialog
      ref={ref}
      className={wide ? "modal wide" : "modal"}
      onCancel={onClose}
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
      aria-label={title}
    >
      <header className="modal-head">
        <h2>{title}</h2>
        <button
          className="icon-button"
          aria-label="Close dialog"
          onClick={onClose}
        >
          <X size={22} />
        </button>
      </header>
      <div className="modal-body">{children}</div>
    </dialog>
  );
}
export function VenueCard({
  venue,
  onOpen,
  onSave,
}: {
  venue: Venue;
  onOpen: () => void;
  onSave: () => void;
}) {
  return (
    <article className="venue-card">
      <button
        className="art-button"
        onClick={onOpen}
        aria-label={`Explore ${venue.name}`}
      >
        <Art category={venue.category} />
      </button>
      <button
        className={`bookmark ${venue.saved ? "selected" : ""}`}
        aria-label={`${venue.saved ? "Unsave" : "Save"} ${venue.name}`}
        onClick={onSave}
      >
        <BookmarkSimple size={20} weight={venue.saved ? "fill" : "regular"} />
      </button>
      <div className="venue-card-body">
        <div className="eyebrow">
          {venue.category} <span>· {venue.area}</span>
        </div>
        <button className="text-button title-link" onClick={onOpen}>
          <h3>{venue.name}</h3>
          <ArrowUpRight size={20} />
        </button>
        <p>
          {venue.details.speciality ||
            venue.details.description ||
            "Details awaiting verification"}
        </p>
        <div className="card-meta">
          <span>
            {typeof venue.details.price_per_person === "number"
              ? money(venue.details.price_per_person)
              : "Price unconfirmed"}{" "}
            <small>/ person</small>
          </span>
          <span className="tiny-tag">
            {venue.is_demo ? "Demo venue" : venue.freshness}
          </span>
        </div>
      </div>
    </article>
  );
}
export function PlanCard({
  plan,
  index,
  onOpen,
  onSave,
}: {
  plan: Plan;
  index: number;
  onOpen: () => void;
  onSave: () => void;
}) {
  const r = plan.result;
  return (
    <article className={`plan-card ${index === 0 ? "featured" : ""}`}>
      <div className="plan-card-top">
        <span className="eyebrow">
          {index === 0
            ? "Your best fit"
            : index === 1
              ? "Another way to go"
              : index === 2
                ? "A change of scene"
                : `Option ${index + 1}`}
        </span>
        <button
          className="icon-button"
          onClick={onSave}
          aria-label={`${plan.saved ? "Unsave" : "Save"} plan ${index + 1}`}
        >
          <BookmarkSimple size={21} weight={plan.saved ? "fill" : "regular"} />
        </button>
      </div>
      <div className="mini-route">
        {r.stops.map((s, i) => (
          <span key={s.venue_id}>
            {i > 0 && <span className="route-dot">···</span>}
            <Art category={s.category} small />
          </span>
        ))}
      </div>
      <h3>{r.title}</h3>
      <p>{r.reasons[0]}</p>
      <div className="plan-stats">
        <span>
          <Clock />
          {r.total_minutes} min
        </span>
        <span>
          <Users />
          {plan.request.party_size}
        </span>
        <strong>{money(r.total_cost)}</strong>
      </div>
      <div className="fit-note">
        <CheckCircle size={16} />
        {money(r.budget_remaining)} within budget · {r.time_remaining} min to
        spare
      </div>
      <button
        className={index === 0 ? "primary full" : "secondary full"}
        onClick={onOpen}
      >
        See this plan <ArrowUpRight size={18} />
      </button>
    </article>
  );
}
export function PageTitle({
  eyebrow,
  title,
  description,
  action,
}: {
  eyebrow: string;
  title: string;
  description: string;
  action?: ReactNode;
}) {
  return (
    <div className="page-title">
      <div>
        <div className="eyebrow">{eyebrow}</div>
        <h1>{title}</h1>
        <p>{description}</p>
      </div>
      {action}
    </div>
  );
}
export function LocationLabel() {
  return (
    <span className="location-label">
      <MapPin size={17} weight="fill" />
      Coimbatore
      <span className="live-dot" />
    </span>
  );
}
