// src/stores/index.ts
import { writable } from "svelte/store";

export type HallucinationResult = {
  id: string;
  type: "intrinsic" | "extrinsic" | "none";
  confidence: number;
  rawLabel?: string;
  ts: string;
  context?: string;
  prompt?: string;
  response?: string;
};

export const latestResult = writable<HallucinationResult | null>(null);
export const history = writable<HallucinationResult[]>([]);

export function pushResult(r: HallucinationResult) {
  latestResult.set(r);
  history.update(h => [r, ...h].slice(0, 100));
}
