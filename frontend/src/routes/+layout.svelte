<!---frontend/src/routes/+layout.svelte--->
<script>
    import '../app.css';
</script>

<div class="app-bg">
    <div class="orb o1"></div>
    <div class="orb o2"></div>
    <div class="overlay"><slot /></div>
</div>

<style>
    .app-bg { position: relative; min-height: 100vh; background: #0f172a; overflow: hidden; }
    .orb { position: absolute; border-radius: 50%; filter: blur(100px); opacity: 0.4; z-index: 0; animation: float 20s infinite alternate; }
    .o1 { width: 500px; height: 500px; background: #4f46e5; top: -100px; left: -100px; }
    .o2 { width: 600px; height: 600px; background: #db2777; bottom: -100px; right: -100px; animation-delay: -5s; }
    .overlay { position: relative; z-index: 10; min-height: 100vh; background-image: linear-gradient(rgba(255,255,255,0.03) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.03) 1px, transparent 1px); background-size: 50px 50px; }
    @keyframes float { from { transform: translate(0,0); } to { transform: translate(30px, 30px); } }
</style>