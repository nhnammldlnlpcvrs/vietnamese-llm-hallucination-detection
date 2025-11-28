// src/lib/api/api.ts
export interface HalluInput {
  context: string;
  prompt: string;
  response: string;
}

export interface HalluOutput {
  label: string;
  confidence: number; // 0..1
}

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000/api/v1/detect";

async function parseJsonSafe(res: Response) {
  const txt = await res.text();
  try { return JSON.parse(txt); } catch { return txt; }
}

export async function detectHallucination(data: HalluInput): Promise<HalluOutput> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 20000);
  try {
    const res = await fetch(API_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
      signal: controller.signal
    });

    const payload = await parseJsonSafe(res);
    if (!res.ok) {
      const msg = (payload && payload.detail) ? payload.detail : `Server error ${res.status}`;
      throw new Error(msg);
    }

    // normalize
    const label = payload?.label ?? payload?.result ?? "none";
    const confidence = typeof payload?.confidence === "number" ? payload.confidence : (Number(payload?.score) || 1);
    return { label: String(label), confidence: Math.max(0, Math.min(1, Number(confidence))) };
  } catch (e: any) {
    if (e.name === "AbortError") throw new Error("Yêu cầu bị timeout (20s)");
    throw e;
  } finally {
    clearTimeout(timeout);
  }
}