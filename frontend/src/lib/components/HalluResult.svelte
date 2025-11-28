<!-- src/lib/components/HalluResult.svelte -->
<script lang="ts" context="module">
  export type HalluOutput = { label: string; confidence: number };
</script>

<script lang="ts">
  import { fly } from "svelte/transition";
  export let result: HalluOutput | null = null;

  function themeFor(label: string) {
    const l = label.toLowerCase();
    if (l.includes("no") || l.includes("none") || l.includes("correct")) {
      return { color: "#34d399", title: "Chính xác (No Hallucination)", desc: "Thông tin phù hợp với ngữ cảnh." };
    } else if (l.includes("intrin")) {
      return { color: "#f43f5e", title: "Mâu thuẫn (Intrinsic)", desc: "Thông tin trái ngược với ngữ cảnh." };
    } else {
      return { color: "#f59e0b", title: "Bịa đặt (Extrinsic)", desc: "Thông tin không có trong ngữ cảnh." };
    }
  }
</script>

{#if result}
  {#key result.label + result.confidence}
    <aside class="card" in:fly={{ y: 20, duration: 400 }} aria-live="polite">
      <div style="display:flex;justify-content:space-between;align-items:center">
        <div>
          <div class="badge">Kết quả</div>
          <h3 style="margin:0;color:{themeFor(result.label).color}">{themeFor(result.label).title}</h3>
          <div class="muted small">{themeFor(result.label).desc}</div>
        </div>
        <div style="text-align:right">
          <div style="font-weight:800;font-size:1.5rem">{(result.confidence*100).toFixed(1)}%</div>
          <div class="muted small">Confidence</div>
        </div>
      </div>

      <div style="margin-top:0.9rem">
        <div style="height:12px;background:rgba(255,255,255,0.04);border-radius:999px;overflow:hidden;border:1px solid rgba(255,255,255,0.02)">
          <div style="height:100%;transition:width 0.9s ease;background:{themeFor(result.label).color};width:{Math.max(3,result.confidence*100)}%"></div>
        </div>
      </div>

      <div style="display:flex;gap:0.5rem;flex-wrap:wrap;margin-top:0.9rem">
        <div class="chip">Label raw: <strong style="margin-left:6px">{result.label}</strong></div>
        <div class="chip">Model: Vistral7B + ensemble</div>
        <div class="chip">Time: {new Date().toLocaleString()}</div>
      </div>
    </aside>
  {/key}
{:else}
  <div class="card muted center" style="min-height:180px">Sẵn sàng — nhập dữ liệu để kiểm tra</div>
{/if}

<style>
  .chip{ padding:6px 10px;border-radius:10px;background:rgba(255,255,255,0.02);border:1px solid rgba(255,255,255,0.02); color:var(--muted); font-size:0.85rem;}
</style>