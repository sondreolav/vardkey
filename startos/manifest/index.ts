import { setupManifest } from '@start9labs/start-sdk'
import { long, short } from './i18n'

export const manifest = setupManifest({
  id: 'vardkey',
  title: 'VardKey',
  license: 'GPL-3.0-only',
  packageRepo: 'https://gitea.sondreolav.com/ai-bot/helsesjekk',
  upstreamRepo: 'https://gitea.sondreolav.com/ai-bot/helsesjekk',
  marketingUrl: 'https://sondreolav.com/vardkey',
  donationUrl: null,
  description: { short, long },
  volumes: ['main'],
  images: {
    main: {
      // The application is our own and publishes no image, so the package builds
      // it from the repository root with the Dockerfile in this directory.
      source: { dockerBuild: {} },
      arch: ['x86_64', 'aarch64'],
    },
  },
})
