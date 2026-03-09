<script>
    import '../app.css';
</script>clear


<div class="relative min-h-screen overflow-x-hidden">
    <div class="fixed top-0 left-0 w-full h-full -z-10 pointer-events-none overflow-hidden">
        <div class="absolute top-[-10%] left-[-10%] w-[40%] h-[40%] bg-indigo-600/10 blur-[120px] rounded-full"></div>
        <div class="absolute bottom-[-5%] right-[-5%] w-[30%] h-[30%] bg-purple-600/10 blur-[120px] rounded-full"></div>
        <div class="absolute inset-0 opacity-[0.03]" 
             style="background-image: radial-gradient(#fff 1px, transparent 0); background-size: 40px 40px;"></div>
    </div>
    
    <slot />
</div>