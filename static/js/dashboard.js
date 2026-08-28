/* ==========================================================================
   ⚙️ VORTEX BOT DASHBOARD INTERACTIVE SCRIPT
   ========================================================================== */

document.addEventListener("DOMContentLoaded", () => {
    // Current Active Guild ID for music controls
    let selectedGuildId = null;
    let musicStateData = [];

    // ==========================================
    // 📱 MOBILE DRAWER CONTROLS
    // ==========================================
    const mobileMenuBtn = document.getElementById("mobile-menu-btn");
    const closeDrawerBtn = document.getElementById("close-drawer-btn");
    const sidebarDrawer = document.getElementById("sidebar-drawer");
    const mobileBackdrop = document.getElementById("mobile-backdrop");

    function openMobileDrawer() {
        if (sidebarDrawer) sidebarDrawer.classList.add("open");
        if (mobileBackdrop) mobileBackdrop.classList.add("active");
        document.body.style.overflow = "hidden";
    }

    function closeMobileDrawer() {
        if (sidebarDrawer) sidebarDrawer.classList.remove("open");
        if (mobileBackdrop) mobileBackdrop.classList.remove("active");
        document.body.style.overflow = "";
    }

    if (mobileMenuBtn) mobileMenuBtn.addEventListener("click", openMobileDrawer);
    if (closeDrawerBtn) closeDrawerBtn.addEventListener("click", closeMobileDrawer);
    if (mobileBackdrop) mobileBackdrop.addEventListener("click", closeMobileDrawer);

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

            // Automatically close drawer on mobile after selection
            if (window.innerWidth <= 992) {
                closeMobileDrawer();
            }

            // Trigger fetch once when switching to specific panels
            if (tabId === "leaderboards") {
                fetchLeaderboards();
            } else if (tabId === "moderation") {
                fetchModeration();
            } else if (tabId === "rpg") {
                fetchRPG();
            } else if (tabId === "features") {
                fetchFeatures();
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
        if (!selectedGuildId) return;
        const levelsBody = document.getElementById("levels-leaderboard-body");
        const economyBody = document.getElementById("economy-leaderboard-body");

        try {
            const res = await fetch(`/api/leaderboards?guild_id=${selectedGuildId}`);
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

    let localIsPlaying = false;

    async function fetchMusicState() {
        if (!selectedGuildId) return;
        try {
            const res = await fetch(`/api/music/state?guild_id=${selectedGuildId}`);
            const data = await res.json();

            if (data.error || !data.active) {
                showEmptyPlayer();
                return;
            }

            // Show player, hide empty
            playerEmptyView.classList.add("hidden");
            playerActiveView.classList.remove("hidden");

            // Set Title/Uploader
            if (data.current) {
                trackTitle.textContent = data.current.title;
                trackArtist.textContent = data.current.uploader;
                localIsPlaying = data.is_playing;
            } else {
                trackTitle.textContent = "No Track Playing";
                trackArtist.textContent = "Vortex Radio";
                localIsPlaying = false;
            }

            // Toggle Play/Pause Button Icon
            if (data.is_playing) {
                btnPauseResume.innerHTML = `<i class="fa-solid fa-pause"></i>`;
            } else {
                btnPauseResume.innerHTML = `<i class="fa-solid fa-play"></i>`;
            }

            // Update Volume slider (only if user is not actively sliding it)
            if (document.activeElement !== volumeSlider) {
                volumeSlider.value = data.volume;
                volumeDisplay.textContent = `${data.volume}%`;
            }

            // Update Queue
            queueList.innerHTML = "";
            if (data.queue && data.queue.length > 0) {
                data.queue.forEach((song, idx) => {
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
        const action = localIsPlaying ? "pause" : "resume";
        sendControlAction(action);
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

    // ==========================================
    // 🛡️ MODERATION DATA
    // ==========================================
    async function fetchModeration() {
        if (!selectedGuildId) return;
        const warningsBody = document.getElementById("warnings-table-body");
        const tempbansBody = document.getElementById("tempbans-table-body");

        try {
            const res = await fetch(`/api/moderation?guild_id=${selectedGuildId}`);
            const data = await res.json();

            // Populate Warnings
            warningsBody.innerHTML = "";
            if (data.warnings && data.warnings.length > 0) {
                data.warnings.forEach(row => {
                    const tr = document.createElement("tr");
                    tr.classList.add("warning-row");
                    tr.setAttribute("data-user-id", row.user_id);
                    tr.innerHTML = `
                        <td><code>#${row.id}</code></td>
                        <td><code>${row.user_id}</code></td>
                        <td><strong>${row.username}</strong></td>
                        <td>${row.reason}</td>
                        <td class="text-muted"><small>${row.timestamp}</small></td>
                    `;
                    warningsBody.appendChild(tr);
                });
            } else {
                warningsBody.innerHTML = `<tr><td colspan="5" class="loading">No warnings logged yet.</td></tr>`;
            }

            // Populate Tempbans
            tempbansBody.innerHTML = "";
            if (data.tempbans && data.tempbans.length > 0) {
                data.tempbans.forEach(row => {
                    const tr = document.createElement("tr");
                    tr.innerHTML = `
                        <td><code>${row.user_id}</code></td>
                        <td><strong>${row.username}</strong></td>
                        <td><code>${row.guild_id}</code></td>
                        <td class="text-danger">${row.unban_time}</td>
                    `;
                    tempbansBody.appendChild(tr);
                });
            } else {
                tempbansBody.innerHTML = `<tr><td colspan="4" class="loading">No active temporary bans.</td></tr>`;
            }

            // Setup search filter for warnings
            const warningSearch = document.getElementById("warning-search-input");
            warningSearch.addEventListener("input", () => {
                const query = warningSearch.value.toLowerCase().trim();
                const warningRows = document.querySelectorAll(".warning-row");
                warningRows.forEach(row => {
                    const userId = row.getAttribute("data-user-id") || "";
                    if (userId.includes(query)) {
                        row.style.display = "";
                    } else {
                        row.style.display = "none";
                    }
                });
            });

        } catch (err) {
            console.error("Error loading moderation logs:", err);
            warningsBody.innerHTML = `<tr><td colspan="5" class="loading text-danger">Failed to fetch warning logs.</td></tr>`;
            tempbansBody.innerHTML = `<tr><td colspan="4" class="loading text-danger">Failed to fetch tempbans.</td></tr>`;
        }
    }

    // ==========================================
    // ⚔️ RPG ADVENTURERS
    // ==========================================
    async function fetchRPG() {
        if (!selectedGuildId) return;
        const rpgBody = document.getElementById("rpg-table-body");

        try {
            const res = await fetch(`/api/rpg/players?guild_id=${selectedGuildId}`);
            const data = await res.json();

            rpgBody.innerHTML = "";
            if (data.players && data.players.length > 0) {
                data.players.forEach(row => {
                    const tr = document.createElement("tr");
                    tr.innerHTML = `
                        <td><strong>${row.username}</strong><br><small class="text-muted"><code>${row.user_id}</code></small></td>
                        <td><span class="badge music-badge">${row.class}</span></td>
                        <td><strong>Lvl ${row.level}</strong></td>
                        <td>${row.xp.toLocaleString()} XP</td>
                        <td>❤️ ${row.hp}</td>
                        <td>⚔️ ${row.attack} | 🛡️ ${row.defense}</td>
                        <td class="text-success">$${row.coins.toLocaleString()}</td>
                        <td>🗡️ ${row.weapon}<br>🛡️ ${row.armor}</td>
                        <td>🏰 Floor ${row.floor}</td>
                    `;
                    rpgBody.appendChild(tr);
                });
            } else {
                rpgBody.innerHTML = `<tr><td colspan="9" class="loading">No active RPG player logs found.</td></tr>`;
            }
        } catch (err) {
            console.error("Error loading RPG players:", err);
            rpgBody.innerHTML = `<tr><td colspan="9" class="loading text-danger">Failed to fetch RPG statistics.</td></tr>`;
        }
    }

    // ==========================================
    // 🎉 ACTIVE FEATURES & GIVEAWAYS
    // ==========================================
    async function fetchFeatures() {
        if (!selectedGuildId) return;
        const giveawaysBody = document.getElementById("giveaways-table-body");
        const tagsBody = document.getElementById("tags-table-body");
        const respondersBody = document.getElementById("responders-table-body");

        try {
            const res = await fetch(`/api/features/active?guild_id=${selectedGuildId}`);
            const data = await res.json();

            // Populate Giveaways
            giveawaysBody.innerHTML = "";
            if (data.giveaways && data.giveaways.length > 0) {
                data.giveaways.forEach(row => {
                    const tr = document.createElement("tr");
                    const dateFmt = new Date(row.end_time * 1000).toLocaleString();
                    const statusText = row.is_active ? '<span class="badge music-badge">Active</span>' : '<span class="badge">Ended</span>';
                    tr.innerHTML = `
                        <td><strong>${row.prize}</strong></td>
                        <td>🏆 ${row.winners} Winners</td>
                        <td>${row.host}</td>
                        <td><small>${dateFmt}</small></td>
                        <td>${statusText}</td>
                    `;
                    giveawaysBody.appendChild(tr);
                });
            } else {
                giveawaysBody.innerHTML = `<tr><td colspan="5" class="loading">No active giveaways scheduled.</td></tr>`;
            }

            // Populate Custom Tags
            tagsBody.innerHTML = "";
            if (data.custom_tags && data.custom_tags.length > 0) {
                data.custom_tags.forEach(row => {
                    const tr = document.createElement("tr");
                    tr.innerHTML = `
                        <td><code>&${row.tag_name}</code></td>
                        <td>${row.author}</td>
                        <td>${row.uses.toLocaleString()}</td>
                    `;
                    tagsBody.appendChild(tr);
                });
            } else {
                tagsBody.innerHTML = `<tr><td colspan="3" class="loading">No custom tags created yet.</td></tr>`;
            }

            // Populate Autoresponders
            respondersBody.innerHTML = "";
            if (data.autoresponders && data.autoresponders.length > 0) {
                data.autoresponders.forEach(row => {
                    const tr = document.createElement("tr");
                    const matchType = row.is_exact ? "Exact Match" : "Substring Match";
                    tr.innerHTML = `
                        <td><code>${row.trigger}</code></td>
                        <td><small>${row.response}</small></td>
                        <td><span class="badge">${matchType}</span></td>
                    `;
                    respondersBody.appendChild(tr);
                });
            } else {
                respondersBody.innerHTML = `<tr><td colspan="3" class="loading">No active autoresponders.</td></tr>`;
            }

        } catch (err) {
            console.error("Error loading features:", err);
            giveawaysBody.innerHTML = `<tr><td colspan="5" class="loading text-danger">Failed to retrieve giveaways.</td></tr>`;
            tagsBody.innerHTML = `<tr><td colspan="3" class="loading text-danger">Failed to fetch custom tags.</td></tr>`;
            respondersBody.innerHTML = `<tr><td colspan="3" class="loading text-danger">Failed to fetch responders.</td></tr>`;
        }
    }
});
