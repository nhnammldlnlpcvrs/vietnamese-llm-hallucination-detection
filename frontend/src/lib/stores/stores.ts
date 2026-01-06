// frontend/src/lib/stores/stores.ts
import { writable } from "svelte/store";

export interface HallucinationResult {
    type: "intrinsic" | "extrinsic" | "none";
    confidence: number;
    timestamp: string;
}

export const latestResult = writable<HallucinationResult | null>(null);
export const history = writable<HallucinationResult[]>([]);
export const metrics = writable({
    dataDrift: [],
    modelConfidence: [],
    requestTimeline: []
});