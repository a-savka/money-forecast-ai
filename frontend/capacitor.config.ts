import type { CapacitorConfig } from '@capacitor/cli'

const config: CapacitorConfig = {
  appId: 'ru.moneyforecast.app',
  appName: 'MoneyForecast AI',
  webDir: 'dist',
  server: {
    // API в учебном стенде работает по HTTP в локальной сети,
    // поэтому WebView открывается по http://localhost и разрешает cleartext-трафик
    androidScheme: 'http',
    cleartext: true,
  },
}

export default config
