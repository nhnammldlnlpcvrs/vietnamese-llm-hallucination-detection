<!-- src/lib/components/Header.svelte -->
<script lang="ts">
  import { fly } from "svelte/transition";
</script>

<header class="card" in:fly={{ y: -10, duration: 400 }} style="display:flex;justify-content:space-between;align-items:center;margin-bottom:1rem;">
  <div style="display:flex;gap:0.75rem;align-items:center">
    <div style="font-size:1.6rem">✨</div>
    <div>
      <div style="font-weight:800;font-size:1.15rem">Hallu<strong style="background:linear-gradient(90deg,var(--accent1),var(--accent2));-webkit-background-clip:text;-webkit-text-fill-color:transparent;">Detector</strong></div>
      <div class="muted small">Hệ thống phát hiện ảo giác LLM — Hybrid Guardrails</div>
    </div>
  </div>

  <nav style="display:flex;gap:0.5rem;align-items:center">
    <a class="badge" href="https://github.com/" target="_blank" rel="noopener noreferrer">Docs</a>
    <button class="badge" on:click={() => alert('Tùy chọn')}>Tùy chọn</button>
  </nav>
</header>