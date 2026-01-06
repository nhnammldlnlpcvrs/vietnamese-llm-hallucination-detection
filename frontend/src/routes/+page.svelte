<!---frontend/src/routes/+page.svelte--->
<script lang="ts">
    import Header from '$lib/components/Header.svelte';
    import HalluForm from '$lib/components/HalluForm.svelte';
    import HalluResult from '$lib/components/HalluResult.svelte';
    import { detectHallucination, type HalluInput, type HalluOutput } from '$lib/api/api';
    import { fade } from 'svelte/transition';

    let isLoading = false;
    let error: string | null = null;
    let result: HalluOutput | null = null;

    const handleAnalysis = async (event: CustomEvent<HalluInput>) => {
        const { context, prompt, response } = event.detail;
        if (!context || !prompt || !response) {
            error = "Vui lòng nhập đủ 3 trường!"; return;
        }
        isLoading = true; error = null; result = null;
        try {
            await new Promise(r => setTimeout(r, 500)); // UX delay
            result = await detectHallucination({ context, prompt, response });
        } catch (err: any) {
            error = err.message;
        } finally {
            isLoading = false;
        }
    };
</script>

<div class="container">
    <Header />
    <div class="grid">
        <div class="left"><HalluForm {isLoading} {error} on:submit={handleAnalysis} /></div>
        <div class="right">
            {#if result}
                <HalluResult {result} />
            {:else if !isLoading}
                <div class="empty" in:fade>
                    <div style="font-size: 3rem; margin-bottom: 1rem; opacity: 0.6;">💡</div>
                    <h3>Sẵn sàng phân tích</h3>
                    <p>Nhập thông tin bên trái để bắt đầu kiểm tra.</p>
                </div>
            {:else}
                <div class="skeleton" in:fade>
                    <div class="line w75"></div><div class="line w50"></div><div class="line w100"></div>
                </div>
            {/if}
        </div>
    </div>
</div>

<style>
    .container { max-width: 1200px; margin: 0 auto; padding: 0 2rem 4rem 2rem; }
    .grid { display: grid; grid-template-columns: 1.2fr 1fr; gap: 2rem; align-items: start; }
    @media (max-width: 900px) { .grid { grid-template-columns: 1fr; } }
    .empty { text-align: center; padding: 4rem; background: rgba(255,255,255,0.02); border: 2px dashed rgba(255,255,255,0.1); border-radius: 24px; color: #94a3b8; height: 100%; display: flex; flex-direction: column; justify-content: center; align-items: center; min-height: 400px; }
    .skeleton { padding: 2rem; background: rgba(30, 41, 59, 0.4); border-radius: 24px; height: 400px; display: flex; flex-direction: column; justify-content: center; align-items: center; gap: 1rem; }
    .line { height: 10px; background: rgba(255,255,255,0.05); border-radius: 5px; animation: pulse 1.5s infinite; }
    .w75 { width: 75%; } .w50 { width: 50%; } .w100 { width: 100%; }
    @keyframes pulse { 0%, 100% { opacity: 0.3; } 50% { opacity: 0.6; } }
</style>