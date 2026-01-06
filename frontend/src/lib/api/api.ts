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
    try {
        console.log("Đang gọi API:", API_URL); // Log để check
        const res = await fetch(API_URL, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(data),
        });

        if (!res.ok) {
            throw new Error(`Lỗi ${res.status}: ${res.statusText}`);
        }
        return await res.json();
    } catch (error) {
        console.error("API Error:", error);
        throw error;
    }
};