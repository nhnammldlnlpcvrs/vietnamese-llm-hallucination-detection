<script lang="ts">
  import { onMount } from 'svelte';
  import { writable } from 'svelte/store';

  // Stores cho dữ liệu form
  let context = '';
  let prompt = '';
  let responseText = '';
  
  let prediction: string | null = null;
  let loading = false;
  let error: string | null = null;

  async function submitForm() {
    prediction = null;
    error = null;
    loading = true;

    try {
      const res = await fetch('http://localhost:8000/api/predict', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ context, prompt, response: responseText })
      });

      if (!res.ok) {
        throw new Error(`Server error: ${res.status}`);
      }

      const data = await res.json();
      prediction = data.label; // backend trả về { label: "no" | "intrinsic" | "extrinsic" }
    } catch (err: any) {
      error = err.message;
    } finally {
      loading = false;
    }
  }
</script>

<main class="p-6 max-w-xl mx-auto">
  <h1 class="text-2xl font-bold mb-4">LLM Hallucination Detection</h1>

  <div class="mb-4">
    <label class="block font-semibold">Context:</label>
    <textarea bind:value={context} rows="3" class="w-full border p-2 rounded"></textarea>
  </div>

  <div class="mb-4">
    <label class="block font-semibold">Prompt:</label>
    <textarea bind:value={prompt} rows="3" class="w-full border p-2 rounded"></textarea>
  </div>

  <div class="mb-4">
    <label class="block font-semibold">Response:</label>
    <textarea bind:value={responseText} rows="3" class="w-full border p-2 rounded"></textarea>
  </div>

  <button on:click={submitForm} class="bg-blue-600 text-white px-4 py-2 rounded" disabled={loading}>
    {loading ? 'Predicting...' : 'Submit'}
  </button>

  {#if prediction}
    <p class="mt-4 font-bold">Prediction: {prediction}</p>
  {/if}

  {#if error}
    <p class="mt-4 text-red-600 font-bold">Error: {error}</p>
  {/if}
</main>

<style>
  textarea:focus { outline: none; border-color: #2563eb; }
</style>