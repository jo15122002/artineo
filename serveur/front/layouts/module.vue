<template>
    <div class="module-container">
      <slot/>
    </div>
  </template>
  
  <script setup>
  definePageMeta({ layout: false })
  </script>
  
  <style>
  html, body, #__nuxt, .module-container {
    margin: 0; padding: 0; height: 100%;
    width: 100%;
    overflow: hidden;
  }
  </style>
  