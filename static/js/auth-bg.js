/**
 * Ultra-modern technology background animation for auth pages.
 * Features: particle network, floating hexagons, scanning grid, and pulsing nodes.
 */
(function () {
    const wrapper = document.querySelector('.auth-wrapper');
    if (!wrapper) return;

    // ── Canvas setup ──
    const canvas = document.createElement('canvas');
    canvas.id = 'authBgCanvas';
    canvas.style.cssText =
        'position:absolute;top:0;left:0;width:100%;height:100%;z-index:0;pointer-events:none;';
    wrapper.insertBefore(canvas, wrapper.firstChild);

    const ctx = canvas.getContext('2d');
    let W, H;
    const dpr = Math.min(window.devicePixelRatio || 1, 2);

    function resize() {
        W = wrapper.clientWidth;
        H = wrapper.clientHeight;
        canvas.width = W * dpr;
        canvas.height = H * dpr;
        ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    }
    resize();
    window.addEventListener('resize', resize);

    // ── Color palette ──
    const CYAN = [0, 212, 255];
    const TEAL = [0, 180, 216];
    const BLUE = [72, 149, 239];
    const PURPLE = [114, 9, 183];

    function rgba(c, a) {
        return `rgba(${c[0]},${c[1]},${c[2]},${a})`;
    }

    function lerpColor(a, b, t) {
        return [
            a[0] + (b[0] - a[0]) * t,
            a[1] + (b[1] - a[1]) * t,
            a[2] + (b[2] - a[2]) * t,
        ];
    }

    // ── Particles ──
    const PARTICLE_COUNT = Math.min(70, Math.floor((window.innerWidth * window.innerHeight) / 15000));
    const CONNECTION_DIST = 160;
    const particles = [];

    class Particle {
        constructor() {
            this.reset();
        }
        reset() {
            this.x = Math.random() * W;
            this.y = Math.random() * H;
            this.vx = (Math.random() - 0.5) * 0.6;
            this.vy = (Math.random() - 0.5) * 0.6;
            this.radius = Math.random() * 2 + 1;
            this.color = [CYAN, TEAL, BLUE][Math.floor(Math.random() * 3)];
            this.pulse = Math.random() * Math.PI * 2;
            this.pulseSpeed = 0.02 + Math.random() * 0.02;
        }
        update() {
            this.x += this.vx;
            this.y += this.vy;
            this.pulse += this.pulseSpeed;
            if (this.x < -20) this.x = W + 20;
            if (this.x > W + 20) this.x = -20;
            if (this.y < -20) this.y = H + 20;
            if (this.y > H + 20) this.y = -20;
        }
        draw() {
            const a = 0.4 + Math.sin(this.pulse) * 0.3;
            const r = this.radius + Math.sin(this.pulse) * 0.5;
            // Glow
            ctx.beginPath();
            const grd = ctx.createRadialGradient(this.x, this.y, 0, this.x, this.y, r * 4);
            grd.addColorStop(0, rgba(this.color, a * 0.5));
            grd.addColorStop(1, rgba(this.color, 0));
            ctx.fillStyle = grd;
            ctx.arc(this.x, this.y, r * 4, 0, Math.PI * 2);
            ctx.fill();
            // Core
            ctx.beginPath();
            ctx.fillStyle = rgba(this.color, a + 0.2);
            ctx.arc(this.x, this.y, r, 0, Math.PI * 2);
            ctx.fill();
        }
    }

    for (let i = 0; i < PARTICLE_COUNT; i++) particles.push(new Particle());

    // ── Floating hexagons ──
    const hexagons = [];
    const HEX_COUNT = 5;

    class Hexagon {
        constructor() {
            this.x = Math.random() * W;
            this.y = Math.random() * H;
            this.size = 20 + Math.random() * 40;
            this.rotation = Math.random() * Math.PI * 2;
            this.rotSpeed = (Math.random() - 0.5) * 0.008;
            this.vx = (Math.random() - 0.5) * 0.3;
            this.vy = (Math.random() - 0.5) * 0.3;
            this.alpha = 0.03 + Math.random() * 0.06;
            this.color = [CYAN, TEAL, BLUE, PURPLE][Math.floor(Math.random() * 4)];
        }
        update() {
            this.x += this.vx;
            this.y += this.vy;
            this.rotation += this.rotSpeed;
            if (this.x < -60) this.x = W + 60;
            if (this.x > W + 60) this.x = -60;
            if (this.y < -60) this.y = H + 60;
            if (this.y > H + 60) this.y = -60;
        }
        draw() {
            ctx.save();
            ctx.translate(this.x, this.y);
            ctx.rotate(this.rotation);
            ctx.beginPath();
            for (let i = 0; i < 6; i++) {
                const angle = (Math.PI / 3) * i - Math.PI / 6;
                const px = this.size * Math.cos(angle);
                const py = this.size * Math.sin(angle);
                i === 0 ? ctx.moveTo(px, py) : ctx.lineTo(px, py);
            }
            ctx.closePath();
            ctx.strokeStyle = rgba(this.color, this.alpha * 2);
            ctx.lineWidth = 1;
            ctx.stroke();
            ctx.fillStyle = rgba(this.color, this.alpha * 0.5);
            ctx.fill();
            ctx.restore();
        }
    }

    for (let i = 0; i < HEX_COUNT; i++) hexagons.push(new Hexagon());

    // ── Scanning line ──
    let scanY = 0;
    const SCAN_SPEED = 0.4;

    function drawScanLine(time) {
        scanY = (scanY + SCAN_SPEED) % H;
        const gradient = ctx.createLinearGradient(0, scanY - 2, 0, scanY + 2);
        gradient.addColorStop(0, rgba(CYAN, 0));
        gradient.addColorStop(0.5, rgba(CYAN, 0.06));
        gradient.addColorStop(1, rgba(CYAN, 0));
        ctx.fillStyle = gradient;
        ctx.fillRect(0, scanY - 30, W, 60);
    }

    // ── Grid pattern ──
    function drawGrid(time) {
        const spacing = 60;
        const pulse = Math.sin(time * 0.001) * 0.02 + 0.025;
        ctx.strokeStyle = rgba(CYAN, pulse);
        ctx.lineWidth = 0.5;
        for (let x = 0; x < W; x += spacing) {
            ctx.beginPath();
            ctx.moveTo(x, 0);
            ctx.lineTo(x, H);
            ctx.stroke();
        }
        for (let y = 0; y < H; y += spacing) {
            ctx.beginPath();
            ctx.moveTo(0, y);
            ctx.lineTo(W, y);
            ctx.stroke();
        }
        // Intersection dots
        const dotPulse = Math.sin(time * 0.002) * 0.3 + 0.5;
        for (let x = 0; x < W; x += spacing) {
            for (let y = 0; y < H; y += spacing) {
                const dist = Math.abs(y - scanY);
                if (dist < 80) {
                    const intensity = (1 - dist / 80) * 0.15 * dotPulse;
                    ctx.beginPath();
                    ctx.fillStyle = rgba(CYAN, intensity);
                    ctx.arc(x, y, 2, 0, Math.PI * 2);
                    ctx.fill();
                }
            }
        }
    }

    // ── Data streams (binary rain effect) ──
    const streams = [];
    const STREAM_COUNT = 8;

    class DataStream {
        constructor() {
            this.reset();
        }
        reset() {
            this.x = Math.random() * W;
            this.y = -20;
            this.speed = 1 + Math.random() * 2;
            this.chars = [];
            const len = 5 + Math.floor(Math.random() * 10);
            for (let i = 0; i < len; i++) {
                this.chars.push(Math.random() > 0.5 ? '1' : '0');
            }
            this.alpha = 0.08 + Math.random() * 0.12;
        }
        update() {
            this.y += this.speed;
            if (this.y > H + 200) this.reset();
        }
        draw() {
            ctx.font = '10px monospace';
            for (let i = 0; i < this.chars.length; i++) {
                const a = this.alpha * (1 - i / this.chars.length);
                ctx.fillStyle = rgba(CYAN, a);
                ctx.fillText(this.chars[i], this.x, this.y - i * 14);
            }
        }
    }

    for (let i = 0; i < STREAM_COUNT; i++) {
        const s = new DataStream();
        s.y = Math.random() * H;
        streams.push(s);
    }

    // ── Connection lines between nearby particles ──
    function drawConnections() {
        for (let i = 0; i < particles.length; i++) {
            for (let j = i + 1; j < particles.length; j++) {
                const dx = particles[i].x - particles[j].x;
                const dy = particles[i].y - particles[j].y;
                const dist = Math.sqrt(dx * dx + dy * dy);
                if (dist < CONNECTION_DIST) {
                    const alpha = (1 - dist / CONNECTION_DIST) * 0.15;
                    const color = lerpColor(particles[i].color, particles[j].color, 0.5);
                    ctx.beginPath();
                    ctx.strokeStyle = rgba(color, alpha);
                    ctx.lineWidth = 0.6;
                    ctx.moveTo(particles[i].x, particles[i].y);
                    ctx.lineTo(particles[j].x, particles[j].y);
                    ctx.stroke();
                }
            }
        }
    }

    // ── Corner circuit accents ──
    function drawCircuitAccents(time) {
        const pulse = Math.sin(time * 0.003) * 0.15 + 0.2;
        ctx.strokeStyle = rgba(CYAN, pulse * 0.3);
        ctx.lineWidth = 1;

        // Top-left
        ctx.beginPath();
        ctx.moveTo(0, 80);
        ctx.lineTo(0, 20);
        ctx.lineTo(20, 0);
        ctx.lineTo(80, 0);
        ctx.stroke();
        ctx.beginPath();
        ctx.arc(20, 20, 3, 0, Math.PI * 2);
        ctx.fillStyle = rgba(CYAN, pulse * 0.5);
        ctx.fill();

        // Bottom-right
        ctx.beginPath();
        ctx.moveTo(W, H - 80);
        ctx.lineTo(W, H - 20);
        ctx.lineTo(W - 20, H);
        ctx.lineTo(W - 80, H);
        ctx.stroke();
        ctx.beginPath();
        ctx.arc(W - 20, H - 20, 3, 0, Math.PI * 2);
        ctx.fillStyle = rgba(CYAN, pulse * 0.5);
        ctx.fill();

        // Top-right
        ctx.beginPath();
        ctx.moveTo(W - 80, 0);
        ctx.lineTo(W - 20, 0);
        ctx.lineTo(W, 20);
        ctx.lineTo(W, 80);
        ctx.stroke();

        // Bottom-left
        ctx.beginPath();
        ctx.moveTo(0, H - 80);
        ctx.lineTo(0, H - 20);
        ctx.lineTo(20, H);
        ctx.lineTo(80, H);
        ctx.stroke();
    }

    // ── Main loop ──
    let animFrame;
    function animate(time) {
        ctx.clearRect(0, 0, W, H);

        // Background gradient
        const bg = ctx.createRadialGradient(W / 2, H / 2, 0, W / 2, H / 2, Math.max(W, H) * 0.8);
        bg.addColorStop(0, 'rgba(10, 15, 30, 0.3)');
        bg.addColorStop(1, 'rgba(5, 8, 18, 0.1)');
        ctx.fillStyle = bg;
        ctx.fillRect(0, 0, W, H);

        drawGrid(time);
        drawScanLine(time);
        drawCircuitAccents(time);

        hexagons.forEach(h => { h.update(); h.draw(); });
        streams.forEach(s => { s.update(); s.draw(); });
        particles.forEach(p => { p.update(); p.draw(); });
        drawConnections();

        animFrame = requestAnimationFrame(animate);
    }

    animate(0);

    // Cleanup on page unload
    window.addEventListener('beforeunload', () => cancelAnimationFrame(animFrame));
})();
