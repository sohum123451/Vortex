/* ==========================================================================
   ⚡ VORTEX BOT DASHBOARD INTERACTIVE SCRIPT
   High-Speed Data Binding, Live Music Controls, and Responsive Navigation
   ========================================================================== */

document.addEventListener("DOMContentLoaded", () => {
    // Extract Guild ID from URL query or body data attribute
    const urlParams = new URLSearchParams(window.location.search);
    const bodyGuildId = document.body ? document.body.dataset.guildId : null;
    let selectedGuildId = urlParams.get("guild_id") || bodyGuildId || null;

    let localIsPlaying = false;

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

    function switchTab(tabId) {
        navLinks.forEach(item => {
            if (item.getAttribute("data-tab") === tabId) {
                item.classList.add("active");
            } else {
                item.classList.remove("active");
            }
        });

        tabPanes.forEach(pane => {
            if (pane.id === `tab-${tabId}`) {
                pane.classList.add("active");
            } else {
                pane.classList.remove("active");
            }
        });

        // Trigger data fetches on tab view
        if (tabId === "leaderboards") fetchLeaderboards();
        else if (tabId === "moderation") fetchModeration();
        else if (tabId === "rpg") fetchRPG();
        else if (tabId === "features") fetchFeatures();
        else if (tabId === "music") fetchMusicState();
    }

    navLinks.forEach(link => {
        link.addEventListener("click", (e) => {
            e.preventDefault();
            const tabId = link.getAttribute("data-tab");
            switchTab(tabId);
            if (window.innerWidth <= 1024) closeMobileDrawer();
        });
    });

    // ==========================================
    // 📊 SYSTEM OVERVIEW STATS (Polling 4s)
    // ==========================================
    async function fetchStats() {
        try {
            const res = await fetch("/api/stats");
            const data = await res.json();

            if (data && data.ready) {
                const elGuilds = document.getElementById("stat-guilds");
                const elUsers = document.getElementById("stat-users");
                const elPing = document.getElementById("stat-ping");
                const elUptime = document.getElementById("stat-uptime");
                const elLevelUsers = document.getElementById("db-level-users");
                const elCoins = document.getElementById("db-coins");

                if (elGuilds) elGuilds.textContent = data.guilds || 0;
                if (elUsers) elUsers.textContent = (data.users || 0).toLocaleString();
                if (elPing) elPing.textContent = `${data.ping || 0}ms`;
                if (elUptime) elUptime.textContent = data.uptime || "0h 0m";

                if (elLevelUsers && data.db_records) elLevelUsers.textContent = (data.db_records.levels_users || 0).toLocaleString();
                if (elCoins && data.db_records) elCoins.textContent = (data.db_records.coins || 0).toLocaleString();
            }
        } catch (err) {
            console.error("Error fetching stats:", err);
        }
    }

    fetchStats();
    setInterval(fetchStats, 5000);

    // ==========================================
    // 🎵 LIVE MUSIC PLAYER STATE
    // ==========================================
    const playerActiveView = document.getElementById("player-active-view");
    const playerEmptyView = document.getElementById("player-empty-view");
    const trackTitle = document.getElementById("current-track-title");
    const trackArtist = document.getElementById("current-track-uploader");
    const trackArtwork = document.querySelector(".album-disc-art");
    const btnPlayPause = document.getElementById("btn-pause-resume");
    const btnSkip = document.getElementById("btn-skip");
    const volumeSlider = document.getElementById("player-volume");
    const volumeValDisplay = document.getElementById("volume-val-display");
    const queueList = document.getElementById("music-queue-list");

    async function fetchMusicState() {
        if (!selectedGuildId) return;

        try {
            const res = await fetch("/api/music/states");
            const data = await res.json();
            const guildMusic = Array.isArray(data) ? data.find(g => g.guild_id === selectedGuildId) : null;

            if (guildMusic && guildMusic.is_connected && guildMusic.now_playing) {
                if (playerActiveView) playerActiveView.classList.remove("hidden");
                if (playerEmptyView) playerEmptyView.style.display = "none";
                if (trackArtwork) trackArtwork.classList.add("playing");

                localIsPlaying = !guildMusic.is_paused;
                if (trackTitle) trackTitle.textContent = guildMusic.now_playing.title || "Unknown Title";
                if (trackArtist) trackArtist.textContent = guildMusic.now_playing.uploader || "Live Audio Stream";

                if (btnPlayPause) {
                    btnPlayPause.innerHTML = localIsPlaying ? '<i class="fa-solid fa-pause"></i>' : '<i class="fa-solid fa-play"></i>';
                }

                if (volumeSlider) volumeSlider.value = guildMusic.volume || 70;
                if (volumeValDisplay) volumeValDisplay.textContent = `${guildMusic.volume || 70}%`;

                // Render Queue
                if (queueList) {
                    if (guildMusic.queue && guildMusic.queue.length > 0) {
                        queueList.innerHTML = guildMusic.queue.map((item, idx) => `
                            <li style="padding: 10px 14px; background: rgba(255,255,255,0.03); border: 1px solid var(--border-glass); border-radius: var(--radius-sm); margin-bottom: 8px; display: flex; align-items: center; justify-content: space-between;">
                                <span><strong>#${idx + 1}</strong> ${item.title}</span>
                                <small style="color: var(--text-muted);">${item.duration || 'LIVE'}</small>
                            </li>
                        `).join("");
                    } else {
                        queueList.innerHTML = `<li style="text-align:center; color:var(--text-muted); padding: 20px;">Queue is empty</li>`;
                    }
                }
            } else {
                if (playerActiveView) playerActiveView.classList.add("hidden");
                if (playerEmptyView) playerEmptyView.style.display = "block";
                if (trackArtwork) trackArtwork.classList.remove("playing");
                if (queueList) queueList.innerHTML = `<li style="text-align:center; color:var(--text-muted); padding: 24px;">No active queue. Play a song with <code>&play</code>!</li>`;
            }
        } catch (err) {
            console.error("Error loading music state:", err);
        }
    }

    if (btnPlayPause) {
        btnPlayPause.addEventListener("click", async () => {
            const action = localIsPlaying ? "pause" : "resume";
            await fetch("/api/music/control", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ guild_id: selectedGuildId, action: action })
            });
            fetchMusicState();
        });
    }

    if (btnSkip) {
        btnSkip.addEventListener("click", async () => {
            await fetch("/api/music/control", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ guild_id: selectedGuildId, action: "skip" })
            });
            fetchMusicState();
        });
    }

    if (volumeSlider) {
        volumeSlider.addEventListener("change", async () => {
            const vol = parseInt(volumeSlider.value);
            if (volumeValDisplay) volumeValDisplay.textContent = `${vol}%`;
            await fetch("/api/music/control", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ guild_id: selectedGuildId, action: "volume", value: vol })
            });
        });
    }

    // Polling music
    fetchMusicState();
    setInterval(fetchMusicState, 3000);

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

            if (warningsBody) {
                if (data.warnings && data.warnings.length > 0) {
                    warningsBody.innerHTML = data.warnings.map(w => `
                        <tr>
                            <td><code>#${w.id}</code></td>
                            <td><code>${w.user_id}</code></td>
                            <td><strong>${w.username}</strong></td>
                            <td>${w.reason || 'Misconduct'}</td>
                            <td style="color:var(--text-muted); font-size:0.8rem;">${w.timestamp}</td>
                        </tr>
                    `).join("");
                } else {
                    warningsBody.innerHTML = `<tr><td colspan="5" style="text-align:center; padding:32px; color:var(--text-muted);"><i class="fa-solid fa-shield-check" style="font-size:1.6rem; color:var(--accent-emerald); display:block; margin-bottom:8px;"></i>No warnings logged. Server is clean!</td></tr>`;
                }
            }

            if (tempbansBody) {
                if (data.tempbans && data.tempbans.length > 0) {
                    tempbansBody.innerHTML = data.tempbans.map(tb => `
                        <tr>
                            <td><code>${tb.user_id}</code></td>
                            <td><strong>${tb.username}</strong></td>
                            <td style="color:var(--accent-rose); font-weight:600;">${tb.unban_time}</td>
                        </tr>
                    `).join("");
                } else {
                    tempbansBody.innerHTML = `<tr><td colspan="3" style="text-align:center; padding:28px; color:var(--text-muted);">No active temporary bans.</td></tr>`;
                }
            }
        } catch (err) {
            console.error("Error loading moderation logs:", err);
            if (warningsBody) warningsBody.innerHTML = `<tr><td colspan="5" style="text-align:center; color:var(--accent-rose); padding:24px;">Failed to fetch warning logs.</td></tr>`;
        }
    }

    // ==========================================
    // ⚔️ RPG ADVENTURERS & CUSTOM TAGS
    // ==========================================
    async function fetchRPG() {
        if (!selectedGuildId) return;
        const rpgBody = document.getElementById("rpg-table-body");
        const tagsBody = document.getElementById("tags-table-body");
        const respondersBody = document.getElementById("responders-table-body");

        try {
            const res = await fetch(`/api/rpg/players?guild_id=${selectedGuildId}`);
            const data = await res.json();

            if (rpgBody) {
                if (data.players && data.players.length > 0) {
                    rpgBody.innerHTML = data.players.map(p => `
                        <tr>
                            <td><strong>${p.username}</strong><br><small style="color:var(--text-muted);"><code>${p.user_id}</code></small></td>
                            <td><span class="badge music-badge">${p.class}</span></td>
                            <td><strong>Lvl ${p.level}</strong></td>
                            <td>${(p.xp || 0).toLocaleString()} XP</td>
                            <td>❤️ ${p.hp}</td>
                            <td>⚔️ ${p.attack} | 🛡️ ${p.defense}</td>
                            <td style="color:var(--accent-emerald); font-weight:700;">$${(p.coins || 0).toLocaleString()}</td>
                            <td>🗡️ ${p.weapon}<br>🛡️ ${p.armor}</td>
                            <td>🏰 Floor ${p.floor}</td>
                        </tr>
                    `).join("");
                } else {
                    rpgBody.innerHTML = `<tr><td colspan="9" style="text-align:center; padding:32px; color:var(--text-muted);"><i class="fa-solid fa-dice-d20" style="font-size:1.8rem; color:var(--accent-gold); display:block; margin-bottom:8px;"></i>No active hero profiles in this server. Start an adventure with <code>&chooseclass</code>!</td></tr>`;
                }
            }

            // Fetch custom tags & autoresponders
            const fRes = await fetch(`/api/features/active?guild_id=${selectedGuildId}`);
            const fData = await fRes.json();

            if (tagsBody) {
                if (fData.custom_tags && fData.custom_tags.length > 0) {
                    tagsBody.innerHTML = fData.custom_tags.map(t => `
                        <tr>
                            <td><code>&${t.tag_name}</code></td>
                            <td>${t.author}</td>
                            <td>${(t.uses || 0).toLocaleString()}</td>
                        </tr>
                    `).join("");
                } else {
                    tagsBody.innerHTML = `<tr><td colspan="3" style="text-align:center; padding:24px; color:var(--text-muted);">No custom tags yet. Create one with <code>&tag create &lt;name&gt; &lt;content&gt;</code>!</td></tr>`;
                }
            }

            if (respondersBody) {
                if (fData.autoresponders && fData.autoresponders.length > 0) {
                    respondersBody.innerHTML = fData.autoresponders.map(ar => `
                        <tr>
                            <td><code>${ar.trigger}</code></td>
                            <td><small>${ar.response}</small></td>
                            <td><span class="badge">${ar.is_exact ? 'Exact' : 'Substring'}</span></td>
                        </tr>
                    `).join("");
                } else {
                    respondersBody.innerHTML = `<tr><td colspan="3" style="text-align:center; padding:24px; color:var(--text-muted);">No autoresponders configured. Add one with <code>&autoresponder add</code>!</td></tr>`;
                }
            }
        } catch (err) {
            console.error("Error loading RPG / Tags:", err);
        }
    }

    // ==========================================
    // 🎁 GIVEAWAYS & PREFIX CONFIG
    // ==========================================
    async function fetchFeatures() {
        if (!selectedGuildId) return;
        const giveawaysBody = document.getElementById("giveaways-table-body");

        try {
            const res = await fetch(`/api/features/active?guild_id=${selectedGuildId}`);
            const data = await res.json();

            if (giveawaysBody) {
                if (data.giveaways && data.giveaways.length > 0) {
                    giveawaysBody.innerHTML = data.giveaways.map(g => `
                        <tr>
                            <td><strong>${g.prize}</strong></td>
                            <td>🏆 ${g.winners} Winners</td>
                            <td>${g.host}</td>
                            <td><small>${new Date(g.end_time * 1000).toLocaleString()}</small></td>
                            <td><span class="badge music-badge">Active</span></td>
                        </tr>
                    `).join("");
                } else {
                    giveawaysBody.innerHTML = `<tr><td colspan="5" style="text-align:center; padding:32px; color:var(--text-muted);"><i class="fa-solid fa-gift" style="font-size:1.8rem; color:var(--accent-purple); display:block; margin-bottom:8px;"></i>No active giveaways scheduled. Start one with <code>&gstart 10m 1 Nitro</code>!</td></tr>`;
                }
            }

            fetchLevelConfig();
            fetchPrefixConfig();
        } catch (err) {
            console.error("Error loading features:", err);
        }
    }

    // ==========================================
    // 🏆 LEADERBOARDS (XP & ECONOMY)
    // ==========================================
    async function fetchLeaderboards() {
        if (!selectedGuildId) return;
        const levelsBody = document.getElementById("levels-leaderboard-body");
        const ecoBody = document.getElementById("eco-leaderboard-body");

        try {
            const res = await fetch(`/api/leaderboards?guild_id=${selectedGuildId}`);
            const data = await res.json();

            if (levelsBody) {
                if (data.levels && data.levels.length > 0) {
                    levelsBody.innerHTML = data.levels.map((l, i) => `
                        <tr>
                            <td><strong>#${i + 1}</strong></td>
                            <td>${l.username}</td>
                            <td><span class="badge music-badge">Lvl ${l.level}</span></td>
                            <td>${(l.xp || 0).toLocaleString()} XP</td>
                        </tr>
                    `).join("");
                } else {
                    levelsBody.innerHTML = `<tr><td colspan="4" style="text-align:center; padding:28px; color:var(--text-muted);">No leveled members yet. Chat to earn XP!</td></tr>`;
                }
            }

            if (ecoBody) {
                if (data.economy && data.economy.length > 0) {
                    ecoBody.innerHTML = data.economy.map((e, i) => `
                        <tr>
                            <td><strong>#${i + 1}</strong></td>
                            <td>${e.username}</td>
                            <td style="color:var(--accent-emerald); font-weight:700;">$${(e.net_worth || 0).toLocaleString()}</td>
                        </tr>
                    `).join("");
                } else {
                    ecoBody.innerHTML = `<tr><td colspan="3" style="text-align:center; padding:28px; color:var(--text-muted);">No economy records found. Claim daily coins with <code>&daily</code>!</td></tr>`;
                }
            }
        } catch (err) {
            console.error("Error loading leaderboards:", err);
        }
    }

    // ==========================================
    // ⚙️ PREFIX & LEVEL CONFIG SAVERS
    // ==========================================
    window.fetchPrefixConfig = async function() {
        if (!selectedGuildId) return;
        try {
            const res = await fetch(`/api/prefix?guild_id=${selectedGuildId}`);
            const data = await res.json();
            if (data && data.prefix) {
                const input = document.getElementById("server-prefix-input");
                if (input) input.value = data.prefix;
            }
        } catch (err) {
            console.error("Error fetching prefix:", err);
        }
    };

    window.savePrefixConfig = async function() {
        if (!selectedGuildId) return;
        const statusSpan = document.getElementById("prefix-config-status");
        const input = document.getElementById("server-prefix-input");
        if (!input) return;

        const newPrefix = input.value.trim() || "&";
        if (statusSpan) {
            statusSpan.style.color = "#8E95A5";
            statusSpan.textContent = "Saving...";
        }

        try {
            const res = await fetch("/api/prefix", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ guild_id: selectedGuildId, prefix: newPrefix })
            });
            const data = await res.json();
            if (data.success && statusSpan) {
                statusSpan.style.color = "#2ECC71";
                statusSpan.textContent = `✅ Prefix set to "${data.prefix}"!`;
                setTimeout(() => { statusSpan.textContent = ""; }, 4000);
            } else if (statusSpan) {
                statusSpan.style.color = "#FF4757";
                statusSpan.textContent = "❌ Failed to save prefix.";
            }
        } catch (err) {
            if (statusSpan) {
                statusSpan.style.color = "#FF4757";
                statusSpan.textContent = "❌ Network error.";
            }
        }
    };

    window.fetchLevelConfig = async function() {
        if (!selectedGuildId) return;
        try {
            const res = await fetch(`/api/level_config?guild_id=${selectedGuildId}`);
            const data = await res.json();
            if (data) {
                const elStatus = document.getElementById("level-status-select");
                const elChan = document.getElementById("level-channel-select");
                const elTpl = document.getElementById("level-template-input");
                if (elStatus) elStatus.value = data.is_enabled ? "enabled" : "disabled";
                if (elChan) elChan.value = data.channel_id || "current";
                if (elTpl) elTpl.value = data.custom_msg || "🎉 **Level Up!** Congratulations {user}, you reached **Level {level}**! ⭐";
            }
        } catch (err) {
            console.error("Error loading level config:", err);
        }
    };

    window.saveLevelConfig = async function() {
        if (!selectedGuildId) return;
        const statusSpan = document.getElementById("level-config-status");
        const isEnabled = document.getElementById("level-status-select").value === "enabled";
        const channelId = document.getElementById("level-channel-select").value;
        const customMsg = document.getElementById("level-template-input").value;

        if (statusSpan) {
            statusSpan.style.color = "#8E95A5";
            statusSpan.textContent = "Saving...";
        }

        try {
            const res = await fetch("/api/level_config", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    guild_id: selectedGuildId,
                    is_enabled: isEnabled,
                    channel_id: channelId,
                    custom_msg: customMsg
                })
            });
            const data = await res.json();
            if (data.success && statusSpan) {
                statusSpan.style.color = "#2ECC71";
                statusSpan.textContent = "✅ Leveling settings saved successfully!";
                setTimeout(() => { statusSpan.textContent = ""; }, 4000);
            } else if (statusSpan) {
                statusSpan.style.color = "#FF4757";
                statusSpan.textContent = "❌ Failed to save.";
            }
        } catch (err) {
            if (statusSpan) {
                statusSpan.style.color = "#FF4757";
                statusSpan.textContent = "❌ Network error.";
            }
        }
    };

    // Auto-fetch active guild data on load
    fetchPrefixConfig();
    fetchLevelConfig();
});
