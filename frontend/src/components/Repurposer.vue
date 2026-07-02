<script setup>
import { ref, computed, onMounted } from "vue";
import Icon from "./Icon.vue";

const API = import.meta.env.PUBLIC_API_URL || "http://localhost:8787";

const url = ref("");
const persona = ref("Entrepreneur");
const voice = ref("Professionnelle");
const loading = ref(false);
const error = ref("");
const result = ref(null);
const section = ref("overview");
const drawerKey = ref(null);
const exportOpen = ref(false);
const copied = ref(false);
const showTranscript = ref(false);
const quotaInfo = ref(null);

onMounted(async () => {
  try {
    const res = await fetch(`${API}/api/quota`);
    if (res.ok) quotaInfo.value = await res.json();
  } catch { /* silencieux */ }
});

const PERSONAS = [
  "Entrepreneur", "Créateur", "Coach", "SaaS",
  "Agence", "Immobilier", "Finance", "E-commerce",
];
const VOICES = ["Professionnelle", "Directe", "Éducative", "Premium", "Décontractée"];

const NAV_TOP = [
  { key: "overview", label: "Overview", icon: "dashboard" },
  { key: "calendar", label: "Calendrier", icon: "calendar" },
];
const NAV_CONTENT = [
  { key: "posts", label: "Posts", icon: "message" },
  { key: "carousels", label: "Carrousels", icon: "layers" },
  { key: "threads", label: "Threads", icon: "send" },
];
const NAV_BOTTOM = [
  { key: "clips", label: "Clips", icon: "film" },
  { key: "source", label: "Source", icon: "file" },
];

const fmt = computed(() => result.value?.formats ?? {});

// --- Helpers ----------------------------------------------------------------
const chars = (t) => (t || "").length;
const snippet = (t, n = 120) => {
  const s = (t || "").replace(/\n+/g, " ").trim();
  return s.length > n ? s.slice(0, n) + "…" : s;
};

const posts = computed(() => fmt.value.posts ?? []);
const carousel = computed(() => fmt.value.carousel ?? null);
const thread = computed(() => fmt.value.thread ?? []);
const clips = computed(() => fmt.value.clips ?? []);

const stats = computed(() => {
  const platforms = new Set(posts.value.map((p) => p.platform));
  platforms.add("X"); // thread
  return {
    days: fmt.value.weekly_calendar?.length ?? 0,
    contents: posts.value.length + (carousel.value ? 1 : 0) + (thread.value.length ? 1 : 0),
    platforms: platforms.size,
    clips: clips.value.length,
  };
});
const summary = computed(() => [
  { label: "Posts générés", n: posts.value.length, section: "posts" },
  { label: "Carrousels générés", n: carousel.value ? 1 : 0, section: "carousels" },
  { label: "Threads générés", n: thread.value.length ? 1 : 0, section: "threads" },
  { label: "Clips identifiés", n: clips.value.length, section: "clips" },
]);

// --- Drawer -----------------------------------------------------------------
const drawerTitle = computed(() => {
  const k = drawerKey.value;
  if (!k) return "";
  if (k.startsWith("post:")) return `Post ${posts.value[+k.slice(5)]?.platform}`;
  if (k === "carousel") return "Carrousel";
  if (k === "thread") return "Thread";
  return "";
});
function openDrawer(key) { drawerKey.value = key; exportOpen.value = false; copied.value = false; }
function closeDrawer() { drawerKey.value = null; exportOpen.value = false; }

// --- Progression réelle (SSE) -----------------------------------------------
const STEPS = [
  { key: "transcript", label: "Récupération de la transcription" },
  { key: "generate", label: "Génération des contenus" },
];
const stepState = ref({}); // { transcript: 'active'|'done', ... }
const stepDetail = ref({});

async function submit() {
  error.value = "";
  if (!url.value.trim()) return;
  loading.value = true;
  stepState.value = {};
  stepDetail.value = {};
  try {
    const res = await fetch(`${API}/api/process/stream`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url: url.value.trim(), persona: persona.value, voice: voice.value }),
    });
    if (!res.body) throw new Error("Flux indisponible");
    const reader = res.body.getReader();
    const dec = new TextDecoder();
    let buf = "";
    let finished = false;
    while (!finished) {
      const { value, done } = await reader.read();
      if (done) break;
      buf += dec.decode(value, { stream: true });
      const frames = buf.split("\n\n");
      buf = frames.pop();
      for (const frame of frames) {
        if (!frame.trim()) continue;
        let ev = "message", data = "";
        for (const line of frame.split("\n")) {
          if (line.startsWith("event: ")) ev = line.slice(7);
          else if (line.startsWith("data: ")) data += line.slice(6);
        }
        const payload = data ? JSON.parse(data) : {};
        if (ev === "step") {
          stepState.value = { ...stepState.value, [payload.name]: payload.state === "done" ? "done" : "active" };
          if (payload.detail) stepDetail.value = { ...stepDetail.value, [payload.name]: payload.detail };
        } else if (ev === "result") {
          result.value = payload;
          section.value = "overview";
        } else if (ev === "error") {
          error.value = payload.message || "Erreur inconnue";
        } else if (ev === "done") {
          finished = true;
        }
      }
    }
  } catch (e) {
    error.value = e.message;
  } finally {
    loading.value = false;
  }
}
function reset() { result.value = null; error.value = ""; drawerKey.value = null; }

// --- Copie / export ---------------------------------------------------------
function textFor(key) {
  if (key.startsWith("post:")) return posts.value[+key.slice(5)].content;
  if (key === "carousel") {
    const c = carousel.value;
    return [c.title, ...c.slides.map((s, i) => `${i + 1}. ${s}`), c.cta].join("\n\n");
  }
  if (key === "thread") return thread.value.join("\n\n");
  return "";
}
async function copyKey(key) {
  await navigator.clipboard.writeText(textFor(key));
  copied.value = true;
  setTimeout(() => (copied.value = false), 1500);
}
function exportMarkdown(key) {
  const blob = new Blob([textFor(key)], { type: "text/markdown" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = `${key.replace(":", "-")}.md`;
  a.click();
  URL.revokeObjectURL(a.href);
  exportOpen.value = false;
}
</script>

<template>
  <!-- ÉTAT 1 — accueil -->
  <div v-if="!result && !loading" class="landing">
    <div class="intro">
      <div class="logo-lg" v-html="LOGO"></div>
      <h1>Une vidéo entre.<br />Une <span>semaine</span> de contenu sort.</h1>
      <p>Colle un lien YouTube. Repars avec un calendrier éditorial et tous tes
        contenus prêts à publier — posts, carrousels, threads, clips.</p>
    </div>
    <div class="composer">
      <div class="composer-row">
        <input v-model="url" type="url" placeholder="Colle un lien YouTube…" @keyup.enter="submit" />
        <button class="primary" @click="submit">Générer la semaine</button>
      </div>
      <div class="composer-opts">
        <label>Profil <select v-model="persona"><option v-for="p in PERSONAS" :key="p" :value="p">{{ p }}</option></select></label>
        <label>Voix <select v-model="voice"><option v-for="v in VOICES" :key="v" :value="v">{{ v }}</option></select></label>
      </div>
      <p v-if="error" class="error">⚠ {{ error }}</p>
      <p v-if="quotaInfo" class="quota-line">
        <Icon name="sparkles" :size="14" />
        <template v-if="quotaInfo.unlimited">Quota illimité (mode dev)</template>
        <template v-else>{{ quotaInfo.remaining }} / {{ quotaInfo.limit }} vidéos gratuites ce mois</template>
      </p>
    </div>
    <div class="pricing">
      <div class="plan">
        <div class="plan-name">Gratuit</div>
        <div class="price">0$<span>/mois</span></div>
        <ul><li>3 vidéos offertes</li><li>Tous les formats inclus</li><li>Sans carte bancaire</li></ul>
      </div>
      <div class="plan featured">
        <div class="plan-name">Reflow Pro</div>
        <div class="price">19$<span>/mois</span></div>
        <ul><li>30 vidéos par mois</li><li>Historique des générations</li><li>Exports</li><li>Annulation à tout moment</li></ul>
      </div>
    </div>
  </div>

  <!-- ÉTAT 2 — progression -->
  <div v-else-if="loading" class="progress-wrap">
    <div class="progress">
      <div class="progress-title">Génération en cours…</div>
      <ul>
        <li v-for="s in STEPS" :key="s.key" :class="{ done: stepState[s.key] === 'done', active: stepState[s.key] === 'active' }">
          <span class="tick"><Icon v-if="stepState[s.key] === 'done'" name="check" :size="12" /></span>
          {{ s.label }}<span v-if="stepDetail[s.key]" class="step-detail"> · {{ stepDetail[s.key] }}</span>
        </li>
      </ul>
    </div>
  </div>

  <!-- ÉTAT 3 — workspace -->
  <div v-else class="app">
    <aside class="sidebar">
      <div class="side-title" :title="result.title">{{ result.title }}</div>
      <div class="side-meta">{{ result.transcript_source }} · {{ result.quota_remaining === null ? "illimité" : result.quota_remaining + " restant(s)" }}<template v-if="result.from_cache"> · ⚡</template></div>
      <nav>
        <button v-for="s in NAV_TOP" :key="s.key" :class="{ active: section === s.key }" @click="section = s.key">
          <Icon :name="s.icon" :size="17" /> {{ s.label }}
        </button>
        <div class="nav-group">Contenus</div>
        <button v-for="s in NAV_CONTENT" :key="s.key" class="indent" :class="{ active: section === s.key }" @click="section = s.key">
          <Icon :name="s.icon" :size="17" /> {{ s.label }}
        </button>
        <div class="nav-sep"></div>
        <button v-for="s in NAV_BOTTOM" :key="s.key" :class="{ active: section === s.key }" @click="section = s.key">
          <Icon :name="s.icon" :size="17" /> {{ s.label }}
        </button>
      </nav>
      <button class="new" @click="reset"><Icon name="plus" :size="16" /> Nouvelle vidéo</button>
    </aside>

    <section class="workspace">
      <!-- OVERVIEW -->
      <div v-if="section === 'overview'">
        <h2>Semaine générée</h2>
        <p class="lead">Tout ton contenu de la semaine, prêt à publier.</p>
        <div class="stat-row">
          <div class="stat"><div class="stat-n">1</div><div class="stat-l">vidéo analysée</div></div>
          <div class="stat"><div class="stat-n">{{ stats.days }}</div><div class="stat-l">jours de contenu</div></div>
          <div class="stat"><div class="stat-n">{{ stats.contents }}</div><div class="stat-l">contenus générés</div></div>
          <div class="stat"><div class="stat-n">{{ stats.platforms }}</div><div class="stat-l">plateformes</div></div>
          <div class="stat"><div class="stat-n">{{ stats.clips }}</div><div class="stat-l">idées de clips</div></div>
        </div>
        <div class="breakdown">
          <div v-for="b in summary" :key="b.label" class="bd-row" @click="section = b.section">
            <span class="bd-plat">{{ b.label }}</span>
            <span class="bd-count">{{ b.n }}</span>
            <Icon name="chevron-right" :size="16" class="bd-arrow" />
          </div>
        </div>
        <h3>Calendrier de publication</h3>
        <div class="calendar">
          <div v-for="(d, i) in fmt.weekly_calendar" :key="i" class="day">
            <div class="day-head">{{ d.day }}</div>
            <div class="day-chan">{{ d.channel }}</div>
            <p>{{ d.action }}</p>
          </div>
        </div>
      </div>

      <!-- CALENDRIER -->
      <div v-else-if="section === 'calendar'">
        <h2>Calendrier éditorial</h2>
        <div class="calendar">
          <div v-for="(d, i) in fmt.weekly_calendar" :key="i" class="day">
            <div class="day-head">{{ d.day }}</div>
            <div class="day-chan">{{ d.channel }}</div>
            <p>{{ d.action }}</p>
          </div>
        </div>
      </div>

      <!-- POSTS -->
      <div v-else-if="section === 'posts'">
        <h2>Posts</h2>
        <div class="cards">
          <div v-for="(p, i) in posts" :key="i" class="content-card">
            <div class="cc-top"><span class="tag">{{ p.platform }}</span><span class="cc-meta">{{ chars(p.content) }} caractères</span></div>
            <p class="cc-preview">{{ snippet(p.content) }}</p>
            <div class="cc-actions">
              <button class="btn-primary" @click="openDrawer('post:' + i)"><Icon name="open" :size="15" /> Ouvrir</button>
              <button class="btn-ghost" @click="copyKey('post:' + i)"><Icon name="copy" :size="15" /></button>
            </div>
          </div>
        </div>
      </div>

      <!-- CARROUSELS -->
      <div v-else-if="section === 'carousels'">
        <h2>Carrousel</h2>
        <div class="cards">
          <div class="content-card">
            <div class="cc-top"><span class="tag">LinkedIn · Instagram · TikTok</span><span class="cc-meta">{{ carousel.slides.length }} slides</span></div>
            <div class="cc-title">{{ carousel.title }}</div>
            <p class="cc-preview">{{ carousel.slides[0] }}</p>
            <div class="cc-actions">
              <button class="btn-primary" @click="openDrawer('carousel')"><Icon name="open" :size="15" /> Ouvrir</button>
              <button class="btn-ghost" @click="copyKey('carousel')"><Icon name="copy" :size="15" /></button>
            </div>
          </div>
        </div>
      </div>

      <!-- THREADS -->
      <div v-else-if="section === 'threads'">
        <h2>Thread</h2>
        <div class="cards">
          <div class="content-card">
            <div class="cc-top"><span class="tag">X · Threads</span><span class="cc-meta">{{ thread.length }} posts</span></div>
            <p class="cc-preview">{{ snippet(thread[0]) }}</p>
            <div class="cc-actions">
              <button class="btn-primary" @click="openDrawer('thread')"><Icon name="open" :size="15" /> Ouvrir</button>
              <button class="btn-ghost" @click="copyKey('thread')"><Icon name="copy" :size="15" /></button>
            </div>
          </div>
        </div>
      </div>

      <!-- CLIPS -->
      <div v-else-if="section === 'clips'">
        <h2>Idées de clips</h2>
        <div class="clips">
          <div v-for="(m, i) in clips" :key="i" class="clip">
            <div class="clip-head">
              <span v-if="m.timestamp" class="clip-ts">{{ m.timestamp }}</span>
              <span class="clip-title">{{ m.title }}</span>
            </div>
            <p class="clip-hook">« {{ m.hook }} »</p>
            <p class="clip-why">{{ m.why }}</p>
          </div>
        </div>
      </div>

      <!-- SOURCE -->
      <div v-else-if="section === 'source'">
        <h2>Source</h2>
        <div class="summary-card">
          <div class="sum-head"><Icon name="sparkles" :size="16" /> Résumé</div>
          <p>{{ fmt.summary }}</p>
          <div class="sum-head" style="margin-top:16px"><Icon name="layers" :size="16" /> Points clés</div>
          <ul class="key-points"><li v-for="(m, i) in clips" :key="i">{{ m.title }}</li></ul>
        </div>
        <button class="accordion" @click="showTranscript = !showTranscript">
          <Icon :name="showTranscript ? 'chevron-down' : 'chevron-right'" :size="16" />
          Transcript complet ({{ result.transcript_chars.toLocaleString() }} caractères)
        </button>
        <div v-if="showTranscript" class="doc-page muted">{{ result.transcript }}</div>
      </div>
    </section>
  </div>

  <!-- DRAWER -->
  <div v-if="drawerKey" class="drawer-overlay" @click.self="closeDrawer">
    <div class="drawer">
      <header class="drawer-head">
        <h3>{{ drawerTitle }}</h3>
        <div class="drawer-actions">
          <div class="export">
            <button class="btn-ghost" @click="exportOpen = !exportOpen"><Icon name="download" :size="15" /> Exporter</button>
            <div v-if="exportOpen" class="export-menu">
              <button @click="copyKey(drawerKey); exportOpen = false"><Icon name="copy" :size="14" /> {{ copied ? 'Copié' : 'Copier' }}</button>
              <button @click="exportMarkdown(drawerKey)"><Icon name="file-text" :size="14" /> Markdown</button>
              <button disabled>Notion <span class="soon">bientôt</span></button>
              <button disabled>PDF <span class="soon">bientôt</span></button>
            </div>
          </div>
          <button class="btn-icon" @click="closeDrawer"><Icon name="close" :size="18" /></button>
        </div>
      </header>
      <div class="drawer-body">
        <!-- Post -->
        <div v-if="drawerKey.startsWith('post:')" class="mock li">
          <div class="li-top"><div class="avatar"></div><div><div class="name">Ton nom</div><div class="sub">{{ posts[+drawerKey.slice(5)].platform }} · à l'instant</div></div></div>
          <p class="post-body">{{ posts[+drawerKey.slice(5)].content }}</p>
          <div class="li-actions"><span>👍 J'aime</span><span>💬 Commenter</span><span>↗ Partager</span></div>
        </div>
        <!-- Carrousel -->
        <div v-else-if="drawerKey === 'carousel'">
          <div class="slide-grid">
            <div class="slide cover">{{ carousel.title }}</div>
            <div v-for="(s, i) in carousel.slides" :key="i" class="slide"><span class="slide-n">{{ i + 1 }}</span>{{ s }}</div>
          </div>
          <p class="cta">{{ carousel.cta }}</p>
        </div>
        <!-- Thread -->
        <div v-else-if="drawerKey === 'thread'" class="thread-view">
          <div v-for="(t, i) in thread" :key="i" class="tweet">
            <div class="avatar sm"></div>
            <div class="tweet-body"><div class="name">Ton nom <span class="handle">@toi · {{ i + 1 }}/{{ thread.length }}</span></div><p>{{ t }}</p></div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  data() {
    return {
      LOGO: '<svg viewBox="0 0 24 24" width="44" height="44"><rect width="24" height="24" rx="7" fill="#635bff"/><g stroke="#fff" stroke-width="1.4" stroke-linecap="round"><path d="M8 12h4M12 12l4-5M12 12l4 5"/></g><g fill="#fff"><circle cx="7.5" cy="12" r="1.7"/><circle cx="16.5" cy="7" r="1.7"/><circle cx="16.5" cy="12" r="1.7"/><circle cx="16.5" cy="17" r="1.7"/></g></svg>',
    };
  },
};
</script>

<style scoped>
h2 { font-size: 1.4rem; margin: 0 0 4px; letter-spacing: -0.02em; }
h3 { font-size: 1.05rem; margin: 32px 0 14px; letter-spacing: -0.01em; }
.lead { color: var(--muted); margin: 0 0 24px; }

/* Accueil */
.landing { max-width: 760px; margin: 0 auto; padding: 56px 24px 64px; }
.intro { text-align: center; margin-bottom: 40px; }
.logo-lg { display: flex; justify-content: center; margin-bottom: 22px; }
.intro h1 { font-size: 2.5rem; line-height: 1.12; letter-spacing: -0.02em; margin: 0 0 16px; }
.intro h1 span { color: var(--accent); }
.intro p { color: var(--muted); font-size: 1.1rem; max-width: 560px; margin: 0 auto; }
.composer { background: var(--panel); border: 1px solid var(--line); border-radius: 14px; padding: 16px; }
.composer-row { display: flex; gap: 10px; }
input { flex: 1; background: var(--bg); border: 1px solid var(--line); border-radius: 9px; padding: 13px 14px; color: var(--text); font-size: 0.98rem; }
input:focus { outline: none; border-color: var(--accent); }
.primary { background: var(--accent); color: #fff; border: none; border-radius: 9px; padding: 0 20px; font-weight: 600; cursor: pointer; white-space: nowrap; }
.composer-opts { display: flex; gap: 18px; margin-top: 12px; }
.composer-opts label { display: flex; align-items: center; gap: 8px; color: var(--muted); font-size: 0.88rem; }
select { background: var(--bg); border: 1px solid var(--line); border-radius: 8px; padding: 7px 9px; color: var(--text); font-size: 0.88rem; }
.error { color: #ff7a7a; margin: 12px 0 0; font-size: 0.9rem; }
.quota-line { display: flex; align-items: center; gap: 7px; color: var(--muted); font-size: 0.85rem; margin: 12px 2px 0; }
.quota-line :deep(svg) { color: var(--accent); }
.pricing { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-top: 48px; }
@media (max-width: 620px) { .pricing { grid-template-columns: 1fr; } }
.plan { background: var(--panel); border: 1px solid var(--line); border-radius: 12px; padding: 22px; }
.plan.featured { border-color: var(--accent); }
.plan-name { font-weight: 650; }
.price { font-size: 1.9rem; font-weight: 700; margin: 8px 0 14px; }
.price span { font-size: 0.9rem; color: var(--muted); font-weight: 400; }
.plan ul { list-style: none; padding: 0; margin: 0; }
.plan li { padding: 6px 0 6px 22px; position: relative; font-size: 0.92rem; }
.plan li::before { content: "✓"; position: absolute; left: 0; color: var(--ok); }

/* Progression */
.progress-wrap { display: flex; justify-content: center; padding: 120px 24px; }
.progress { background: var(--panel); border: 1px solid var(--line); border-radius: 14px; padding: 28px 32px; min-width: 340px; }
.progress-title { font-weight: 600; margin-bottom: 18px; }
.progress ul { list-style: none; padding: 0; margin: 0; }
.progress li { display: flex; align-items: center; gap: 12px; padding: 9px 0; color: var(--faint); font-size: 0.95rem; }
.progress li.done, .progress li.active { color: var(--text); }
.step-detail { color: var(--faint); }
.tick { width: 18px; height: 18px; border-radius: 50%; border: 1px solid var(--line); display: inline-flex; align-items: center; justify-content: center; color: var(--ok); flex-shrink: 0; }
.progress li.done .tick { border-color: var(--ok); }
.progress li.active .tick { border-color: var(--accent); border-top-color: transparent; animation: spin 0.7s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }

/* Workspace */
.app { display: grid; grid-template-columns: 244px 1fr; min-height: calc(100vh - 56px); }
.sidebar { border-right: 1px solid var(--line-soft); padding: 20px 14px; display: flex; flex-direction: column; }
.side-title { font-weight: 600; font-size: 0.95rem; line-height: 1.3; overflow: hidden; text-overflow: ellipsis; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; }
.side-meta { color: var(--faint); font-size: 0.78rem; margin: 6px 0 18px; }
.sidebar nav { flex: 1; display: flex; flex-direction: column; gap: 2px; }
.sidebar nav button { display: flex; align-items: center; gap: 11px; width: 100%; text-align: left; background: transparent; border: none; color: var(--muted); padding: 9px 11px; border-radius: 8px; font-size: 0.92rem; cursor: pointer; }
.sidebar nav button:hover { background: var(--panel); color: var(--text); }
.sidebar nav button.active { background: var(--accent-soft); color: var(--text); }
.sidebar nav button.active :deep(svg) { color: var(--accent); }
.sidebar nav button.indent { padding-left: 20px; }
.nav-group { color: var(--faint); font-size: 0.72rem; text-transform: uppercase; letter-spacing: 0.06em; margin: 14px 11px 4px; }
.nav-sep { height: 1px; background: var(--line-soft); margin: 12px 8px; }
.new { display: flex; align-items: center; justify-content: center; gap: 8px; margin-top: 16px; background: var(--panel-2); border: 1px solid var(--line); color: var(--text); padding: 10px; border-radius: 8px; cursor: pointer; font-size: 0.88rem; }
.workspace { padding: 28px 36px; max-width: 900px; }

/* Stats */
.stat-row { display: grid; grid-template-columns: repeat(5, 1fr); gap: 12px; margin: 8px 0 24px; }
.stat { background: var(--panel); border: 1px solid var(--line); border-radius: 12px; padding: 16px; }
.stat-n { font-size: 1.7rem; font-weight: 700; letter-spacing: -0.02em; }
.stat-l { color: var(--muted); font-size: 0.8rem; margin-top: 2px; }
.breakdown { border: 1px solid var(--line); border-radius: 12px; overflow: hidden; }
.bd-row { display: flex; align-items: center; gap: 12px; padding: 13px 18px; cursor: pointer; }
.bd-row + .bd-row { border-top: 1px solid var(--line-soft); }
.bd-row:hover { background: var(--panel); }
.bd-plat { font-weight: 550; flex: 1; }
.bd-count { color: var(--muted); font-size: 0.9rem; }
.bd-arrow { color: var(--faint); }

/* Calendrier */
.calendar { display: grid; gap: 10px; }
.day { background: var(--panel); border: 1px solid var(--line); border-left: 3px solid var(--accent); border-radius: 10px; padding: 14px 16px; }
.day-head { font-weight: 650; }
.day-chan { color: var(--accent); font-size: 0.78rem; text-transform: uppercase; letter-spacing: 0.04em; margin: 2px 0 6px; }
.day p { margin: 0; color: var(--muted); font-size: 0.92rem; }

/* Cartes */
.cards { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 14px; }
.content-card { background: var(--panel); border: 1px solid var(--line); border-radius: 12px; padding: 16px; display: flex; flex-direction: column; }
.cc-top { display: flex; align-items: center; justify-content: space-between; margin-bottom: 10px; gap: 8px; }
.tag { background: var(--accent-soft); color: var(--accent); font-size: 0.72rem; font-weight: 600; padding: 3px 8px; border-radius: 6px; white-space: nowrap; }
.cc-meta { color: var(--faint); font-size: 0.78rem; white-space: nowrap; }
.cc-title { font-weight: 600; margin-bottom: 6px; }
.cc-preview { color: var(--muted); font-size: 0.88rem; line-height: 1.5; margin: 0 0 16px; flex: 1; }
.cc-actions { display: flex; gap: 8px; }
.btn-primary { display: inline-flex; align-items: center; gap: 6px; background: var(--accent); color: #fff; border: none; border-radius: 8px; padding: 8px 14px; font-size: 0.85rem; font-weight: 500; cursor: pointer; }
.btn-ghost { display: inline-flex; align-items: center; gap: 6px; background: var(--panel-2); border: 1px solid var(--line); color: var(--text); border-radius: 8px; padding: 8px 12px; font-size: 0.85rem; cursor: pointer; }
.btn-icon { background: transparent; border: none; color: var(--muted); cursor: pointer; padding: 4px; display: inline-flex; }
.btn-icon:hover { color: var(--text); }

/* Clips */
.clips { display: grid; gap: 10px; }
.clip { background: var(--panel); border: 1px solid var(--line); border-radius: 10px; padding: 14px 16px; }
.clip-head { display: flex; align-items: center; gap: 10px; margin-bottom: 6px; }
.clip-ts { font-variant-numeric: tabular-nums; background: var(--accent-soft); color: var(--accent); font-size: 0.78rem; font-weight: 600; padding: 2px 8px; border-radius: 6px; }
.clip-title { font-weight: 600; }
.clip-hook { margin: 0 0 6px; font-style: italic; color: var(--text); }
.clip-why { margin: 0; color: var(--muted); font-size: 0.9rem; }

/* Source */
.summary-card { background: var(--panel); border: 1px solid var(--line); border-radius: 12px; padding: 20px; }
.sum-head { display: flex; align-items: center; gap: 8px; font-weight: 600; font-size: 0.9rem; color: var(--accent); margin-bottom: 8px; }
.summary-card p { margin: 0; line-height: 1.6; }
.key-points { margin: 0; padding-left: 20px; color: var(--muted); line-height: 1.8; }
.accordion { display: flex; align-items: center; gap: 8px; width: 100%; text-align: left; background: transparent; border: none; color: var(--text); padding: 16px 2px; margin-top: 8px; cursor: pointer; font-size: 0.92rem; }
.doc-page { background: #f7f7f4; color: #1c1c1c; border-radius: 10px; padding: 32px 36px; white-space: pre-wrap; line-height: 1.7; font-size: 0.95rem; }
.doc-page.muted { background: var(--panel); color: var(--muted); font-size: 0.88rem; }

/* Drawer */
.drawer-overlay { position: fixed; inset: 0; background: rgba(0, 0, 0, 0.55); display: flex; justify-content: flex-end; z-index: 50; }
.drawer { width: 620px; max-width: 92vw; background: var(--bg); border-left: 1px solid var(--line); height: 100vh; display: flex; flex-direction: column; }
.drawer-head { display: flex; align-items: center; justify-content: space-between; padding: 18px 22px; border-bottom: 1px solid var(--line-soft); }
.drawer-head h3 { margin: 0; font-size: 1.05rem; }
.drawer-actions { display: flex; align-items: center; gap: 10px; }
.export { position: relative; }
.export-menu { position: absolute; right: 0; top: calc(100% + 6px); background: var(--panel); border: 1px solid var(--line); border-radius: 10px; padding: 6px; min-width: 180px; z-index: 5; box-shadow: 0 12px 30px rgba(0,0,0,0.4); }
.export-menu button { display: flex; align-items: center; gap: 9px; width: 100%; text-align: left; background: transparent; border: none; color: var(--text); padding: 9px 10px; border-radius: 7px; font-size: 0.88rem; cursor: pointer; }
.export-menu button:hover:not(:disabled) { background: var(--panel-2); }
.export-menu button:disabled { color: var(--faint); cursor: default; justify-content: space-between; }
.soon { font-size: 0.68rem; background: var(--line); padding: 2px 6px; border-radius: 5px; }
.drawer-body { padding: 24px 22px; overflow-y: auto; flex: 1; }
.mock { background: var(--panel); border: 1px solid var(--line); border-radius: 12px; padding: 18px; }
.avatar { width: 44px; height: 44px; border-radius: 50%; background: linear-gradient(135deg, var(--accent), #9b5bff); flex-shrink: 0; }
.avatar.sm { width: 38px; height: 38px; }
.li-top { display: flex; gap: 12px; align-items: center; margin-bottom: 14px; }
.name { font-weight: 600; font-size: 0.92rem; }
.sub { color: var(--faint); font-size: 0.8rem; }
.post-body { white-space: pre-wrap; line-height: 1.6; margin: 0; }
.li-actions { display: flex; gap: 20px; margin-top: 16px; padding-top: 12px; border-top: 1px solid var(--line-soft); color: var(--muted); font-size: 0.82rem; }
.thread-view { display: flex; flex-direction: column; }
.tweet { display: flex; gap: 12px; background: var(--panel); border: 1px solid var(--line); padding: 14px 16px; }
.tweet:first-child { border-radius: 12px 12px 0 0; }
.tweet:last-child { border-radius: 0 0 12px 12px; }
.tweet + .tweet { border-top: none; }
.tweet-body { flex: 1; }
.handle { color: var(--faint); font-weight: 400; font-size: 0.85rem; }
.tweet p { margin: 4px 0 0; line-height: 1.5; white-space: pre-wrap; }
.slide-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
.slide { background: var(--panel); border: 1px solid var(--line); border-radius: 12px; padding: 18px; font-size: 0.92rem; line-height: 1.45; min-height: 150px; position: relative; }
.slide.cover { background: linear-gradient(150deg, var(--accent), #8b47ff); color: #fff; font-weight: 650; font-size: 1.1rem; display: flex; align-items: center; }
.slide-n { position: absolute; top: 10px; right: 12px; color: var(--faint); font-size: 0.8rem; }
.cta { margin: 14px 0 0; color: var(--muted); font-size: 0.9rem; }

@media (max-width: 720px) {
  .app { grid-template-columns: 1fr; }
  .sidebar { border-right: none; border-bottom: 1px solid var(--line-soft); }
  .workspace { padding: 20px; }
  .stat-row { grid-template-columns: 1fr 1fr; }
  .slide-grid { grid-template-columns: 1fr; }
}
</style>
