import { createApp } from "vue";
import { createPinia } from "pinia";
import router from "./router";

// Vuetify
import "vuetify/styles";
import { createVuetify } from "vuetify";
import * as components from "vuetify/components";
import * as directives from "vuetify/directives";
import "@mdi/font/css/materialdesignicons.css";

import App from "./App.vue";

const vuetify = createVuetify({
  components,
  directives,
  theme: {
    defaultTheme: "light",
    themes: {
      light: {
        colors: {
          primary: "#f59e0b",
          secondary: "#2e1a00",
          background: "#fdf6e3",
          surface: "#FFFFFF",
          "surface-light": "#F3F4F6",
          error: "#EF4444",
          success: "#10B981",
          warning: "#F59E0B",
          info: "#3B82F6",
        },
      },
    },
  },
});

const app = createApp(App);
app.use(createPinia());
app.use(router);
app.use(vuetify);
app.mount("#app");
