<!---frontend/src/lib/components/HalluResult.svelte--->
<script lang="ts">
    import type { HalluOutput } from '$lib/api/api';
    import { fly, slide } from 'svelte/transition';

    export let result: HalluOutput;

    const getTheme = (label: string) => {
        const l = label.toLowerCase();
        if (l.includes("no")) return { color: "#34d399", bg: "rgba(52, 211, 153, 0.1)", icon: "✅", title: "Chính xác", desc: "Thông tin hoàn toàn khớp với ngữ cảnh." };
        if (l.includes("intrinsic")) return { color: "#f43f5e", bg: "rgba(244, 63, 94, 0.1)", icon: "🚫", title: "Mâu thuẫn (Intrinsic)", desc: "Thông tin sai lệch/ngược lại với ngữ cảnh gốc." };
        return { color: "#fbbf24", bg: "rgba(251, 191, 36, 0.1)", icon: "⚠️", title: "Bịa đặt (Extrinsic)", desc: "Thông tin không có trong ngữ cảnh (có thể đúng ngoài đời)." };
    };

    $: theme = getTheme(result.label);
</script>

<div class="glass-panel" style="background: {theme.bg}; border-color: {theme.color}" in:fly={{ y: 20 }}>
    <div class="icon-wrapper">{theme.icon}</div>
    <h3 style="color: {theme.color}">{theme.title}</h3>
    <p class="desc">{theme.desc}</p>
    
    <div class="divider"></div>

    <div class="bar-container">
        <div class="label"><span>Độ tin cậy</span><span style="color: {theme.color}">{(result.confidence * 100).toFixed(1)}%</span></div>
        <div class="track"><div class="fill" style="width: {result.confidence * 100}%; background: {theme.color}" in:slide={{ axis: 'x', duration: 1000 }}></div></div>
    </div>
</div>

<style>
    .glass-panel { backdrop-filter: blur(16px); border-radius: 24px; padding: 2rem; height: 100%; border: 1px solid; text-align: center; box-shadow: 0 8px 32px rgba(0,0,0,0.3); }
    .icon-wrapper { font-size: 4rem; margin-bottom: 1rem; animation: tada 1s ease-in-out; }
    h3 { font-size: 2rem; margin: 0 0 0.5rem 0; font-weight: 700; }
    .desc { color: #cbd5e1; margin-bottom: 0; }
    .divider { height: 1px; background: rgba(255,255,255,0.1); margin: 2rem 0; }
    .bar-container { text-align: left; background: rgba(0,0,0,0.2); padding: 1.5rem; border-radius: 16px; }
    .label { display: flex; justify-content: space-between; margin-bottom: 0.5rem; font-weight: 600; font-size: 0.9rem; }
    .track { height: 10px; background: rgba(255,255,255,0.1); border-radius: 5px; overflow: hidden; }
    .fill { height: 100%; border-radius: 5px; transition: width 1s ease-out; }
    @keyframes tada { 0% { transform: scale(1); } 10%, 20% { transform: scale(0.9) rotate(-3deg); } 30%, 50%, 70%, 90% { transform: scale(1.1) rotate(3deg); } 40%, 60%, 80% { transform: scale(1.1) rotate(-3deg); } 100% { transform: scale(1) rotate(0); } }
</style>