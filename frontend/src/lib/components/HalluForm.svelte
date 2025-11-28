<!-- src/lib/components/HalluForm.svelte -->
<script lang="ts">
  import { createEventDispatcher } from "svelte";
  export let isLoading = false;
  export let error: string | null = null;

  const dispatch = createEventDispatcher();

  let context = "";
  let prompt = "";
  let responseText = "";

  function submit(e?: Event) {
    e?.preventDefault();
    if (!context.trim() || !prompt.trim() || !responseText.trim()) {
      dispatch("error", { message: "Vui lòng điền đủ Context, Prompt và Response." });
      return;
    }
    dispatch("submit", { context: context.trim(), prompt: prompt.trim(), response: responseText.trim() });
  }

  function clearAll() {
    context = "";
    prompt = "";
    responseText = "";
    dispatch("clear");
  }
</script>

<form class="card" on:submit|preventDefault={submit} aria-labelledby="halluform-title">
  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:0.6rem">
    <div>
      <h3 id="halluform-title" style="margin:0">Dữ liệu đầu vào</h3>
      <div class="muted small">Paste context / prompt / response để phân tích</div>
    </div>
    <div class="badge">Input</div>
  </div>

  <label for="context" class="small">Context (Ngữ cảnh)</label>
  <textarea id="context" bind:value={context} rows="6" placeholder="Dán đoạn văn bản gốc hoặc tài liệu tham khảo..." />

  <label for="prompt" class="small">Prompt (Câu hỏi)</label>
  <input id="prompt" type="text" bind:value={prompt} placeholder="Người dùng đã hỏi gì?" />

  <label for="response" class="small">Response (Câu trả lời LLM)</label>
  <textarea id="response" bind:value={responseText} rows="4" placeholder="Câu trả lời AI cần kiểm chứng..." />

  {#if error}
    <div style="margin-top:0.6rem;color:#fecaca;background: rgba(255,0,0,0.04);padding:0.5rem;border-radius:8px">{error}</div>
  {/if}

  <div style="display:flex;justify-content:flex-end;gap:0.6rem;margin-top:0.8rem">
    <button type="button" class="ghost-btn" on:click={clearAll} disabled={isLoading}>Xóa</button>
    <button type="submit" class="primary-btn" disabled={isLoading}>
      {#if isLoading}
        <span class="dot-loader" aria-hidden="true"></span> Đang phân tích...
      {:else}
        Kiểm tra ngay
      {/if}
    </button>
  </div>
</form>

<style>
  textarea, input {
    width:100%;
    padding:0.75rem;
    border-radius:10px;
    border:1px solid rgba(255,255,255,0.04);
    background: rgba(15,23,42,0.55);
    color:var(--text);
    font-size:0.95rem;
    margin-top:0.3rem;
  }
  .primary-btn {
    padding:0.65rem 1rem;
    border-radius:10px;
    border:none;
    background: linear-gradient(90deg,var(--accent1),var(--accent2));
    color:white;
    font-weight:700;
  }
  .ghost-btn {
    padding:0.55rem 0.9rem;
    border-radius:10px;
    background:transparent;
    border:1px solid rgba(255,255,255,0.04);
    color:var(--muted);
    font-weight:700;
  }
  .primary-btn:disabled, .ghost-btn:disabled { opacity:0.6; cursor:not-allowed; }
  .dot-loader {
    width:14px;height:14px;border-radius:50%;display:inline-block;margin-right:8px;
    border:2px solid rgba(255,255,255,0.12);border-top-color:white;animation:spin .7s linear infinite;
  }
  @keyframes spin{ to{ transform:rotate(360deg);} }
</style>