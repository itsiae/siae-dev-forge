<!-- Vue v-html su input untrusted (CWE-79). Stack frontend SIAE: Vue.js. -->
<template>
  <!-- VULNERABLE: v-html bypassa template auto-escape -->
  <div v-html="userInput"></div>
  <div v-html="rawHtml"></div>
</template>

<script setup lang="ts">
import { ref } from "vue";
const userInput = ref<string>("user-provided-html-here");
const rawHtml = ref<string>("<script>alert(1)</script>");
</script>
