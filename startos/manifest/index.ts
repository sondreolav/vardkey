import { setupManifest } from '@start9labs/start-sdk'
import { long, short } from './i18n'

export const manifest = setupManifest({
  id: 'vardkey',
  title: 'VardKey',
  license: 'GPL-3.0-only',
  // Both point at the public GitHub mirror, not at the self-hosted Gitea
  // instance that development happens on: these two links are shown in the
  // StartOS UI, and the mirror is the copy that is meant to take that traffic.
  packageRepo: 'https://github.com/sondreolav/vardkey',
  upstreamRepo: 'https://github.com/sondreolav/vardkey',
  marketingUrl: 'https://sondreolav.com/vardkey',
  donationUrl: 'https://sondreolav.com/donations',
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
