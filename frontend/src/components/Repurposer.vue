<script setup>
import { ref, computed } from "vue";

const API = import.meta.env.PUBLIC_API_URL || "http://localhost:8787";

const url = ref("");
const loading = ref(false);
const error = ref("");
const result = ref(null);
const activeTab = ref("blog_article");
const copied = ref("");

const TABS = [
  { key: "blog_article", label: "Article de blog" },
  { key: "x_thread", label: "Thread X" },
  { key: "linkedin_post", label: "LinkedIn" },
  { key: "newsletter", label: "Newsletter" },
  { key: "instagram_captions", label: "Instagram" },
  { key: "key_moments", label: "Clips" },
  { key: "seo_titles", label: "Titres SEO" },
];

const activeContent = computed(() => result.value?.formats?.[activeTab.value]);

async function submit() {
  error.value = "";
  result.value = null;
  if (!url.value.trim()) return;
  loading.value = true;
  try {
    const res = await fetch(`${API}/api/process`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url: url.value.trim() }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Erreur inconnue");
    result.value = data;
    activeTab.value = "blog_article";
  } catch (e) {
    error.value = e.message;
  } finally {
    loading.value = false;
  }
}

function asText(content) {
  if (Array.isArray(content)) {
    if (content.length && typeof content[0] === "object") {
      return content.map((m) => `• ${m.title} — ${m.why}`).join("\n\n");
    }
    return content.join("\n\n");
  }
  return content ?? "";
}

async function copy() {
  await navigator.clipboard.writeText(asText(activeContent.value));
  copied.value = activeTab.value;
  setTimeout(() => (copied.value = ""), 1500);
}
</script>

<template>
  <div class="card form">
    <input
      v-model="url"
      type="url"
      placeholder="https://www.youtube.com/watch?v=..."
      @keyup.enter="submit"
    />
    <button :disabled="loading" @click="submit">
      {{ loading ? "Traitement…" : "Générer" }}
    </button>
  </div>

  <p v-if="error" class="error">⚠ {{ error }}</p>

  <div v-if="loading" class="card hint">
    Récupération du transcript puis génération des formats… (10-40 s selon la vidéo)
  </div>

  <div v-if="result" class="result">
    <div class="meta">
      <strong>{{ result.title }}</strong>
      <span>
        source : {{ result.transcript_source }} ·
        {{ result.transcript_chars.toLocaleString() }} caractères ·
        {{ result.quota_remaining }} restant(s) ce mois
      </span>
    </div>

    <div class="tabs">
      <button
        v-for="t in TABS"
        :key="t.key"
        :class="{ active: activeTab === t.key }"
        @click="activeTab = t.key"
      >
        {{ t.label }}
      </button>
    </div>

    <div class="card output">
      <button class="copy" @click="copy">
        {{ copied === activeTab ? "✓ Copié" : "Copier" }}
      </button>
      <pre>{{ asText(activeContent) }}</pre>
    </div>
  </div>
</template>

<style scoped>
.card {
  background: var(--card);
  border: 1px solid var(--line);
  border-radius: 14px;
  padding: 16px;
}
.form { display: flex; gap: 10px; }
input {
  flex: 1;
  background: #0f1120;
  border: 1px solid var(--line);
  border-radius: 10px;
  padding: 14px 16px;
  color: var(--text);
  font-size: 1rem;
}
input:focus { outline: none; border-color: var(--accent); }
button {
  background: var(--accent);
  color: white;
  border: none;
  border-radius: 10px;
  padding: 14px 22px;
  font-weight: 600;
  cursor: pointer;
  font-size: 1rem;
}
button:disabled { opacity: 0.6; cursor: default; }
.error { color: #ff8080; text-align: center; margin-top: 16px; }
.hint { margin-top: 16px; color: var(--muted); text-align: center; }
.result { margin-top: 24px; }
.meta { display: flex; flex-direction: column; gap: 4px; margin-bottom: 14px; }
.meta span { color: var(--muted); font-size: 0.85rem; }
.tabs { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 14px; }
.tabs button {
  background: transparent;
  border: 1px solid var(--line);
  color: var(--muted);
  padding: 8px 14px;
  font-size: 0.9rem;
  font-weight: 500;
}
.tabs button.active { background: var(--accent); color: white; border-color: var(--accent); }
.output { position: relative; }
.copy {
  position: absolute;
  top: 12px;
  right: 12px;
  background: var(--line);
  color: var(--text);
  padding: 6px 12px;
  font-size: 0.8rem;
}
pre {
  white-space: pre-wrap;
  word-break: break-word;
  margin: 0;
  padding-top: 8px;
  font-family: inherit;
  line-height: 1.6;
}
</style>
