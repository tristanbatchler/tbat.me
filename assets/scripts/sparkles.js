document.addEventListener('DOMContentLoaded', function () {
    "use strict";

    // Apply sparkle effect to elements with specific classes
    applySparkleEffect('.sparkle', 40, ["#ff0080", "#ff0080", "#0000FF"], 3, 30);
    applySparkleEffect('.sparkle-more', 30, ["#ff0080", "#ff0080", "#0000FF"], 10, 10);
    applySparkleEffect('.sparkle-less', 5, ["#ff0080", "#ff0080", "#0000FF"], 2, 5);
});

// Function to apply sparkle effect to elements with specific selector
function applySparkleEffect(selector, count, color, speed, overlap) {
    document.querySelectorAll(selector).forEach(function (element) {
        createSparkle(element, {
            count: count,
            color: color,
            speed: speed,
            overlap: overlap
        });
    });
}

// Function to create sparkle effect for an element
function createSparkle(element, options) {
    const settings = Object.assign({
        width: element.offsetWidth,
        height: element.offsetHeight,
        color: "#FFFFFF",
        count: 30,
        overlap: 0,
        speed: 1
    }, options);

    const sparkle = new Sparkle(element, settings);
    sparkle.over();
}

// Sparkle class to manage individual sparkle behavior
class Sparkle {
    constructor(element, options) {
        this.options = options;
        this.init(element);
    }

    init(element) {
        this.canvas = document.createElement('canvas');
        this.canvas.classList.add('sparkle-canvas');
        this.canvas.style.position = 'absolute';
        this.canvas.style.top = `-${this.options.overlap}px`;
        this.canvas.style.left = `-${this.options.overlap}px`;
        this.canvas.style.pointerEvents = 'none';
        element.appendChild(this.canvas);

        this.context = this.canvas.getContext("2d");
        this.sprite = new Image();
        this.sprites = [0, 6, 13, 20];
        this.sprite.src = this.datauri;

        this.canvas.width = this.options.width + (this.options.overlap * 2);
        this.canvas.height = this.options.height + (this.options.overlap * 2);

        this.particles = this.createSparkles(this.canvas.width, this.canvas.height);
        this.anim = null;
        this.fade = false;
    }

    createSparkles(w, h) {
        let particles = [];

        for (let i = 0; i < this.options.count; i++) {
            let color = this.options.color;
            if (this.options.color === "rainbow") {
                color = '#' + Math.floor(Math.random() * 16777215).toString(16);
            } else if (Array.isArray(this.options.color)) {
                color = this.options.color[Math.floor(Math.random() * this.options.color.length)];
            }

            particles[i] = {
                position: {
                    x: Math.floor(Math.random() * w),
                    y: Math.floor(Math.random() * h)
                },
                style: this.sprites[Math.floor(Math.random() * 4)],
                delta: {
                    x: Math.floor(Math.random() * 1000) - 500,
                    y: Math.abs(Math.floor(Math.random() * 1000) - 500)
                },
                size: parseFloat((Math.random() * 2).toFixed(2)),
                color: color,
                opacity: Math.random()
            };
        }

        return particles;
    }

    draw(time, fade) {
        const ctx = this.context;
        ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);

        this.particles.forEach(particle => {
            const modulus = Math.floor(Math.random() * 7);
            if (Math.floor(time) % modulus === 0) {
                particle.style = this.sprites[Math.floor(Math.random() * 4)];
            }

            ctx.save();
            ctx.globalAlpha = particle.opacity;
            ctx.drawImage(this.sprite, particle.style, 0, 7, 7, particle.position.x, particle.position.y, 7, 7);

            if (this.options.color) {
                ctx.globalCompositeOperation = "source-atop";
                ctx.globalAlpha = 0.5;
                ctx.fillStyle = particle.color;
                ctx.fillRect(particle.position.x, particle.position.y, 7, 7);
            }

            ctx.restore();
        });
    }

    update() {
        const _this = this;

        this.anim = requestAnimationFrame(function (time) {
            _this.particles.forEach(particle => {
                const randX = Math.random() > Math.random() * 2;
                const randY = Math.random() > Math.random() * 3;

                if (randX) particle.position.x += ((particle.delta.x * _this.options.speed) / 1500);
                if (!randY) particle.position.y -= ((particle.delta.y * _this.options.speed) / 800);

                if (particle.position.x > _this.canvas.width) particle.position.x = -7;
                if (particle.position.x < -7) particle.position.x = _this.canvas.width;
                if (particle.position.y > _this.canvas.height) particle.position.y = -7;
                if (particle.position.y < -7) particle.position.y = _this.canvas.height;

                if (_this.fade) particle.opacity -= 0.02;
                else particle.opacity -= 0.005;

                if (particle.opacity <= 0) particle.opacity = (_this.fade) ? 0 : 1;
            });

            _this.draw(time);
            if (_this.fade) {
                _this.fadeCount -= 1;
                if (_this.fadeCount < 0) {
                    cancelAnimationFrame(_this.anim);
                } else {
                    _this.update();
                }
            } else {
                _this.update();
            }
        });
    }

    cancel() {
        this.fadeCount = 100;
    }

    over() {
        cancelAnimationFrame(this.anim);
        this.particles.forEach(particle => {
            particle.opacity = Math.random();
        });
        this.fade = false;
        this.update();
    }

    out() {
        this.fade = true;
        this.cancel();
    }

    get datauri() {
        return "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABsAAAAHCAYAAAD5wDa1AAAAGXRFWHRTb2Z0d2FyZQBBZG9iZSBJbWFnZVJlYWR5ccllPAAAAyRpVFh0WE1MOmNvbS5hZG9iZS54bXAAAAAAADw/eHBhY2tldCBiZWdpbj0i77u/IiBpZD0iVzVNME1wQ2VoaUh6cmVTek5UY3prYzlkIj8+IDx4OnhtcG1ldGEgeG1sbnM6eD0iYWRvYmU6bnM6bWV0YS8iIHg6eG1wdGs9IkFkb2JlIFhNUCBDb3JlIDUuMC1jMDYxIDY0LjE0MDk0OSwgMjAxMC8xMi8wNy0xMDo1NzowMSAgICAgICAgIj4gPHJkZjpSREYgeG1sbnM6cmRmPSJodHRwOi8vd3d3LnczLm9yZy8xOTk5LzAyLzIyLXJkZi1zeW50YXgtbnMjIj4gPHJkZjpEZXNjcmlwdGlvbiByZGY6YWJvdXQ9IiIgeG1sbnM6eG1wPSJodHRwOi8vbnMuYWRvYmUuY29tL3hhcC8xLjAvIiB4bWxuczp4bXBNTT0iaHR0cDovL25zLmFkb2JlLmNvbS94YXAvMS4wL21tLyIgeG1sbnM6c3RSZWY9Imh0dHA6Ly9ucy5hZG9iZS5jb20veGFwLzEuMC9zVHlwZS9SZXNvdXJjZVJlZiMiIHhtcDpDcmVhdG9yVG9vbD0iQWRvYmUgUGhvdG9zaG9wIENTNS4xIE1hY2ludG9zaCIgeG1wTU06SW5zdGFuY2VJRD0ieG1wLmlpZDozNDNFMzM5REEyMkUxMUUzOEE3NEI3Q0U1QUIzMTc4NiIgeG1wTU06RG9jdW1lbnRJRD0ieG1wLmRpZDozNDNFMzM5RUEyMkUxMUUzOEE3NEI3Q0U1QUIzMTc4NiI+IDx4bXBNTTpEZXJpdmVkRnJvbSBzdFJlZjppbnN0YW5jZUlEPSJ4bXAuaWlkOjM0M0UzMzlCQTIyRTExRTM4QTc0QjdDRTVBQjMxNzg2IiBzdFJlZjpkb2N1bWVudElEPSJ4bXAuZGlkOjM0M0UzMzlDQTIyRTExRTM4QTc0QjdDRTVBQjMxNzg2Ii8+IDwvcmRmOkRlc2NyaXB0aW9uPiA8L3JkZjpSREY+IDwveDp4bXBtZXRhPiA8P3hwYWNrZXQgZW5kPSJyIj8+jzOsUQAAANhJREFUeNqsks0KhCAUhW/Sz6pFSc1AD9HL+OBFbdsVOKWLajH9EE7GFBEjOMxcUNHD8dxPBCEE/DKyLGMqraoqcd4j0ChpUmlBEGCFRBzH2dbj5JycJAn90CEpy1J2SK4apVSM4yiKonhePYwxMU2TaJrm8BpykpWmKQ3D8FbX9SOO4/tOhDEG0zRhGAZo2xaiKDLyPGeSyPM8sCxr868+WC/mvu9j13XBtm1ACME8z7AsC/R9r0fGOf+arOu6jUwS7l6tT/B+xo+aDFRo5BykHfav3/gSYAAtIdQ1IT0puAAAAABJRU5ErkJggg==";
    }
}