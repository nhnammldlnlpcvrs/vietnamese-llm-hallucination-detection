<!---frontend/src/routes/+page.svelte--->
<script lang="ts">
    import Header from '$lib/components/Header.svelte';
    import HalluForm from '$lib/components/HalluForm.svelte';
    import HalluResult from '$lib/components/HalluResult.svelte';
    import { detectHallucination } from '$lib/api/api';
    import { addToHistory, currentResult, history } from '$lib/stores/stores';
    import { History, Clock, Trash2 } from 'lucide-svelte';
    import { slide } from 'svelte/transition';

    let isLoading = false;
    let error: string | null = null;
    let formContext = '', formPrompt = '', formResponse = '';

    async function handleAnalysis(event: CustomEvent) {
        isLoading = true; error = null; currentResult.set(null);
        try {
            await new Promise(r => setTimeout(r, 400));
            const res = await detectHallucination(event.detail);
            currentResult.set(res);
            addToHistory(event.detail, res);
        } catch (e: any) {
            error = "Lỗi kết nối Server: " + e.message;
        } finally {
            isLoading = false;
        }
    }

    function restoreItem(item: any) {
        formContext = item.context;
        formPrompt = item.prompt;
        formResponse = item.response;
        currentResult.set(item.result);
        error = null;
    }

    function resetFlow() {
        currentResult.set(null);
    }

    const getHistoryBadge = (label: string) => {
        const l = label.toLowerCase();
        if (l.includes('no') || l.includes('entail')) 
            return { text: 'CHÍNH XÁC', css: 'text-emerald-400 border-emerald-500/30 bg-emerald-500/10' };
        if (l.includes('intrinsic') || l.includes('contra')) 
            return { text: 'MÂU THUẪN', css: 'text-rose-400 border-rose-500/30 bg-rose-500/10' };
        return { text: 'BỊA ĐẶT', css: 'text-amber-400 border-amber-500/30 bg-amber-500/10' };
    };
</script>

<div class="fixed inset-0 bg-[#030712] text-slate-200 font-sans selection:bg-indigo-500/30">
    <div class="absolute inset-0 bg-[url('https://grainy-gradients.vercel.app/noise.svg')] opacity-10 pointer-events-none"></div>
    <div class="absolute top-0 left-0 w-full h-[500px] bg-indigo-900/10 blur-[120px] rounded-full pointer-events-none"></div>
</div>

<div class="relative z-10 h-screen flex flex-col overflow-hidden">
    <Header />

    <div class="flex-1 flex overflow-hidden max-w-[1600px] mx-auto w-full px-4 gap-6 pb-6">
        
        <aside class="w-80 hidden lg:flex flex-col bg-slate-900/30 border border-white/5 rounded-2xl backdrop-blur-md overflow-hidden shadow-2xl">
            <div class="p-4 border-b border-white/5 flex items-center justify-between text-indigo-400">
                <div class="flex items-center gap-2">
                    <History size={18} />
                    <span class="text-xs font-bold uppercase tracking-widest">Lịch sử</span>
                </div>
                <span class="text-[10px] bg-white/5 px-2 py-0.5 rounded-full text-slate-500">{$history.length}</span>
            </div>
            
            <div class="flex-1 overflow-y-auto p-3 space-y-2 custom-scrollbar">
                {#each $history as item (item.id)}
                    {@const badge = getHistoryBadge(item.result.label)}
                    <button 
                        on:click={() => restoreItem(item)}
                        class="w-full text-left p-3 rounded-xl border border-transparent bg-white/[0.02] hover:bg-white/5 hover:border-white/10 transition-all group relative overflow-hidden"
                    >
                        <div class="flex justify-between items-center mb-2">
                            <span class="text-[10px] font-mono text-slate-500 opacity-70">
                                {new Date(item.timestamp).toLocaleTimeString([], {hour:'2-digit', minute:'2-digit'})}
                            </span>
                            <span class="text-[9px] font-black px-1.5 py-0.5 rounded border {badge.css}">
                                {badge.text}
                            </span>
                        </div>
                        <p class="text-xs text-slate-300 font-medium truncate group-hover:text-white transition-colors">
                            {item.prompt}
                        </p>
                        
                        <div class="absolute inset-y-0 left-0 w-1 bg-indigo-500 opacity-0 -translate-x-full group-hover:translate-x-0 group-hover:opacity-100 transition-all duration-300"></div>
                    </button>
                {:else}
                    <div class="flex flex-col items-center justify-center h-40 text-slate-600 opacity-50">
                        <Clock size={24} class="mb-2" />
                        <p class="text-xs">Chưa có dữ liệu phân tích</p>
                    </div>
                {/each}
            </div>
        </aside>

        <main class="flex-1 flex flex-col gap-6 overflow-y-auto custom-scrollbar pr-2">
            {#if $currentResult}
                <div in:slide={{ duration: 400 }} class="mb-2">
                    <HalluResult result={$currentResult} on:reset={resetFlow} />
                </div>
            {/if}

            <div class="bg-slate-900/20 border border-white/5 rounded-2xl p-6 backdrop-blur-sm transition-all duration-500 {$currentResult ? 'opacity-50 grayscale hover:opacity-100 hover:grayscale-0' : 'opacity-100'}">
                <HalluForm 
                    bind:context={formContext}
                    bind:prompt={formPrompt}
                    bind:response={formResponse}
                    {isLoading} 
                    on:submit={handleAnalysis} 
                />
            </div>

            {#if error}
                <div class="p-4 bg-red-500/10 border border-red-500/20 rounded-xl text-red-400 text-sm text-center font-mono">
                    ⚠ {error}
                </div>
            {/if}
        </main>
    </div>
</div>

<style>
    .custom-scrollbar::-webkit-scrollbar { width: 5px; }
    .custom-scrollbar::-webkit-scrollbar-track { background: transparent; }
    .custom-scrollbar::-webkit-scrollbar-thumb { background: #1e293b; border-radius: 10px; }
    .custom-scrollbar::-webkit-scrollbar-thumb:hover { background: #475569; }
</style>