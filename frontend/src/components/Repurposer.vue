<script setup>
import { ref, computed, onUnmounted } from "vue";

const API = import.meta.env.PUBLIC_API_URL || "http://localhost:8787";

const url = ref("");
const persona = ref("Entrepreneur");
const voice = ref("Professionnelle");
const loading = ref(false);
const error = ref("");
const result = ref(null);
const activeTab = ref("weekly_calendar");
const copied = ref(false);

const PERSONAS = [
  "Entrepreneur", "Créateur", "Coach", "SaaS",
  "Agence", "Immobilier", "Finance", "E-commerce",
];
const VOICES = ["Professionnelle", "Directe", "Éducative", "Premium", "Décontractée"];

const TABS = [
  { key: "weekly_calendar", label: "Calendrier", group: "Plan" },
  { key: "linkedin_post", label: "Post LinkedIn", group: "Réseaux" },
  { key: "linkedin_carousel", label: "Carrousel LinkedIn", group: "Réseaux" },
  { key: "x_thread", label: "Thread X", group: "Réseaux" },
  { key: "instagram_carousel", label: "Carrousel Instagram", group: "Réseaux" },
  { key: "newsletter", label: "Newsletter", group: "Écrit" },
  { key: "blog_article", label: "Article de blog", group: "Écrit" },
  { key: "seo_titles", label: "Titres SEO", group: "Écrit" },
  { key: "key_moments", label: "Idées de clips", group: "Vidéo" },
  { key: "transcript", label: "Transcription", group: "Source" },
];

const GROUPS = ["Plan", "Réseaux", "Écrit", "Vidéo", "Source"];
const tabsByGroup = (g) => TABS.filter((t) => t.group === g);
const activeLabel = computed(() => TABS.find((t) => t.key === activeTab.value)?.label);

const fmt = computed(() => result.value?.formats ?? {});
const activeContent = computed(() =>
  activeTab.value === "transcript" ? result.value?.transcript : fmt.value[activeTab.value],
);

// --- Progression simulée pendant l'appel (perception premium) ---------------
const STEPS = [
  "Analyse du transcript",
  "Extraction des thèmes clés",
  "Construction du calendrier éditorial",
  "Génération des posts & carrousels",
  "Thread, newsletter & clips",
  "Finalisation",
];
const stepIndex = ref(0);
let stepTimer = null;
function startSteps() {
  stepIndex.value = 0;
  stepTimer = setInterval(() => {
    if (stepIndex.value < STEPS.length - 1) stepIndex.value++;
  }, 1100);
}
function stopSteps() {
  clearInterval(stepTimer);
  stepTimer = null;
}
onUnmounted(stopSteps);

async function submit() {
  error.value = "";
  if (!url.value.trim()) return;
  loading.value = true;
  startSteps();
  try {
    const res = await fetch(`${API}/api/process`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        url: url.value.trim(),
        persona: persona.value,
        voice: voice.value,
      }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Erreur inconnue");
    result.value = data;
    activeTab.value = "weekly_calendar";
  } catch (e) {
    error.value = e.message;
  } finally {
    stopSteps();
    loading.value = false;
  }
}

function reset() {
  result.value = null;
  error.value = "";
}

// --- Helpers d'affichage / copie --------------------------------------------
function subjectOf(text) {
  return (text || "").split("\n")[0];
}
function bodyOf(text) {
  const parts = (text || "").split("\n");
  return parts.slice(1).join("\n").trim();
}

function asText(content) {
  if (content == null) return "";
  if (typeof content === "string") return content;
  if (Array.isArray(content)) {
    return content
      .map((c) => {
        if (typeof c !== "object") return c;
        if ("day" in c) return `${c.day} · ${c.channel}\n${c.action}`;
        if ("title" in c && "why" in c) return `• ${c.title} — ${c.why}`;
        return Object.values(c).join(" — ");
      })
      .join("\n\n");
  }
  if (Array.isArray(content.slides)) {
    const parts = [];
    if (content.title) parts.push(content.title);
    if (content.cover) parts.push(`[Couverture] ${content.cover}`);
    content.slides.forEach((s, i) => parts.push(`${i + 1}. ${s}`));
    if (content.cta) parts.push(content.cta);
    if (content.caption) parts.push(`\n${content.caption}`);
    return parts.join("\n\n");
  }
  return JSON.stringify(content, null, 2);
}

async function copy() {
  await navigator.clipboard.writeText(asText(activeContent.value));
  copied.value = true;
  setTimeout(() => (copied.value = false), 1500);
}
</script>

<template>
  <!-- ÉTAT 1 — accueil / saisie -->
  <div v-if="!result && !loading" class="landing">
    <div class="intro">
      <h1>Une vidéo entre.<br />Une <span>semaine</span> de contenu sort.</h1>
      <p>
        Colle un lien YouTube. Repars avec un calendrier éditorial et tous tes
        contenus prêts à publier — LinkedIn, X, newsletter, carrousels, article, clips.
      </p>
    </div>

    <div class="composer">
      <div class="composer-row">
        <input
          v-model="url"
          type="url"
          placeholder="Colle un lien YouTube…"
          @keyup.enter="submit"
        />
        <button class="primary" @click="submit">Générer la semaine</button>
      </div>
      <div class="composer-opts">
        <label>
          Profil
          <select v-model="persona">
            <option v-for="p in PERSONAS" :key="p" :value="p">{{ p }}</option>
          </select>
        </label>
        <label>
          Voix
          <select v-model="voice">
            <option v-for="v in VOICES" :key="v" :value="v">{{ v }}</option>
          </select>
        </label>
      </div>
      <p v-if="error" class="error">⚠ {{ error }}</p>
    </div>

    <div class="pricing">
      <div class="plan">
        <div class="plan-name">Gratuit</div>
        <div class="price">0$<span>/mois</span></div>
        <ul>
          <li>3 vidéos offertes</li>
          <li>Tous les formats inclus</li>
          <li>Sans carte bancaire</li>
        </ul>
      </div>
      <div class="plan featured">
        <div class="plan-name">Reflow Pro</div>
        <div class="price">19$<span>/mois</span></div>
        <ul>
          <li>30 vidéos par mois</li>
          <li>Historique des générations</li>
          <li>Export Markdown</li>
          <li>Annulation à tout moment</li>
        </ul>
      </div>
    </div>
  </div>

  <!-- ÉTAT 2 — progression -->
  <div v-else-if="loading" class="progress-wrap">
    <div class="progress">
      <div class="progress-title">Génération en cours…</div>
      <ul>
        <li
          v-for="(s, i) in STEPS"
          :key="s"
          :class="{ done: i < stepIndex, active: i === stepIndex }"
        >
          <span class="tick">{{ i < stepIndex ? "✓" : i === stepIndex ? "" : "" }}</span>
          {{ s }}
        </li>
      </ul>
    </div>
  </div>

  <!-- ÉTAT 3 — workspace produit -->
  <div v-else class="app">
    <aside class="sidebar">
      <div class="side-title" :title="result.title">{{ result.title }}</div>
      <div class="side-meta">
        {{ result.transcript_source }} ·
        {{ result.quota_remaining }} restant(s)
        <template v-if="result.from_cache"> · ⚡</template>
      </div>
      <nav>
        <template v-for="g in GROUPS" :key="g">
          <div class="side-group">{{ g }}</div>
          <button
            v-for="t in tabsByGroup(g)"
            :key="t.key"
            :class="{ active: activeTab === t.key }"
            @click="activeTab = t.key"
          >
            {{ t.label }}
          </button>
        </template>
      </nav>
      <button class="new" @click="reset">＋ Nouvelle vidéo</button>
    </aside>

    <section class="workspace">
      <header class="ws-head">
        <h2>{{ activeLabel }}</h2>
        <button class="copy" @click="copy">{{ copied ? "✓ Copié" : "Copier" }}</button>
      </header>

      <div class="ws-body">
        <!-- Calendrier -->
        <div v-if="activeTab === 'weekly_calendar'" class="calendar">
          <div v-for="(d, i) in fmt.weekly_calendar" :key="i" class="day">
            <div class="day-head">{{ d.day }}</div>
            <div class="day-chan">{{ d.channel }}</div>
            <p>{{ d.action }}</p>
          </div>
        </div>

        <!-- Post LinkedIn -->
        <div v-else-if="activeTab === 'linkedin_post'" class="mock li">
          <div class="li-top">
            <div class="avatar"></div>
            <div>
              <div class="name">Ton nom</div>
              <div class="sub">Ton titre · à l'instant</div>
            </div>
          </div>
          <p class="post-body">{{ fmt.linkedin_post }}</p>
          <div class="li-actions"><span>👍 J'aime</span><span>💬 Commenter</span><span>↗ Partager</span></div>
        </div>

        <!-- Thread X -->
        <div v-else-if="activeTab === 'x_thread'" class="thread">
          <div v-for="(t, i) in fmt.x_thread" :key="i" class="tweet">
            <div class="avatar sm"></div>
            <div class="tweet-body">
              <div class="name">
                Ton nom <span class="handle">@toi · {{ i + 1 }}/{{ fmt.x_thread.length }}</span>
              </div>
              <p>{{ t }}</p>
            </div>
          </div>
        </div>

        <!-- Carrousel LinkedIn -->
        <div v-else-if="activeTab === 'linkedin_carousel'">
          <div class="carousel">
            <div class="slide cover">{{ fmt.linkedin_carousel.title }}</div>
            <div v-for="(s, i) in fmt.linkedin_carousel.slides" :key="i" class="slide">
              <span class="slide-n">{{ i + 1 }}</span>{{ s }}
            </div>
          </div>
          <p class="cta">{{ fmt.linkedin_carousel.cta }}</p>
        </div>

        <!-- Carrousel Instagram -->
        <div v-else-if="activeTab === 'instagram_carousel'">
          <div class="carousel">
            <div class="slide cover ig">{{ fmt.instagram_carousel.cover }}</div>
            <div v-for="(s, i) in fmt.instagram_carousel.slides" :key="i" class="slide ig">
              <span class="slide-n">{{ i + 1 }}</span>{{ s }}
            </div>
          </div>
          <p class="caption">{{ fmt.instagram_carousel.caption }}</p>
        </div>

        <!-- Newsletter -->
        <div v-else-if="activeTab === 'newsletter'" class="mock email">
          <div class="email-subject">
            <span>Objet</span>{{ subjectOf(fmt.newsletter) }}
          </div>
          <div class="email-body">{{ bodyOf(fmt.newsletter) }}</div>
        </div>

        <!-- Article de blog -->
        <div v-else-if="activeTab === 'blog_article'" class="document">
          <div class="doc-page">{{ fmt.blog_article }}</div>
        </div>

        <!-- Titres SEO -->
        <div v-else-if="activeTab === 'seo_titles'" class="titles">
          <div v-for="(t, i) in fmt.seo_titles" :key="i" class="title-row">
            <span class="title-n">{{ i + 1 }}</span>{{ t }}
          </div>
        </div>

        <!-- Idées de clips -->
        <div v-else-if="activeTab === 'key_moments'" class="clips">
          <div v-for="(m, i) in fmt.key_moments" :key="i" class="clip">
            <div class="clip-title">{{ m.title }}</div>
            <p>{{ m.why }}</p>
          </div>
        </div>

        <!-- Transcription -->
        <div v-else-if="activeTab === 'transcript'" class="document">
          <div class="doc-page muted">{{ result.transcript }}</div>
        </div>
      </div>
    </section>
  </div>
</template>

<style scoped>
/* ---------- ÉTAT 1 : accueil ---------- */
.landing { max-width: 760px; margin: 0 auto; padding: 72px 24px 64px; }
.intro { text-align: center; margin-bottom: 40px; }
.intro h1 { font-size: 2.5rem; line-height: 1.12; letter-spacing: -0.02em; margin: 0 0 16px; }
.intro h1 span { color: var(--accent); }
.intro p { color: var(--muted); font-size: 1.1rem; max-width: 560px; margin: 0 auto; }

.composer {
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 14px;
  padding: 16px;
}
.composer-row { display: flex; gap: 10px; }
input {
  flex: 1;
  background: var(--bg);
  border: 1px solid var(--line);
  border-radius: 9px;
  padding: 13px 14px;
  color: var(--text);
  font-size: 0.98rem;
}
input:focus { outline: none; border-color: var(--accent); }
.primary {
  background: var(--accent);
  color: #fff;
  border: none;
  border-radius: 9px;
  padding: 0 20px;
  font-weight: 600;
  cursor: pointer;
  white-space: nowrap;
}
.composer-opts { display: flex; gap: 18px; margin-top: 12px; }
.composer-opts label {
  display: flex; align-items: center; gap: 8px;
  color: var(--muted); font-size: 0.88rem;
}
select {
  background: var(--bg);
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 7px 9px;
  color: var(--text);
  font-size: 0.88rem;
}
.error { color: #ff7a7a; margin: 12px 0 0; font-size: 0.9rem; }

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

/* ---------- ÉTAT 2 : progression ---------- */
.progress-wrap { display: flex; justify-content: center; padding: 120px 24px; }
.progress {
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 14px;
  padding: 28px 32px;
  min-width: 340px;
}
.progress-title { font-weight: 600; margin-bottom: 18px; }
.progress ul { list-style: none; padding: 0; margin: 0; }
.progress li {
  display: flex; align-items: center; gap: 12px;
  padding: 9px 0; color: var(--faint); font-size: 0.95rem;
}
.progress li.done { color: var(--text); }
.progress li.active { color: var(--text); }
.tick {
  width: 18px; height: 18px; border-radius: 50%;
  border: 1px solid var(--line); display: inline-flex;
  align-items: center; justify-content: center; font-size: 0.7rem;
  color: var(--ok); flex-shrink: 0;
}
.progress li.done .tick { border-color: var(--ok); }
.progress li.active .tick {
  border-color: var(--accent);
  border-top-color: transparent;
  animation: spin 0.7s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

/* ---------- ÉTAT 3 : workspace ---------- */
.app { display: grid; grid-template-columns: 248px 1fr; min-height: calc(100vh - 56px); }
.sidebar {
  border-right: 1px solid var(--line-soft);
  padding: 20px 14px;
  display: flex; flex-direction: column;
}
.side-title {
  font-weight: 600; font-size: 0.95rem; line-height: 1.3;
  overflow: hidden; text-overflow: ellipsis; display: -webkit-box;
  -webkit-line-clamp: 2; -webkit-box-orient: vertical;
}
.side-meta { color: var(--faint); font-size: 0.78rem; margin: 6px 0 18px; }
.sidebar nav { flex: 1; }
.side-group {
  color: var(--faint); font-size: 0.72rem; text-transform: uppercase;
  letter-spacing: 0.06em; margin: 16px 8px 6px;
}
.sidebar nav button {
  display: block; width: 100%; text-align: left;
  background: transparent; border: none; color: var(--muted);
  padding: 8px 10px; border-radius: 7px; font-size: 0.9rem; cursor: pointer;
}
.sidebar nav button:hover { background: var(--panel); color: var(--text); }
.sidebar nav button.active { background: var(--accent-soft); color: var(--text); }
.new {
  margin-top: 16px; background: var(--panel-2); border: 1px solid var(--line);
  color: var(--text); padding: 10px; border-radius: 8px; cursor: pointer; font-size: 0.88rem;
}

.workspace { padding: 24px 32px; max-width: 820px; }
.ws-head {
  display: flex; align-items: center; justify-content: space-between;
  margin-bottom: 20px;
}
.ws-head h2 { font-size: 1.25rem; margin: 0; letter-spacing: -0.01em; }
.copy {
  background: var(--panel-2); border: 1px solid var(--line); color: var(--text);
  padding: 7px 14px; border-radius: 8px; font-size: 0.85rem; cursor: pointer;
}

/* Calendrier */
.calendar { display: grid; gap: 10px; }
.day {
  background: var(--panel); border: 1px solid var(--line);
  border-left: 3px solid var(--accent); border-radius: 10px; padding: 14px 16px;
}
.day-head { font-weight: 650; }
.day-chan { color: var(--accent); font-size: 0.78rem; text-transform: uppercase; letter-spacing: 0.04em; margin: 2px 0 6px; }
.day p { margin: 0; color: var(--muted); font-size: 0.92rem; }

/* Mockups réseaux */
.mock { background: var(--panel); border: 1px solid var(--line); border-radius: 12px; padding: 18px; }
.avatar { width: 44px; height: 44px; border-radius: 50%; background: linear-gradient(135deg, var(--accent), #9b5bff); flex-shrink: 0; }
.avatar.sm { width: 38px; height: 38px; }
.li-top { display: flex; gap: 12px; align-items: center; margin-bottom: 14px; }
.name { font-weight: 600; font-size: 0.92rem; }
.sub { color: var(--faint); font-size: 0.8rem; }
.post-body { white-space: pre-wrap; line-height: 1.6; margin: 0; }
.li-actions { display: flex; gap: 20px; margin-top: 16px; padding-top: 12px; border-top: 1px solid var(--line-soft); color: var(--muted); font-size: 0.82rem; }

.thread { display: flex; flex-direction: column; gap: 2px; }
.tweet { display: flex; gap: 12px; background: var(--panel); border: 1px solid var(--line); padding: 14px 16px; }
.tweet:first-child { border-radius: 12px 12px 0 0; }
.tweet:last-child { border-radius: 0 0 12px 12px; }
.tweet + .tweet { border-top: none; }
.tweet-body { flex: 1; }
.handle { color: var(--faint); font-weight: 400; font-size: 0.85rem; }
.tweet p { margin: 4px 0 0; line-height: 1.5; white-space: pre-wrap; }

/* Carrousels */
.carousel { display: flex; gap: 12px; overflow-x: auto; padding-bottom: 12px; }
.slide {
  flex: 0 0 220px; height: 220px; background: var(--panel); border: 1px solid var(--line);
  border-radius: 12px; padding: 18px; font-size: 0.95rem; line-height: 1.4;
  overflow: auto; position: relative;
}
.slide.cover { background: linear-gradient(150deg, var(--accent), #8b47ff); color: #fff; font-weight: 650; font-size: 1.15rem; display: flex; align-items: center; }
.slide.ig { flex-basis: 200px; height: 250px; }
.slide.cover.ig { aspect-ratio: 4/5; }
.slide-n { position: absolute; top: 10px; right: 12px; color: var(--faint); font-size: 0.8rem; }
.cta, .caption { margin: 8px 0 0; color: var(--muted); font-size: 0.9rem; }

/* Email */
.email { padding: 0; overflow: hidden; }
.email-subject {
  padding: 16px 18px; border-bottom: 1px solid var(--line);
  font-weight: 600; display: flex; gap: 10px; align-items: baseline;
}
.email-subject span { color: var(--faint); font-size: 0.72rem; text-transform: uppercase; font-weight: 500; }
.email-body { padding: 18px; white-space: pre-wrap; line-height: 1.65; }

/* Document (article + transcript) */
.document { }
.doc-page {
  background: #f7f7f4; color: #1c1c1c; border-radius: 10px;
  padding: 32px 36px; white-space: pre-wrap; line-height: 1.7; font-size: 0.95rem;
}
.doc-page.muted { background: var(--panel); color: var(--muted); font-size: 0.88rem; line-height: 1.7; }

/* Titres SEO */
.titles { display: flex; flex-direction: column; gap: 8px; }
.title-row {
  background: var(--panel); border: 1px solid var(--line); border-radius: 9px;
  padding: 13px 16px; display: flex; gap: 12px; align-items: baseline;
}
.title-n { color: var(--accent); font-weight: 600; font-size: 0.85rem; }

/* Clips */
.clips { display: grid; gap: 10px; }
.clip { background: var(--panel); border: 1px solid var(--line); border-radius: 10px; padding: 14px 16px; }
.clip-title { font-weight: 600; margin-bottom: 4px; }
.clip p { margin: 0; color: var(--muted); font-size: 0.9rem; }

@media (max-width: 720px) {
  .app { grid-template-columns: 1fr; }
  .sidebar { border-right: none; border-bottom: 1px solid var(--line-soft); }
  .workspace { padding: 20px; }
}
</style>
