// frontend/src/lib/api/api.ts
export interface HalluInput {
    context: string;
    prompt: string;
    response: string;
}

export interface HalluOutput {
    label: string;
    confidence: number;
}

const API_URL = "http://localhost:8000/api/predict";

export const detectHallucination = async (data: HalluInput): Promise<HalluOutput> => {
    const res = await fetch(API_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data),
    });

    if (!res.ok) throw new Error(`Lỗi hệ thống (${res.status})`);
    return await res.json();
};