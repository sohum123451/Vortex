/**
 * ⚡ Vortex Interactive Cursor Tracking & Emil Kowalski Motion Engine
 * Features:
 * - 60fps lerped spring follower dot & ambient glow
 * - Dynamic card spotlighting via relative CSS variables (--mouse-x, --mouse-y)
 * - Magnetic micro-pull button physics
 * - Click squash and stretch
 */

(function () {
    // Only initialize on devices that support hover (non-touch)
    if (window.matchMedia("(hover: none) and (pointer: coarse)").matches) {
        return;
    }

    // 1. Create DOM Cursor Elements
    const dot = document.createElement("div");
    dot.className = "cursor-dot";

    const follower = document.createElement("div");
    follower.className = "cursor-follower";

    const ambientSpotlight = document.createElement("div");
    ambientSpotlight.className = "cursor-ambient-spotlight";

    document.body.appendChild(dot);
    document.body.appendChild(follower);
    document.body.appendChild(ambientSpotlight);

    // Coordinate tracking
    let mouseX = window.innerWidth / 2;
    let mouseY = window.innerHeight / 2;
    let followerX = mouseX;
    let followerY = mouseY;
    let isVisible = false;

    // Mouse movement listener
    window.addEventListener("mousemove", (e) => {
        mouseX = e.clientX;
        mouseY = e.clientY;

        if (!isVisible) {
            isVisible = true;
            dot.style.opacity = "1";
            follower.style.opacity = "1";
            ambientSpotlight.style.opacity = "1";
        }

        // Direct position for instant dot
        dot.style.left = `${mouseX}px`;
        dot.style.top = `${mouseY}px`;

        // Update ambient background spotlight
        document.documentElement.style.setProperty("--cursor-x", `${mouseX}px`);
        document.documentElement.style.setProperty("--cursor-y", `${mouseY}px`);
    });

    window.addEventListener("mouseleave", () => {
        isVisible = false;
        dot.style.opacity = "0";
        follower.style.opacity = "0";
        ambientSpotlight.style.opacity = "0";
    });

    // 2. 60FPS Physics Lerping Loop for Follower Glow
    function animateFollower() {
        const ease = 0.16; // Emil Kowalski responsive spring factor
        followerX += (mouseX - followerX) * ease;
        followerY += (mouseY - followerY) * ease;

        follower.style.left = `${followerX}px`;
        follower.style.top = `${followerY}px`;

        requestAnimationFrame(animateFollower);
    }
    requestAnimationFrame(animateFollower);

    // 3. Click squash & stretch
    window.addEventListener("mousedown", () => {
        document.body.classList.add("cursor-click");
    });
    window.addEventListener("mouseup", () => {
        document.body.classList.remove("cursor-click");
    });

    // 4. Interactive Hover Target Detection & Magnetic Physics
    const interactiveSelectors = [
        "a", "button", "input", "select", "textarea", 
        ".btn", ".nav-btn", ".feature-card", ".ai-badge", 
        ".dash-card", ".stat-card", ".filter-btn", ".badge",
        ".spotlight-card", ".nav-link", ".server-card"
    ];

    function attachInteractivity() {
        // Card Spotlighting (--mouse-x, --mouse-y)
        const spotlightCards = document.querySelectorAll(
            ".feature-card, .ai-badge, .dash-card, .stat-card, .tech-card, .spotlight-card, .server-card, .category-pill"
        );

        spotlightCards.forEach((card) => {
            if (card.dataset.spotlightBound) return;
            card.dataset.spotlightBound = "true";

            card.addEventListener("mousemove", (e) => {
                const rect = card.getBoundingClientRect();
                const x = e.clientX - rect.left;
                const y = e.clientY - rect.top;
                card.style.setProperty("--mouse-x", `${x}px`);
                card.style.setProperty("--mouse-y", `${y}px`);
            });
        });

        // Interactive Cursor Hover Scaling
        const interactiveElements = document.querySelectorAll(interactiveSelectors.join(", "));
        interactiveElements.forEach((el) => {
            if (el.dataset.cursorBound) return;
            el.dataset.cursorBound = "true";

            el.addEventListener("mouseenter", () => {
                document.body.classList.add("cursor-hover");
            });

            el.addEventListener("mouseleave", () => {
                document.body.classList.remove("cursor-hover");
            });
        });

        // Magnetic Micro-Pull for Buttons
        const magneticButtons = document.querySelectorAll(
            ".magnetic-btn, .nav-btn, .hero-btn-primary, .hero-btn-secondary, .filter-btn, .btn-primary, .action-btn"
        );

        magneticButtons.forEach((btn) => {
            if (btn.dataset.magneticBound) return;
            btn.dataset.magneticBound = "true";

            btn.addEventListener("mousemove", (e) => {
                const rect = btn.getBoundingClientRect();
                const btnCenterX = rect.left + rect.width / 2;
                const btnCenterY = rect.top + rect.height / 2;

                const deltaX = (e.clientX - btnCenterX) * 0.22;
                const deltaY = (e.clientY - btnCenterY) * 0.22;

                btn.style.transform = `translate(${deltaX}px, ${deltaY}px)`;
            });

            btn.addEventListener("mouseleave", () => {
                btn.style.transform = "translate(0px, 0px)";
            });
        });
    }

    // Initialize on DOM Ready
    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", attachInteractivity);
    } else {
        attachInteractivity();
    }

    // Re-attach if dynamic content loads
    const observer = new MutationObserver(attachInteractivity);
    observer.observe(document.body, { childList: true, subtree: true });
})();
