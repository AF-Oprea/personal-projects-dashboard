(() => {
  "use strict";

  const $ = (id) => document.getElementById(id);

  const state = {
    player: null,
    ytReady: false,
    playlistId: null,
    playing: false,
    tick: 0,
    titles: new Map(),
  };

  window.onYouTubeIframeAPIReady = () => {
    state.ytReady = true;
  };

  function embedUrl(playlistId, serverUrl) {
    const url = new URL(
      serverUrl && serverUrl.includes("/embed/videoseries")
        ? serverUrl
        : "https://www.youtube.com/embed/videoseries"
    );
    url.searchParams.set("list", playlistId);
    url.searchParams.set("autoplay", "1");
    url.searchParams.set("loop", "1");
    url.searchParams.set("enablejsapi", "1");
    url.searchParams.set("origin", location.origin);
    return url.toString();
  }

  function mountIframe(src) {
    if (state.player && typeof state.player.destroy === "function") {
      try {
        state.player.destroy();
      } catch {
        /* iframe will be replaced anyway */
      }
      state.player = null;
    }
    const host = $("screen-host");
    host.replaceChildren();
    const iframe = document.createElement("iframe");
    iframe.id = "screen";
    iframe.className = "screen";
    iframe.title = "YouTube video player";
    iframe.allow =
      "accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share";
    iframe.referrerPolicy = "strict-origin-when-cross-origin";
    iframe.allowFullscreen = true;
    iframe.src = src;
    host.appendChild(iframe);
    document.body.classList.add("is-tuned");
  }

  function waitForApi() {
    return new Promise((resolve, reject) => {
      const started = Date.now();
      const timer = window.setInterval(() => {
        if (state.ytReady && window.YT && window.YT.Player) {
          window.clearInterval(timer);
          resolve();
        } else if (Date.now() - started > 8000) {
          window.clearInterval(timer);
          reject(new Error("YouTube IFrame API did not load."));
        }
      }, 50);
    });
  }

  function bindPlayer() {
    return new Promise((resolve) => {
      const el = $("screen");
      if (!window.YT || !window.YT.Player || !el || el.tagName !== "IFRAME") {
        resolve(null);
        return;
      }
      let settled = false;
      const finish = (player) => {
        if (settled) return;
        settled = true;
        resolve(player || null);
      };
      const timer = window.setTimeout(() => finish(state.player), 8000);
      state.player = new YT.Player("screen", {
        playerVars: {
          listType: "playlist",
          list: state.playlistId,
          index: 0,
          autoplay: 1,
          loop: 1,
          modestbranding: 1,
          rel: 0,
          playsinline: 1,
          enablejsapi: 1,
          controls: 1,
        },
        events: {
          onReady: (event) => {
            window.clearTimeout(timer);
            state.player = event.target;
            onPlayerReady();
            finish(event.target);
          },
          onStateChange: onPlayerState,
          onError: () => skipUnavailable(),
        },
      });
    });
  }

  function onPlayerReady() {
    if (!state.player) return;
    if (state.player.setVolume) state.player.setVolume(Number($("volume").value));
    if (state.player.setLoop) state.player.setLoop($("loop").checked);
    if ($("shuffle").checked && state.player.setShuffle) state.player.setShuffle(true);
    refreshButtons();
  }

  function onPlayerState(event) {
    const YTState = window.YT ? window.YT.PlayerState : {};
    state.playing = event.data === YTState.PLAYING;
    document.body.classList.toggle("is-live", state.playing);
    $("air-label").textContent = state.playing ? "On air" : state.playlistId ? "Paused" : "Standby";
    refreshNowPlaying();
    refreshButtons();
    if (event.data === YTState.PLAYING || event.data === YTState.CUED) {
      hydrateQueue();
    }
    if (event.data === YTState.PLAYING) startTick();
  }

  function skipUnavailable() {
    if (!state.player || typeof state.player.nextVideo !== "function") return;
    try {
      state.player.nextVideo();
    } catch {
      /* playlist may be empty */
    }
  }

  function startTick() {
    window.clearInterval(state.tick);
    state.tick = window.setInterval(refreshNowPlaying, 400);
  }

  function formatTime(total) {
    if (!Number.isFinite(total) || total < 0) return "0:00";
    const seconds = Math.floor(total);
    const m = Math.floor(seconds / 60);
    const s = seconds % 60;
    return `${m}:${String(s).padStart(2, "0")}`;
  }

  function refreshNowPlaying() {
    if (!state.player || typeof state.player.getVideoData !== "function") return;
    const data = state.player.getVideoData() || {};
    if (data.title) $("title").textContent = data.title;
    if (data.author) $("author").textContent = data.author;
    const duration = state.player.getDuration ? state.player.getDuration() : 0;
    const current = state.player.getCurrentTime ? state.player.getCurrentTime() : 0;
    $("elapsed").textContent = formatTime(current);
    $("duration").textContent = formatTime(duration);
    const pct = duration ? Math.min(100, (current / duration) * 100) : 0;
    $("bar").style.width = `${pct}%`;
    highlightCurrent(data.video_id);
  }

  function refreshButtons() {
    const tuned = Boolean(state.playlistId && state.player);
    $("toggle").disabled = !tuned;
    $("prev").disabled = !tuned;
    $("next").disabled = !tuned;
    $("toggle").textContent = state.playing ? "Pause" : "Tune In";
  }

  async function hydrateQueue() {
    if (!state.player || typeof state.player.getPlaylist !== "function") return;
    const ids = state.player.getPlaylist() || [];
    if (!ids.length) {
      $("queue").innerHTML = "";
      $("queue-count").textContent = "Waiting for the playlist…";
      return;
    }
    $("queue-count").textContent = `${ids.length} tracks`;
    renderQueue(ids);
    const missing = ids.filter((id) => !state.titles.has(id)).slice(0, 24);
    if (!missing.length) return;
    try {
      const response = await fetch("/api/meta", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ids: missing }),
      });
      const payload = await response.json();
      for (const track of payload.tracks || []) {
        if (track && track.id) state.titles.set(track.id, track);
      }
      renderQueue(ids);
    } catch {
      /* titles stay as ids */
    }
  }

  function renderQueue(ids) {
    const currentId =
      state.player && state.player.getVideoData ? state.player.getVideoData().video_id : null;
    $("queue").innerHTML = ids
      .map((id, index) => {
        const meta = state.titles.get(id) || {};
        const title = escapeHtml(meta.title || `Track ${index + 1}`);
        const author = escapeHtml(meta.author || id);
        const thumb = escapeAttr(meta.thumbnail || `https://i.ytimg.com/vi/${id}/mqdefault.jpg`);
        const current = id === currentId ? " is-current" : "";
        return `<li class="${current}" data-id="${escapeAttr(id)}">
          <img src="${thumb}" alt="" />
          <div>
            <h3>${title}</h3>
            <p>${author}</p>
          </div>
        </li>`;
      })
      .join("");
  }

  function highlightCurrent(videoId) {
    document.querySelectorAll(".queue li").forEach((node) => {
      node.classList.toggle("is-current", node.getAttribute("data-id") === videoId);
    });
  }

  function escapeHtml(value) {
    return String(value)
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;");
  }

  function escapeAttr(value) {
    return escapeHtml(value).replaceAll("'", "&#39;");
  }

  async function applyStation(station) {
    state.playlistId = station.playlist_id;
    $("playlist").value = station.source_url || station.watch_url || "";
    $("freq").textContent = `${station.frequency || "87.5"} FM`;
    $("shuffle").checked = Boolean(station.shuffle);
    $("loop").checked = station.loop !== false;
    $("title").textContent = "Cueing the playlist…";
    $("author").textContent = "The station is linking your YouTube list.";
    showError("");
    const src = embedUrl(station.playlist_id, station.embed_url);
    mountIframe(src);
    refreshButtons();
    try {
      await waitForApi();
      const player = await bindPlayer();
      if (player && player.setLoop) player.setLoop($("loop").checked);
      if (player && $("shuffle").checked && player.setShuffle) player.setShuffle(true);
    } catch {
      $("author").textContent = "Playlist is in the player. Use YouTube controls if Tune In stays off.";
    }
    refreshButtons();
  }

  function showError(message, options = {}) {
    const node = $("form-error");
    node.hidden = !message;
    node.textContent = message || "";
    if ($("idle-copy") && (options.idle || !message)) {
      $("idle-copy").textContent = options.idle
        ? message
        : "Link a playlist to go on air.";
    }
  }

  $("tune-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    showError("");
    const url = $("playlist").value.trim();
    try {
      const response = await fetch("/api/tune", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url }),
      });
      const payload = await response.json();
      if (!response.ok || !payload.tuned) {
        throw new Error(payload.error || "Could not tune that playlist.");
      }
      await applyStation(payload.station);
    } catch (err) {
      showError(err.message || "Could not tune that playlist.");
    }
  });

  $("toggle").addEventListener("click", () => {
    if (!state.player) return;
    if (state.playing) state.player.pauseVideo();
    else state.player.playVideo();
  });

  $("prev").addEventListener("click", () => state.player && state.player.previousVideo());
  $("next").addEventListener("click", () => state.player && state.player.nextVideo());

  $("volume").addEventListener("input", (event) => {
    if (state.player) state.player.setVolume(Number(event.target.value));
  });

  $("shuffle").addEventListener("change", async (event) => {
    if (state.player && state.player.setShuffle) state.player.setShuffle(event.target.checked);
    await fetch("/api/control", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ shuffle: event.target.checked }),
    });
    hydrateQueue();
  });

  $("loop").addEventListener("change", async (event) => {
    if (state.player && state.player.setLoop) state.player.setLoop(event.target.checked);
    await fetch("/api/control", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ loop: event.target.checked }),
    });
  });

  $("queue").addEventListener("click", (event) => {
    const row = event.target.closest("li[data-id]");
    if (!row || !state.player) return;
    const ids = state.player.getPlaylist() || [];
    const index = ids.indexOf(row.getAttribute("data-id"));
    if (index >= 0 && state.player.playVideoAt) state.player.playVideoAt(index);
  });

  document.addEventListener("keydown", (event) => {
    if (event.target.matches("input, textarea")) return;
    if (event.code === "Space") {
      event.preventDefault();
      $("toggle").click();
    } else if (event.key === "n") $("next").click();
    else if (event.key === "p") $("prev").click();
  });

  async function boot() {
    const params = new URLSearchParams(location.search);
    const preset = params.get("list") || params.get("url") || "";
    if (preset) $("playlist").value = preset.startsWith("http") ? preset : `https://www.youtube.com/playlist?list=${preset}`;

    try {
      const response = await fetch("/api/station");
      const payload = await response.json();
      if (payload.tuned && payload.station) {
        if (!preset) $("playlist").value = payload.station.source_url || payload.station.watch_url;
        await applyStation(payload.station);
      } else if (preset) {
        $("tune-form").requestSubmit();
      }
    } catch {
      if (preset) $("tune-form").requestSubmit();
    }
  }

  boot();
})();
