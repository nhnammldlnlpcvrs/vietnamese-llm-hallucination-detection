<!---frontend/src/lib/components/HalluForm.svelte--->
<script lang="ts">
    import { createEventDispatcher } from 'svelte';
    import { Zap, FileText, MessageSquare, Terminal, Loader2 } from 'lucide-svelte';

    export let isLoading = false;
    
    export let context = '';
    export let prompt = '';
    export let response = '';

    const dispatch = createEventDispatcher();
    const handleSubmit = () => {
        if (context && prompt && response) dispatch('submit', { context, prompt, response });
    };
</script>

<div class="relative z-10 space-y-6 max-w-3xl mx-auto">
    <div class="group relative rounded-2xl bg-slate-900/40 border border-white/10 p-1 transition-all hover:border-indigo-500/50 hover:shadow-[0_0_20px_rgba(99,102,241,0.1)]">
        <div class="absolute -top-3 left-4 px-2 bg-[#030712] text-xs font-mono text-indigo-400 flex items-center gap-2">
            <FileText size={12} /> CONTEXT_SOURCE
        </div>
        <textarea 
            bind:value={context} 
            placeholder="Nhập dữ liệu nguồn (Source Knowledge)..."
            class="w-full h-32 bg-transparent p-4 text-sm text-slate-300 placeholder:text-slate-600 outline-none resize-none font-mono"
        ></textarea>
    </div>

    <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div class="group relative rounded-2xl bg-slate-900/40 border border-white/10 p-1 transition-all hover:border-pink-500/50 hover:shadow-[0_0_20px_rgba(236,72,153,0.1)]">
            <div class="absolute -top-3 left-4 px-2 bg-[#030712] text-xs font-mono text-pink-400 flex items-center gap-2">
                <MessageSquare size={12} /> USER_QUERY
            </div>
            <textarea 
                bind:value={prompt} 
                placeholder="Người dùng hỏi gì?"
                class="w-full h-32 bg-transparent p-4 text-sm text-slate-300 placeholder:text-slate-600 outline-none resize-none font-mono"
            ></textarea>
        </div>

        <div class="group relative rounded-2xl bg-slate-900/40 border border-white/10 p-1 transition-all hover:border-cyan-500/50 hover:shadow-[0_0_20px_rgba(6,182,212,0.1)]">
            <div class="absolute -top-3 left-4 px-2 bg-[#030712] text-xs font-mono text-cyan-400 flex items-center gap-2">
                <Terminal size={12} /> AI_OUTPUT
            </div>
            <textarea 
                bind:value={response} 
                placeholder="Câu trả lời của AI..."
                class="w-full h-32 bg-transparent p-4 text-sm text-slate-300 placeholder:text-slate-600 outline-none resize-none font-mono"
            ></textarea>
        </div>
    </div>

    <div class="flex justify-center pt-4">
        <button 
            on:click={handleSubmit}
            disabled={isLoading || !context || !prompt || !response}
            class="relative group px-8 py-4 bg-gradient-to-r from-indigo-600 to-pink-600 rounded-full text-white font-bold shadow-lg shadow-indigo-500/40 hover:shadow-indigo-500/60 transition-all active:scale-95 disabled:opacity-50 disabled:cursor-not-allowed overflow-hidden"
        >
            <div class="absolute inset-0 bg-white/20 group-hover:translate-x-full transition-transform duration-500 -skew-x-12 -translate-x-full"></div>
            <div class="flex items-center gap-2 relative z-10">
                {#if isLoading}
                    <Loader2 size={20} class="animate-spin" />
                    <span>ĐANG XỬ LÝ DỮ LIỆU...</span>
                {:else}
                    <Zap size={20} class="fill-white" />
                    <span>KÍCH HOẠT QUÉT</span>
                {/if}
            </div>
        </button>
    </div>
</div>