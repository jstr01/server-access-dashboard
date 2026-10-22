import './assets/tailwind.css'
import { createApp } from 'vue'
import App from './App.vue'
import router from './router'

import CountryFlag from 'vue-country-flag-next'
import { Chart as ChartJS, registerables } from 'chart.js'

ChartJS.register(...registerables)

const app = createApp(App)

app.use(router)

app.component('country-flag', CountryFlag)

app.mount('#app')
