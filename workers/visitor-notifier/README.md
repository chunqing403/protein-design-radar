# CAOM visitor notifier

This Cloudflare Worker receives privacy-limited visit events from the static site and sends them to WeChat through PushPlus.

## Deploy

```powershell
npx wrangler login
npx wrangler secret put PUSHPLUS_TOKEN --config workers/visitor-notifier/wrangler.jsonc
npx wrangler deploy --config workers/visitor-notifier/wrangler.jsonc
```

Set the GitHub Actions repository variable `VISITOR_NOTIFY_ENDPOINT` to the deployed `/visit` URL, for example:

```text
https://caom-visitor-notifier.example.workers.dev/visit
```

The site build exposes it as `PUBLIC_VISITOR_NOTIFY_ENDPOINT`. The token remains an encrypted Worker secret and is never sent to a browser.
