<!-- src/routes/+layout.svelte -->
<script lang="ts">
  import "../app.css";
</script>

<div style="position:relative;min-height:100vh;padding:2rem 0">
  <div style="position:absolute;left:-120px;top:-90px;width:420px;height:420px;border-radius:50%;filter:blur(100px);background:linear-gradient(135deg,var(--accent1),#818cf8);opacity:0.65;z-index:1;"></div>
  <div style="position:absolute;right:-120px;bottom:-120px;width:520px;height:520px;border-radius:50%;filter:blur(100px);background:linear-gradient(135deg,#ec4899,#db2777);opacity:0.65;z-index:1;"></div>

  <main style="position:relative;z-index:20" class="container">
    <slot />
  </main>
</div>