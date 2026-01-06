<!---frontend/src/lib/components/Header.svelte--->
<script>
    import { fly } from 'svelte/transition';
</script>

<header in:fly={{ y: -20, duration: 800 }}>
    <div class="logo">
        <span class="icon">✨</span>
        <h1>Hallu<span class="highlight">Detector</span></h1>
    </div>
    <p>Hệ thống phát hiện ảo giác LLM Tiếng Việt (Hybrid Guardrails)</p>
</header>

<style>
    header { text-align: center; margin-bottom: 3rem; padding-top: 2rem; }
    .logo { display: flex; justify-content: center; gap: 0.5rem; align-items: center; margin-bottom: 0.5rem; }
    .icon { font-size: 2.5rem; animation: pulse 3s infinite; }
    h1 { 
        font-size: 3rem; font-weight: 800; margin: 0; 
        background: linear-gradient(to right, #fff, #94a3b8);
        background-clip: text; -webkit-background-clip: text; 
        -webkit-text-fill-color: transparent; color: transparent;
    }
    .highlight { 
        background: linear-gradient(135deg, #6366f1, #a855f7);
        background-clip: text; -webkit-background-clip: text; 
        -webkit-text-fill-color: transparent; color: transparent;
    }
    p { color: #94a3b8; font-size: 1.1rem; margin: 0; }
    @keyframes pulse { 0%, 100% { transform: scale(1); } 50% { transform: scale(1.1); } }
</style>