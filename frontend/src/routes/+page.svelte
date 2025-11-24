<script lang="ts">
  import { fade, fly, slide } from 'svelte/transition';
  import { quintOut } from 'svelte/easing';

  // --- State Variables ---
  let context = '';
  let prompt = '';
  let llmResponse = '';
  
  let loading = false;
  let prediction: string | null = null;
  let confidence: number | null = null; // Thêm biến lưu độ tin cậy
  let error: string | null = null;

  // --- API Call ---
  async function detectHallucination() {
    if (!context || !prompt || !llmResponse) {
      error = "Vui lòng nhập đầy đủ thông tin trước khi kiểm tra.";
      return;
    }

    loading = true;
    error = null;
    prediction = null;
    confidence = null; // Reset confidence

    try {
      const res = await fetch('http://localhost:8000/api/predict', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ context, prompt, response: llmResponse })
      });

      if (!res.ok) throw new Error('Server error');
      
      const data = await res.json();
      
      // Lưu kết quả từ Backend
      prediction = data.label;
      confidence = data.confidence; 

    } catch (err) {
      error = "Không thể kết nối tới Server API.";
      console.error(err);
    } finally {
      loading = false;
    }
  }

  // --- UI Configuration Helper ---
  function getResultConfig(label: string) {
    const l = label.toLowerCase();
    
    // 1. Trường hợp Không ảo giác (Xanh)
    if (l.includes('no')) return { 
      color: 'from-emerald-500 to-teal-500', 
      bg: 'bg-emerald-50 text-emerald-900 border-emerald-200',
      icon: '✅', // Đã thêm icon
      text: 'Chính xác (No Hallucination)',
      desc: 'Thông tin khớp hoàn toàn với ngữ cảnh.'
    };
    
    // 2. Trường hợp Mâu thuẫn (Vàng)
    if (l.includes('intrinsic')) return { 
      color: 'from-amber-500 to-orange-500', 
      bg: 'bg-amber-50 text-amber-900 border-amber-200',
      icon: '⚠️', // Đã thêm icon
      text: 'Mâu thuẫn (Intrinsic)',
      desc: 'Mô hình bịa ra thông tin trái ngược với ngữ cảnh.'
    };
    
    // 3. Trường hợp Bịa đặt ngoài luồng (Đỏ)
    return { 
      color: 'from-rose-500 to-red-600', 
      bg: 'bg-rose-50 text-rose-900 border-rose-200',
      icon: '🚨', // Đã thêm icon
      text: 'Bịa đặt (Extrinsic)',
      desc: 'Thông tin không tồn tại trong ngữ cảnh nguồn.'
    };
  }
</script>

<!-- Giao diện chính -->
<div class="min-h-screen bg-gradient-to-br from-slate-50 via-slate-100 to-slate-200 flex items-center justify-center p-4 font-sans text-slate-800 relative overflow-hidden">
  
  <!-- Hiệu ứng nền (Blobs) -->
  <div class="absolute top-[-10%] left-[-10%] w-96 h-96 bg-purple-300 rounded-full mix-blend-multiply filter blur-3xl opacity-30 animate-blob"></div>
  <div class="absolute top-[-10%] right-[-10%] w-96 h-96 bg-yellow-300 rounded-full mix-blend-multiply filter blur-3xl opacity-30 animate-blob animation-delay-2000"></div>
  <div class="absolute -bottom-32 left-20 w-96 h-96 bg-pink-300 rounded-full mix-blend-multiply filter blur-3xl opacity-30 animate-blob animation-delay-4000"></div>

  <!-- Card trung tâm -->
  <main class="relative w-full max-w-3xl bg-white/70 backdrop-blur-xl border border-white/50 shadow-2xl rounded-3xl p-8 md:p-10 overflow-hidden">
    
    <!-- Header -->
    <header class="text-center mb-10">
      <div class="inline-block p-3 rounded-2xl bg-indigo-100 text-indigo-600 mb-4 shadow-sm">
        <svg xmlns="http://www.w3.org/2000/svg" class="h-8 w-8" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
          <path stroke-linecap="round" stroke-linejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
        </svg>
      </div>
      <h1 class="text-4xl font-extrabold bg-clip-text text-transparent bg-gradient-to-r from-indigo-600 to-purple-600 mb-2">
        Hallucination Detector
      </h1>
      <p class="text-slate-500 font-medium">Phát hiện ảo giác trong mô hình ngôn ngữ tiếng Việt</p>
    </header>

    <!-- Form Input -->
    <div class="space-y-6">
      <div class="group">
        <label for="context" class="block text-sm font-semibold text-slate-700 mb-2 ml-1">📄 Context (Ngữ cảnh)</label>
        <textarea 
          id="context" 
          bind:value={context} 
          class="w-full p-4 bg-white border border-slate-200 rounded-xl focus:ring-4 focus:ring-indigo-500/10 focus:border-indigo-500 transition-all duration-300 outline-none shadow-sm hover:shadow-md resize-y min-h-[100px]"
          placeholder="Dán đoạn văn bản gốc vào đây..."
        ></textarea>
      </div>

      <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div class="group">
          <label for="prompt" class="block text-sm font-semibold text-slate-700 mb-2 ml-1">❓ Prompt (Câu hỏi)</label>
          <input 
            type="text" 
            id="prompt" 
            bind:value={prompt} 
            class="w-full p-4 bg-white border border-slate-200 rounded-xl focus:ring-4 focus:ring-indigo-500/10 focus:border-indigo-500 transition-all duration-300 outline-none shadow-sm hover:shadow-md"
            placeholder="Người dùng hỏi gì?"
          />
        </div>

        <div class="group">
          <label for="response" class="block text-sm font-semibold text-slate-700 mb-2 ml-1">🤖 Response (Câu trả lời)</label>
          <textarea 
            id="response" 
            bind:value={llmResponse} 
            rows="1"
            class="w-full p-4 bg-white border border-slate-200 rounded-xl focus:ring-4 focus:ring-indigo-500/10 focus:border-indigo-500 transition-all duration-300 outline-none shadow-sm hover:shadow-md min-h-[58px]"
            placeholder="LLM trả lời gì?"
          ></textarea>
        </div>
      </div>

      {#if error}
        <div transition:slide class="p-4 rounded-xl bg-red-50 text-red-600 border border-red-100 flex items-center gap-3">
          <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
            <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clip-rule="evenodd" />
          </svg>
          {error}
        </div>
      {/if}

      <button 
        on:click={detectHallucination} 
        disabled={loading}
        class="w-full py-4 px-6 rounded-xl bg-gradient-to-r from-indigo-600 to-purple-600 text-white font-bold text-lg shadow-lg shadow-indigo-500/30 hover:shadow-indigo-500/50 hover:scale-[1.02] active:scale-[0.98] transition-all duration-300 disabled:opacity-70 disabled:cursor-not-allowed flex items-center justify-center gap-3"
      >
        {#if loading}
          <svg class="animate-spin h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
          </svg>
          Đang phân tích...
        {:else}
          <span>🔍 Kiểm tra ngay</span>
        {/if}
      </button>
    </div>

    <!-- Kết quả -->
    {#if prediction}
      {@const config = getResultConfig(prediction)}
      
      <div class="mt-10 border-t border-slate-100 pt-8" in:fly="{{ y: 20, duration: 800, easing: quintOut }}">
        <h3 class="text-lg font-bold text-slate-800 mb-4 flex items-center gap-2">
          Kết quả phân tích:
        </h3>
        
        <div class={`p-6 rounded-2xl border ${config.bg} relative overflow-hidden shadow-inner`}>
          <!-- Nền trang trí -->
          <div class={`absolute top-0 right-0 w-32 h-32 bg-gradient-to-br ${config.color} opacity-10 rounded-full -mr-10 -mt-10 blur-2xl`}></div>

          <div class="relative z-10 flex flex-col md:flex-row items-center gap-6">
            <!-- Icon Tròn lớn -->
            <div class={`w-20 h-20 rounded-full bg-gradient-to-br ${config.color} flex items-center justify-center text-4xl shadow-lg text-white shrink-0`}>
              {config.icon}
            </div>
            
            <!-- Thông tin và Thanh tiến trình -->
            <div class="flex-1 w-full">
              <h4 class="text-2xl font-bold mb-1">{config.text}</h4>
              <p class="opacity-90 mb-4">{config.desc}</p>
              
              <!-- Thanh Confidence Score -->
              {#if confidence !== null}
                <div class="flex items-center justify-between text-sm font-bold opacity-80 mb-1">
                  <span>Độ tin cậy của AI:</span>
                  <span>{(confidence * 100).toFixed(1)}%</span>
                </div>
                
                <div class="w-full bg-black/5 rounded-full h-3 overflow-hidden shadow-inner">
                  <div 
                    class={`h-full rounded-full bg-gradient-to-r ${config.color} shadow-sm`} 
                    style="width: {confidence * 100}%"
                    transition:slide="{{ duration: 1000, axis: 'x' }}"
                  ></div>
                </div>
              {/if}
            </div>
          </div>
        </div>
      </div>
    {/if}
  </main>

  <footer class="absolute bottom-4 text-slate-400 text-sm font-medium">
    &copy; 2025 AI Research Lab
  </footer>
</div>

<style>
  /* Custom Animation */
  @keyframes blob {
    0% { transform: translate(0px, 0px) scale(1); }
    33% { transform: translate(30px, -50px) scale(1.1); }
    66% { transform: translate(-20px, 20px) scale(0.9); }
    100% { transform: translate(0px, 0px) scale(1); }
  }
  .animate-blob {
    animation: blob 7s infinite;
  }
  .animation-delay-2000 {
    animation-delay: 2s;
  }
  .animation-delay-4000 {
    animation-delay: 4s;
  }
</style>