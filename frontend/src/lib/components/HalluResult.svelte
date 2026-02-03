<!---frontend/src/lib/components/HalluResult.svelte--->
<script lang="ts">
    import type { HalluOutput } from '$lib/api/api';
    import { ShieldCheck, Ban, AlertOctagon, RotateCcw } from 'lucide-svelte';
    import { fly } from 'svelte/transition';
    import { createEventDispatcher } from 'svelte';

    export let result: HalluOutput;
    const dispatch = createEventDispatcher();

    $: theme = (() => {
        const l = result.label?.toLowerCase() || '';

        if (l.includes('no') || l.includes('entailment')) {
            return { 
                color: 'text-emerald-400', 
                border: 'border-emerald-500', 
                bg: 'from-emerald-950/40', 
                icon: ShieldCheck, 
                title: 'CHÍNH XÁC',
                desc: 'Thông tin hoàn toàn khớp với ngữ cảnh.'
            };
        }
        
        if (l.includes('intrinsic') || l.includes('contradiction')) {
            return { 
                color: 'text-rose-500', 
                border: 'border-rose-500', 
                bg: 'from-rose-950/40', 
                icon: Ban, 
                title: 'MÂU THUẪN',
                desc: 'Thông tin sai lệch so với dữ liệu gốc.'
            };
        }

        return { 
            color: 'text-amber-400', 
            border: 'border-amber-500', 
            bg: 'from-amber-950/40', 
            icon: AlertOctagon, 
            title: 'BỊA ĐẶT',
            desc: 'Thông tin không tồn tại trong ngữ cảnh.'
        };
    })();
</script>

<div in:fly={{ y: 20, duration: 500 }} class="relative z-20 w-full">
    <div class="relative rounded-2xl border {theme.border} bg-gradient-to-br {theme.bg} to-slate-950/80 backdrop-blur-xl p-6 shadow-2xl overflow-hidden">
        
        <div class="flex items-start justify-between gap-6">
            <div class="flex items-center gap-4">
                <div class="relative p-3 rounded-xl bg-white/5 border border-white/10 shadow-inner">
                    <svelte:component this={theme.icon} size={32} class={theme.color} />
                </div>
                <div>
                    <h3 class="text-2xl font-black tracking-wide text-white">{theme.title}</h3>
                    <p class="text-xs text-slate-400">{theme.desc}</p>
                </div>
            </div>

            <div class="text-right">
                <div class="text-3xl font-bold {theme.color}">{(result.confidence * 100).toFixed(0)}%</div>
                <div class="text-[10px] text-slate-500 font-bold uppercase">Độ tin cậy</div>
            </div>
        </div>

        <div class="mt-6 h-1.5 w-full bg-slate-900 rounded-full overflow-hidden">
            <div class="h-full {theme.color.replace('text', 'bg')} shadow-[0_0_10px_currentColor] transition-all duration-1000" style="width: {result.confidence * 100}%"></div>
        </div>

        <div class="mt-6 flex justify-end pt-4 border-t border-white/5">
            <button 
                on:click={() => dispatch('reset')}
                class="flex items-center gap-2 px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-white text-sm font-bold transition-all border border-slate-700 hover:border-indigo-500"
            >
                <RotateCcw size={16} />
                Test Case Tiếp Theo
            </button>
        </div>
    </div>
</div>