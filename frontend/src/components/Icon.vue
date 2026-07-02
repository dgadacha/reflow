<script setup>
// Icônes vectorielles cohérentes (jeu Lucide) — aucun emoji.
import { computed } from "vue";

const props = defineProps({
  name: { type: String, required: true },
  size: { type: [Number, String], default: 18 },
});

const ICONS = {
  dashboard:
    '<rect width="7" height="9" x="3" y="3" rx="1"/><rect width="7" height="5" x="14" y="3" rx="1"/><rect width="7" height="9" x="14" y="12" rx="1"/><rect width="7" height="5" x="3" y="16" rx="1"/>',
  calendar:
    '<path d="M8 2v4M16 2v4"/><rect width="18" height="18" x="3" y="4" rx="2"/><path d="M3 10h18"/>',
  message:
    '<path d="M7.9 20A9 9 0 1 0 4 16.1L2 22z"/>',
  mail:
    '<rect width="20" height="16" x="2" y="4" rx="2"/><path d="m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7"/>',
  file:
    '<path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z"/><path d="M14 2v4a2 2 0 0 0 2 2h4"/>',
  "file-text":
    '<path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z"/><path d="M14 2v4a2 2 0 0 0 2 2h4"/><path d="M10 9H8M16 13H8M16 17H8"/>',
  film:
    '<rect width="18" height="18" x="3" y="3" rx="2"/><path d="M7 3v18M3 7.5h4M3 12h18M3 16.5h4M17 3v18M17 7.5h4M17 16.5h4"/>',
  copy:
    '<rect width="14" height="14" x="8" y="8" rx="2"/><path d="M4 16c-1.1 0-2-.9-2-2V4c0-1.1.9-2 2-2h10c1.1 0 2 .9 2 2"/>',
  download:
    '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><path d="m7 10 5 5 5-5"/><path d="M12 15V3"/>',
  check: '<path d="M20 6 9 17l-5-5"/>',
  "chevron-right": '<path d="m9 18 6-6-6-6"/>',
  "chevron-down": '<path d="m6 9 6 6 6-6"/>',
  open: '<path d="M15 3h6v6"/><path d="M10 14 21 3"/><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/>',
  close: '<path d="M18 6 6 18M6 6l12 12"/>',
  plus: '<path d="M5 12h14M12 5v14"/>',
  sparkles:
    '<path d="M9.9 15.5A2 2 0 0 0 8.5 14L2.4 12.5a.5.5 0 0 1 0-1L8.5 10A2 2 0 0 0 9.9 8.5l1.6-6.1a.5.5 0 0 1 1 0L14 8.5A2 2 0 0 0 15.5 10l6.1 1.5a.5.5 0 0 1 0 1L15.5 14a2 2 0 0 0-1.4 1.5l-1.6 6.1a.5.5 0 0 1-1 0z"/>',
  layers:
    '<path d="m12.8 2.5 8.9 4.4a.6.6 0 0 1 0 1.1l-8.9 4.4a1.8 1.8 0 0 1-1.6 0L2.3 8a.6.6 0 0 1 0-1.1l8.9-4.4a1.8 1.8 0 0 1 1.6 0Z"/><path d="m2.3 12 8.9 4.4a1.8 1.8 0 0 0 1.6 0L21.7 12"/><path d="m2.3 16.5 8.9 4.4a1.8 1.8 0 0 0 1.6 0l8.9-4.4"/>',
  send:
    '<path d="M14.5 21.7a.5.5 0 0 0 .9 0l6.5-19a.5.5 0 0 0-.63-.64l-19 6.5a.5.5 0 0 0 0 .94l7.9 3.18a2 2 0 0 1 1.1 1.1z"/><path d="m21.85 2.15-10.94 10.94"/>',
};

const paths = computed(() => ICONS[props.name] || "");
</script>

<template>
  <svg
    :width="size"
    :height="size"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    stroke-width="2"
    stroke-linecap="round"
    stroke-linejoin="round"
    v-html="paths"
  ></svg>
</template>
