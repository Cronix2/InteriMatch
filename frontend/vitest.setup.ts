import "@testing-library/jest-dom/vitest";
import { vi, afterEach } from "vitest";
import { cleanup } from "@testing-library/react";

// Mock global de l'API : tous les composants importent depuis @/lib/api,
// on évite ainsi de tester des appels HTTP réels dans les smoke tests.
vi.mock("@/lib/api");

// Cleanup DOM between tests
afterEach(() => {
  cleanup();
});

// jsdom n'implémente pas matchMedia : stub minimal nécessaire pour
// page.tsx (gestion du thème système).
Object.defineProperty(window, "matchMedia", {
  writable: true,
  value: vi.fn().mockImplementation((query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })),
});

// Stub de localStorage déterministe pour les tests qui touchent au token JWT.
const localStorageMock: Storage = (() => {
  let store: Record<string, string> = {};
  return {
    getItem: (key) => store[key] ?? null,
    setItem: (key, value) => {
      store[key] = String(value);
    },
    removeItem: (key) => {
      delete store[key];
    },
    clear: () => {
      store = {};
    },
    key: (index) => Object.keys(store)[index] ?? null,
    get length() {
      return Object.keys(store).length;
    },
  };
})();

Object.defineProperty(window, "localStorage", {
  writable: true,
  value: localStorageMock,
});
