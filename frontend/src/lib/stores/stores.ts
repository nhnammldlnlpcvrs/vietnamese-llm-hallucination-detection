// frontend/src/lib/stores/stores.ts
import { writable } from "svelte/store";
import type { HalluInput, HalluOutput } from "$lib/api/api";

export interface HistoryItem extends HalluInput {
    id: string;
    result: HalluOutput;
    timestamp: Date;
}

export const history = writable<HistoryItem[]>([]);
export const currentResult = writable<HalluOutput | null>(null);

export function addToHistory(input: HalluInput, result: HalluOutput) {
    history.update(h => [{
        ...input,
        id: crypto.randomUUID(),
        result,
        timestamp: new Date()
    }, ...h].slice(0, 50));
}