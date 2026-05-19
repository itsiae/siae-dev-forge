<!-- SAFE: Vue template interpolation {{}} auto-escape XSS. -->
<template>
  <div>{{ userInput }}</div>
  <div v-text="userInput"></div>
</template>

<script setup lang="ts">
import { ref } from "vue";
const userInput = ref<string>("user-text");
</script>
