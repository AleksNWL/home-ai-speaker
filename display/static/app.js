const STATE_LABELS = {
  idle: "ожидание",
  listening: "слушаю",
  thinking: "думаю",
  speaking: "говорю",
  playing: "музыка",
};

const orb = document.getElementById("orb");
const stateLabel = document.getElementById("stateLabel");
const transcript = document.getElementById("transcript");
const reply = document.getElementById("reply");
const nowPlaying = document.getElementById("nowPlaying");
const clock = document.getElementById("clock");

function tickClock() {
  const now = new Date();
  clock.textContent = now.toLocaleTimeString("ru-RU", {
    hour: "2-digit",
    minute: "2-digit",
  });
}

async function refresh() {
  try {
    const res = await fetch("/api/status", { cache: "no-store" });
    if (!res.ok) return;
    const data = await res.json();
    const state = data.state || "idle";
    orb.className = `orb state-${state}`;
    orb.dataset.state = state;
    stateLabel.textContent = STATE_LABELS[state] || state;
    transcript.textContent = data.last_transcript ? `«${data.last_transcript}»` : "";
    reply.textContent = data.last_reply || "";
    nowPlaying.textContent = data.now_playing || "";
  } catch (_) {
    /* kiosk may boot before server */
  }
}

tickClock();
setInterval(tickClock, 1000);
refresh();
setInterval(refresh, 700);
