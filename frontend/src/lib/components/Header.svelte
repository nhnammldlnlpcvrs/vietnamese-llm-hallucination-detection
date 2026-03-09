<!---frontend/src/lib/components/Header.svelte--->
<script lang="ts">
    import { Bot, Sparkles } from 'lucide-svelte';
</script>

<header class="flex justify-center py-8 relative z-10">
    <div class="flex items-center gap-3 px-6 py-3 rounded-full bg-white/5 border border-white/10 backdrop-blur-md shadow-[0_0_15px_rgba(99,102,241,0.3)]">
        <div class="relative">
            <Bot size={28} class="text-indigo-400" />
            <Sparkles size={12} class="absolute -top-1 -right-1 text-pink-400 animate-pulse" />
        </div>
        <h1 class="text-xl font-bold tracking-tight text-white">
            AI <span class="text-transparent bg-clip-text bg-gradient-to-r from-indigo-400 to-pink-400">Guardian</span>
        </h1>
    </div>
</header>