# CAOM visitor notifier

This Cloudflare Worker receives privacy-limited visit events from the static site and sends them to WeChat through PushPlus.

## Deploy

```powershell
npx wrangler login
npx wrangler secret put PUSHPLUS_TOKEN --config workers/visitor-notifier/wrangler.jsonc
npx wrangler deploy --config workers/visitor-notifier/wrangler.jsonc
```

For visitors in networks where `workers.dev` is unavailable, deploy the same handler to Cloudflare Pages and attach an external-DNS subdomain:

```powershell
npx wrangler pages project create caom-visitor-gateway --production-branch main
npx wrangler pages deploy workers/visitor-notifier/pages --project-name caom-visitor-gateway --branch main
npx wrangler pages secret put PUSHPLUS_TOKEN --project-name caom-visitor-gateway
```

In the Pages dashboard, attach `notify.caom.online`, then create this record at the existing DNS provider:

```text
CNAME  notify  caom-visitor-gateway.pages.dev
```

The production site posts visit events to `https://notify.caom.online/visit`.

Set the GitHub Actions repository variable `VISITOR_NOTIFY_ENDPOINT` to the deployed `/visit` URL, for example:

```text
https://caom-visitor-notifier.example.workers.dev/visit
```

The site build exposes it as `PUBLIC_VISITOR_NOTIFY_ENDPOINT`. The token remains an encrypted Worker secret and is never sent to a browser.
