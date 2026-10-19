import assert from "node:assert/strict";
import { afterEach, beforeEach, test } from "node:test";
import worker from "../workers/visitor-notifier/src/index.mjs";

const originalFetch = globalThis.fetch;
const originalCaches = globalThis.caches;

function visitRequest(origin = "https://www.caom.online", ip = "203.0.113.8") {
  return new Request("https://worker.example/visit", {
    method: "POST",
    headers: {
      Origin: origin,
      "Content-Type": "application/json",
      "CF-Connecting-IP": ip,
      "User-Agent": "Mozilla/5.0 (iPhone; Mobile)",
    },
    body: JSON.stringify({
      path: "/papers.html",
      referrer: "https://www.google.com/search?q=protein",
      language: "zh-CN",
      viewport: "390x844",
    }),
  });
}

beforeEach(() => {
  const entries = new Map();
  globalThis.caches = {
    default: {
      async match(key) {
        return entries.get(key.url);
      },
      async put(key, value) {
        entries.set(key.url, value);
      },
    },
  };
});

afterEach(() => {
  globalThis.fetch = originalFetch;
  globalThis.caches = originalCaches;
});

test("rejects requests from unapproved origins", async () => {
  const response = await worker.fetch(visitRequest("https://attacker.example"), { PUSHPLUS_TOKEN: "secret" });
  assert.equal(response.status, 403);
  assert.deepEqual(await response.json(), { ok: false, error: "forbidden" });
});

test("sends a privacy-limited PushPlus message", async () => {
  let pushed;
  globalThis.fetch = async (_url, init) => {
    pushed = JSON.parse(init.body);
    return Response.json({ code: 200, msg: "success" });
  };

  const response = await worker.fetch(visitRequest(), {
    PUSHPLUS_TOKEN: "secret-token",
    NOTIFY_COOLDOWN_SECONDS: "1800",
  });

  assert.equal(response.status, 202);
  assert.equal(pushed.token, "secret-token");
  assert.match(pushed.content, /访问页面：https:\/\/www\.caom\.online\/papers\.html/);
  assert.match(pushed.content, /访问来源：https:\/\/www\.google\.com/);
  assert.doesNotMatch(pushed.content, /203\.0\.113\.8/);
});

test("deduplicates repeated visits from the same browser and address", async () => {
  let pushCount = 0;
  globalThis.fetch = async () => {
    pushCount += 1;
    return Response.json({ code: 200 });
  };

  const env = { PUSHPLUS_TOKEN: "secret-token" };
  const first = await worker.fetch(visitRequest(), env);
  const second = await worker.fetch(visitRequest(), env);

  assert.equal(first.status, 202);
  assert.deepEqual(await second.json(), { ok: true, deduplicated: true });
  assert.equal(pushCount, 1);
});

test("reports whether the Worker has been configured", async () => {
  const response = await worker.fetch(new Request("https://worker.example/health"), {});
  assert.equal(response.status, 200);
  assert.deepEqual(await response.json(), { ok: true, configured: false });
});
