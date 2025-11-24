export async function checkHallucination(context: string, prompt: string, response_text: string) {
    const res = await fetch("http://localhost:8000/check", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ context, prompt, response: response_text })
    });
    return await res.json();
}

export async function fetchMetrics() {
    const res = await fetch("http://localhost:8000/metrics");
    return await res.json();
}