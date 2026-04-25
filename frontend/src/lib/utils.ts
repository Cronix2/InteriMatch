import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";
import axios from "axios";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/**
 * Extrait un message d'erreur lisible depuis une exception (axios ou autre),
 * évitant le typage `any` partout dans les `catch`.
 */
export function getApiErrorDetail(err: unknown, fallback = "Une erreur est survenue"): string {
  if (axios.isAxiosError(err)) {
    const detail = err.response?.data?.detail;
    if (typeof detail === "string" && detail) return detail;
    if (err.message) return err.message;
  }
  if (err instanceof Error && err.message) return err.message;
  return fallback;
}

/** Statut HTTP d'une erreur axios, ou undefined si non-axios. */
export function getApiErrorStatus(err: unknown): number | undefined {
  return axios.isAxiosError(err) ? err.response?.status : undefined;
}
