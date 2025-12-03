<script lang="ts">
    import { createEventDispatcher } from 'svelte';
    import { slide } from 'svelte/transition';

    export let isLoading = false;
    export let error: string | null = null;

    let context = "";
    let prompt = "";
    let response = "";

    const dispatch = createEventDispatcher();
    const handleSubmit = () => dispatch('submit', { context, prompt, response });

    // Action tự động co giãn chiều cao
    const autoResize = (node: HTMLTextAreaElement) => {
        const resize = () => {
            node.style.height = 'auto';
            node.style.height = `${node.scrollHeight}px`;
        };
        node.addEventListener('input', resize);
        return { destroy() { node.removeEventListener('input', resize); } };
    };
</script>

<div class="glass-panel">
    <div class="header"><h2>Dữ liệu đầu vào</h2></div>

    <div class="field">
        <label for="c">Context (Ngữ cảnh gốc)</label>
        <textarea id="c" bind:value={context} use:autoResize rows="1" placeholder="Dán văn bản gốc..."></textarea>
    </div>
    <div class="field">
        <label for="p">Prompt (Câu hỏi)</label>
        <textarea id="p" bind:value={prompt} use:autoResize rows="1" placeholder="Người dùng đã hỏi gì?"></textarea>
    </div>
    <div class="field">
        <label for="r">Response (Câu trả lời AI)</label>
        <textarea id="r" bind:value={response} use:autoResize rows="1" placeholder="Câu trả lời cần kiểm chứng..."></textarea>
    </div>

    <button on:click={handleSubmit} disabled={isLoading || !context || !prompt || !response}>
        {#if isLoading}<div class="loader"></div> Đang phân tích...{:else}Kiểm tra ngay{/if}
    </button>

    {#if error}<div class="error" transition:slide>{error}</div>{/if}
</div>

<style>
    .glass-panel { background: var(--glass-bg); border: 1px solid var(--glass-border); backdrop-filter: blur(16px); border-radius: 24px; padding: 2rem; height: 100%; box-shadow: 0 8px 32px rgba(0,0,0,0.3); }
    .header { border-bottom: 1px solid rgba(255,255,255,0.1); margin-bottom: 1.5rem; padding-bottom: 1rem; }
    h2 { margin: 0; font-size: 1.25rem; color: white; }
    .field { margin-bottom: 1.5rem; }
    label { display: block; margin-bottom: 0.5rem; color: #cbd5e1; font-size: 0.9rem; font-weight: 500; }
    textarea { width: 100%; background: rgba(15, 23, 42, 0.6); border: 1px solid #334155; border-radius: 12px; padding: 1rem; color: white; font-size: 1rem; font-family: inherit; transition: all 0.2s; resize: none; overflow: hidden; min-height: 3.5rem; }
    textarea:focus { outline: none; border-color: #818cf8; background: rgba(15, 23, 42, 0.9); box-shadow: 0 0 0 3px rgba(129, 140, 248, 0.2); }
    button { width: 100%; padding: 1rem; background: linear-gradient(135deg, #4f46e5, #9333ea); border: none; border-radius: 12px; color: white; font-weight: 600; cursor: pointer; transition: transform 0.2s, box-shadow 0.2s; display: flex; justify-content: center; align-items: center; gap: 0.5rem; }
    button:hover:not(:disabled) { transform: translateY(-2px); box-shadow: 0 10px 25px rgba(79, 70, 229, 0.4); }
    button:disabled { opacity: 0.6; cursor: not-allowed; }
    .error { margin-top: 1rem; color: #fca5a5; background: rgba(239, 68, 68, 0.2); padding: 1rem; border-radius: 8px; border: 1px solid rgba(239, 68, 68, 0.5); }
    .loader { width: 18px; height: 18px; border: 2px solid rgba(255,255,255,0.3); border-radius: 50%; border-top-color: white; animation: spin 0.8s linear infinite; }
    @keyframes spin { to { transform: rotate(360deg); } }
</style>