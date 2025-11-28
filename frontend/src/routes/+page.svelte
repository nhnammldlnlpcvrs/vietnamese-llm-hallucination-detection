<!-- src/routes/+page.svelte -->
<script lang="ts">
  import Header from "$lib/components/Header.svelte";
  import HalluForm from "$lib/components/HalluForm.svelte";
  import HalluResult from "$lib/components/HalluResult.svelte";
  import { detectHallucination } from "$lib/api/api";
  import { pushResult } from "$lib/stores";
  import type { HalluOutput } from "$lib/components/HalluResult.svelte";

  let isLoading = false;
  let error: string | null = null;
  let result: HalluOutput | null = null;

  async function onSubmit(e: CustomEvent) {
    error = null;
    result = null;
    isLoading = true;
    try {
      const payload = e.detail;
      // slight UX delay
      await new Promise(r => setTimeout(r, 120));
      const r = await detectHallucination(payload);
      result = r;
      pushResult({
        id: cryptoRandomId(),
        type: r.label.toLowerCase().includes("intrin") ? "intrinsic" : (r.label.toLowerCase().includes("no") ? "none" : "extrinsic"),
        confidence: r.confidence,
        rawLabel: r.label,
        ts: new Date().toISOString(),
        context: payload.context,
        prompt: payload.prompt,
        response: payload.response
      });
    } catch (err: any) {
      error = err?.message ?? String(err);
    } finally {
      isLoading = false;
    }
  }

  function onError(e: CustomEvent) {
    error = e.detail?.message ?? "Lỗi nhập liệu";
  }

  function cryptoRandomId() {
    return (crypto && crypto.getRandomValues) ? Array.from(crypto.getRandomValues(new Uint8Array(6))).map(n => n.toString(16).padStart(2,'0')).join('') : String(Date.now());
  }
</script>

<Header />

<section class="grid-2">
  <div>
    <HalluForm {isLoading} {error} on:submit={onSubmit} on:error={onError} />
  </div>

  <aside>
    <HalluResult {result} />
  </aside>
</section>