import type { SupabaseClient } from "@supabase/supabase-js";
import type { Config } from "./types";
let supabase: SupabaseClient | null = null;
export async function setupAuth(config: Config) {
  if (config.mode === "live" && config.supabase_url && config.supabase_key) {
    const { createClient } = await import("@supabase/supabase-js");
    supabase = createClient(config.supabase_url, config.supabase_key);
  }
  return supabase;
}
export const authClient = () => supabase;
export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  let token = localStorage.getItem("batore-demo-session");
  if (supabase)
    token =
      (await supabase.auth.getSession()).data.session?.access_token || null;
  const headers = new Headers(init.headers);
  if (token) headers.set("Authorization", `Bearer ${token}`);
  if (init.body && !(init.body instanceof FormData))
    headers.set("Content-Type", "application/json");
  const response = await fetch(`/api${path}`, { ...init, headers });
  let data;
  try {
    data = await response.json();
  } catch {
    throw new Error(
      "The service returned an unexpected response. Please try again.",
    );
  }
  if (!response.ok) {
    const detail = data.detail;
    throw new Error(
      Array.isArray(detail)
        ? detail.map((x: { msg: string }) => x.msg).join(". ")
        : typeof detail === "object" && detail
          ? [detail.message, ...(detail.blockers || [])]
              .filter(Boolean)
              .join(". ")
          : detail || "Request failed. Please try again.",
    );
  }
  return data as T;
}
export const post = <T>(path: string, data: unknown = {}) =>
  api<T>(path, { method: "POST", body: JSON.stringify(data) });
export const money = (value: number) =>
  new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
  }).format(value);
export const time = (date: string) =>
  new Intl.DateTimeFormat("en-IN", {
    hour: "numeric",
    minute: "2-digit",
    timeZone: "Asia/Kolkata",
  }).format(new Date(date));
export const dateText = (date: string) =>
  new Intl.DateTimeFormat("en-IN", {
    day: "numeric",
    month: "short",
    hour: "numeric",
    minute: "2-digit",
    timeZone: "Asia/Kolkata",
  }).format(new Date(date));
export function safeLink(url?: string) {
  try {
    const u = new URL(url || "");
    return u.protocol === "https:" ? u.href : undefined;
  } catch {
    return undefined;
  }
}
