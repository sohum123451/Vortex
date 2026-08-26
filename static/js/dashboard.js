/* ==========================================================================
   ⚙️ VORTEX BOT DASHBOARD INTERACTIVE SCRIPT
   ========================================================================== */

document.addEventListener("DOMContentLoaded", () => {
    // Current Active Guild ID for music controls
    let selectedGuildId = null;
    let musicStateData = [];

    // ==========================================
    // 🧭 TAB NAVIGATION SWITCHER
    // ==========================================
    const navLinks = document.querySelectorAll(".nav-link");
    const tabPanes = document.querySelectorAll(".tab-pane");

    navLinks.forEach(link => {
        link.addEventListener("click", (e) => {
            e.preventDefault();
            const tabId = link.getAttribute("data-tab");

            // Update Active Sidebar link
            navLinks.forEach(item => item.classList.remove("active"));
            link.classList.add("active");

            // Show matching Pane
            tabPanes.forEach(pane => {
                pane.classList.remove("active");
                if (pane.id === `tab-${tabId}`) {
                    pane.classList.add("active");
                }
            });

            // Trigger fetch once when switching to specific panels
            if (tabId === "leaderboards") {
                fetchLeaderboards();
            }
        });
    });

    // ==========================================
    // 📊 SYSTEM OVERVIEW STATS (Polling 5s)
    // ==========================================
    async function fetchStats() {
        try {
            const res = await fetch("/api/stats");
            const data = await res.json();

            if (data.ready) {
                document.getElementById("stat-guilds").textContent = data.guilds;
                document.getElementById("stat-users").textContent = data.users;
                document.getElementById("stat-ping").textContent = `${data.ping}ms`;
                document.getElementById("stat-uptime").textContent = data.uptime;
                
                // DB metrics
                document.getElementById("db-level-users").textContent = data.db_records.levels_users;
                document.getElementById("db-coins").textContent = data.db_records.coins.toLocaleString();

                // Status Badge
                const statusBadge = document.getElementById("bot-status-badge");
                statusBadge.querySelector(".status-label").textContent = "Online";
                statusBadge.querySelector(".pulse-dot").style.backgroundColor = "#1dd1a1";
            } else {
                // Loading/Connecting State
                const statusBadge = document.getElementById("bot-status-badge");
                statusBadge.querySelector(".status-label").textContent = "Connecting";
                statusBadge.querySelector(".pulse-dot").style.backgroundColor = "#ff9f43";
            }
        } catch (err) {
            console.error("Error fetching stats:", err);
            const statusBadge = document.getElementById("bot-status-badge");
            statusBadge.querySelector(".status-label").textContent = "Offline";
            statusBadge.querySelector(".pulse-dot").style.backgroundColor = "#ff5252";
        }
    }

    // Call stats initially and configure interval
    fetchStats();
    setInterval(fetchStats, 5000);

    // ==========================================
    // 🏆 LEADERBOARD POPULATION
    // ==========================================
    async function fetchLeaderboards() {
        const levelsBody = document.getElementById("levels-leaderboard-body");
        const economyBody = document.getElementById("economy-leaderboard-body");

        try {
            const res = await fetch("/api/leaderboards");
            const data = await res.json();

            // Populate Levels
            levelsBody.innerHTML = "";
            if (data.levels && data.levels.length > 0) {
                data.levels.forEach((row, idx) => {
                    const tr = document.createElement("tr");
                    tr.innerHTML = `
                        <td class="rank-num">#${idx + 1}</td>
                        <td>${row.username}</td>
                        <td><span class="badge music-badge">Lvl ${row.level}</span></td>
                        <td>${row.xp.toLocaleString()} XP</td>
                    `;
                    levelsBody.appendChild(tr);
                });
            } else {
                levelsBody.innerHTML = `<tr><td colspan="4" class="loading">No leveling data recorded yet.</td></tr>`;
            }

            // Populate Economy
            economyBody.innerHTML = "";
            if (data.economy && data.economy.length > 0) {
                data.economy.forEach((row, idx) => {
                    const tr = document.createElement("tr");
                    tr.innerHTML = `
                        <td class="rank-num">#${idx + 1}</td>
                        <td>${row.username}</td>
                        <td>👛 $${row.balance.toLocaleString()}</td>
                        <td>🏦 $${row.bank.toLocaleString()}</td>
                        <td class="text-success">$${row.total.toLocaleString()}</td>
                    `;
                    economyBody.appendChild(tr);
                });
            } else {
                economyBody.innerHTML = `<tr><td colspan="5" class="loading">No economy data recorded yet.</td></tr>`;
            }

        } catch (err) {
            console.error("Error loading leaderboards:", err);
            levelsBody.innerHTML = `<tr><td colspan="4" class="loading text-danger">Failed to retrieve stats.</td></tr>`;
            economyBody.innerHTML = `<tr><td colspan="5" class="loading text-danger">Failed to retrieve stats.</td></tr>`;
        }
    }

    // ==========================================
    // 🎵 MUSIC CONSOLE CONTROLS (Polling 2s)
    // ==========================================
    const guildSelect = document.getElementById("music-guild-select");
    const playerActiveView = document.getElementById("player-active-view");
    const playerEmptyView = document.getElementById("player-empty-view");

    const trackTitle = document.getElementById("current-track-title");
    const trackArtist = document.getElementById("current-track-uploader");
    const btnPauseResume = document.getElementById("btn-pause-resume");
    const btnSkip = document.getElementById("btn-skip");
    const volumeSlider = document.getElementById("player-volume");
    const volumeDisplay = document.getElementById("volume-val-display");
    const queueList = document.getElementById("music-queue-list");

    async function fetchMusicState() {
        try {
            const res = await fetch("/api/music/state");
            const data = await res.json();
            musicStateData = data.guilds || [];

            // Update Guild Dropdown options
            const currentSelection = guildSelect.value;
            guildSelect.innerHTML = "";

            if (musicStateData.length === 0) {
                guildSelect.innerHTML = `<option value="">No Active Guild Connections</option>`;
                selectedGuildId = null;
                showEmptyPlayer();
                return;
            }

            musicStateData.forEach(g => {
                const opt = document.createElement("option");
                opt.value = g.guild_id;
                opt.textContent = `${g.guild_name} (${g.active ? 'Connected' : 'Offline'})`;
                guildSelect.appendChild(opt);
            });

            // Keep selected guild active if it still exists
            if (currentSelection && musicStateData.some(g => g.guild_id === currentSelection)) {
                guildSelect.value = currentSelection;
                selectedGuildId = currentSelection;
            } else {
                selectedGuildId = musicStateData[0].guild_id;
                guildSelect.value = selectedGuildId;
            }

            updatePlayerConsole();
        } catch (err) {
            console.error("Error fetching music state:", err);
            showEmptyPlayer();
        }
    }

    function showEmptyPlayer() {
        playerActiveView.classList.add("hidden");
        playerEmptyView.classList.remove("hidden");
        queueList.innerHTML = `<li class="empty-queue">Queue is empty</li>`;
    }

    function updatePlayerConsole() {
        if (!selectedGuildId) return;

        const currentGuildState = musicStateData.find(g => g.guild_id === selectedGuildId);
        if (!currentGuildState || !currentGuildState.active || !currentGuildState.current) {
            showEmptyPlayer();
            return;
        }

        // Show player, hide empty
        playerEmptyView.classList.add("hidden");
        playerActiveView.classList.remove("hidden");

        // Set Title/Uploader
        trackTitle.textContent = currentGuildState.current.title;
        trackArtist.textContent = currentGuildState.current.uploader;

        // Toggle Play/Pause Button Icon
        if (currentGuildState.is_playing) {
            btnPauseResume.innerHTML = `<i class="fa-solid fa-pause"></i>`;
        } else {
            btnPauseResume.innerHTML = `<i class="fa-solid fa-play"></i>`;
        }

        // Update Volume slider (only if user is not actively sliding it)
        if (document.activeElement !== volumeSlider) {
            volumeSlider.value = currentGuildState.volume;
            volumeDisplay.textContent = `${currentGuildState.volume}%`;
        }

        // Update Queue
        queueList.innerHTML = "";
        if (currentGuildState.queue && currentGuildState.queue.length > 0) {
            currentGuildState.queue.forEach((song, idx) => {
                const li = document.createElement("li");
                const durationText = song.duration ? `${Math.floor(song.duration / 60)}:${(song.duration % 60).toString().padStart(2, '0')}` : "Stream";
                li.innerHTML = `
                    <span class="song-title"><strong>${idx + 1}.</strong> ${song.title}</span>
                    <span class="song-dur">${durationText}</span>
                `;
                queueList.appendChild(li);
            });
        } else {
            queueList.innerHTML = `<li class="empty-queue">Queue is empty</li>`;
        }
    }

    // Dropdown change listener
    guildSelect.addEventListener("change", () => {
        selectedGuildId = guildSelect.value;
        updatePlayerConsole();
    });

    // Start polling music state
    fetchMusicState();
    setInterval(fetchMusicState, 2000);

    // ==========================================
    // ⚙️ CONTROLLER ACTIONS POST REQUESTS
    // ==========================================
    async function sendControlAction(action, extraData = {}) {
        if (!selectedGuildId) return;

        try {
            const res = await fetch("/api/music/control", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    guild_id: selectedGuildId,
                    action: action,
                    ...extraData
                })
            });
            const data = await res.json();
            if (data.error) {
                console.error("Action error:", data.error);
            } else {
                fetchMusicState(); // refresh state immediately
            }
        } catch (err) {
            console.error("Control API execution error:", err);
        }
    }

    // Click Toggles
    btnPauseResume.addEventListener("click", () => {
        if (!selectedGuildId) return;
        const currentGuildState = musicStateData.find(g => g.guild_id === selectedGuildId);
        if (currentGuildState) {
            const action = currentGuildState.is_playing ? "pause" : "resume";
            sendControlAction(action);
        }
    });

    btnSkip.addEventListener("click", () => {
        sendControlAction("skip");
    });

    // Volume input events
    volumeSlider.addEventListener("input", () => {
        volumeDisplay.textContent = `${volumeSlider.value}%`;
    });

    volumeSlider.addEventListener("change", () => {
        sendControlAction("volume", { value: parseInt(volumeSlider.value) });
    });

    // ==========================================
    // 📚 DOCS SEARCH / FILTER
    // ==========================================
    const searchInput = document.getElementById("docs-search-input");
    const docsRows = document.querySelectorAll("#docs-table-body tr");

    searchInput.addEventListener("input", () => {
        const query = searchInput.value.toLowerCase().trim();

        docsRows.forEach(row => {
            const cells = row.getElementsByTagName("td");
            const commandText = cells[1].textContent.toLowerCase();
            const aliasesText = cells[2].textContent.toLowerCase();

            if (commandText.includes(query) || aliasesText.includes(query)) {
                row.style.display = "";
            } else {
                row.style.display = "none";
            }
        });
    });
});
