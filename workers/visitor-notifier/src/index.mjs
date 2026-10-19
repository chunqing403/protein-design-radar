const DEFAULT_ORIGINS = ["https://www.caom.online", "https://caom.online"];
const DEFAULT_COOLDOWN_SECONDS = 1800;
const MAX_BODY_BYTES = 2048;

function json(body, status, origin = "") {
  const headers = {
    "Content-Type": "application/json; charset=utf-8",
    "Cache-Control": "no-store",
  };
  if (origin) {
    headers["Access-Control-Allow-Origin"] = origin;
    headers.Vary = "Origin";
  }
  return new Response(JSON.stringify(body), { status, headers });
}

export function allowedOrigins(env) {
  const configured = env.ALLOWED_ORIGINS?.split(",")
    .map((value) => value.trim())
    .filter(Boolean);
  return new Set(configured?.length ? configured : DEFAULT_ORIGINS);
}

function safePath(value) {
  if (typeof value !== "string" || !value.startsWith("/")) return "/";
  return value.slice(0, 180).replace(/[\r\n]/g, "");
}

function safeReferrer(value) {
  if (typeof value !== "string" || !value) return "直接访问";
  try {
    return new URL(value).origin.slice(0, 180);
  } catch {
    return "直接访问";
  }
}

function safeText(value, fallback, maxLength) {
  if (typeof value !== "string") return fallback;
  const cleaned = value.replace(/[\r\n]/g, " ").trim();
  return cleaned ? cleaned.slice(0, maxLength) : fallback;
}

function deviceType(userAgent) {
  return /Android|iPhone|iPad|Mobile/i.test(userAgent || "") ? "移动设备" : "桌面设备";
}

async function requestFingerprint(request) {
  const ip = request.headers.get("CF-Connecting-IP") || "unknown";
  const userAgent = request.headers.get("User-Agent") || "unknown";
  const bytes = new TextEncoder().encode(`${ip}|${userAgent}`);
  const digest = await crypto.subtle.digest("SHA-256", bytes);
  return [...new Uint8Array(digest)]
    .slice(0, 12)
    .map((byte) => byte.toString(16).padStart(2, "0"))
    .join("");
}

async function rateLimitState(request, env) {
  const cache = globalThis.caches?.default;
  if (!cache) return { limited: false, remember: async () => {} };

  const fingerprint = await requestFingerprint(request);
  const key = new Request(`https://visitor-rate-limit.invalid/${fingerprint}`);
  try {
    if (await cache.match(key)) return { limited: true, remember: async () => {} };
    const seconds = Math.max(
      60,
      Number.parseInt(env.NOTIFY_COOLDOWN_SECONDS || "", 10) || DEFAULT_COOLDOWN_SECONDS,
    );
    return {
      limited: false,
      remember: () =>
        cache.put(
          key,
          new Response("1", { headers: { "Cache-Control": `public, max-age=${seconds}` } }),
        ),
    };
  } catch {
    return { limited: false, remember: async () => {} };
  }
}

function corsHeaders(origin) {
  return {
    "Access-Control-Allow-Origin": origin,
    "Access-Control-Allow-Methods": "POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
    "Access-Control-Max-Age": "86400",
    Vary: "Origin",
  };
}

async function sendPushPlus(env, details) {
  const response = await fetch("https://www.pushplus.plus/send", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      token: env.PUSHPLUS_TOKEN,
      title: "CAOM 网站有新访客",
      template: "txt",
      channel: "wechat",
      content: [
        `访问时间：${details.time}`,
        `访问页面：https://www.caom.online${details.path}`,
        `访问来源：${details.referrer}`,
        `大致地区：${details.country}`,
        `设备类型：${details.device}`,
        `浏览器语言：${details.language}`,
        `视口尺寸：${details.viewport}`,
      ].join("\n"),
    }),
  });

  if (!response.ok) throw new Error(`pushplus_http_${response.status}`);
  const result = await response.json().catch(() => ({}));
  if (result.code !== undefined && result.code !== 200) {
    const message = safeText(result.msg, "unknown", 80);
    throw new Error(`pushplus_code_${result.code}:${message}`);
  }
}

export async function handleRequest(request, env) {
  const url = new URL(request.url);
  if (request.method === "GET" && url.pathname === "/health") {
    return json({ ok: true, configured: Boolean(env.PUSHPLUS_TOKEN) }, 200);
  }
  if (url.pathname !== "/visit") return json({ ok: false, error: "not_found" }, 404);

  const origin = request.headers.get("Origin") || "";
  if (!allowedOrigins(env).has(origin)) return json({ ok: false, error: "forbidden" }, 403);
  if (request.method === "OPTIONS") return new Response(null, { status: 204, headers: corsHeaders(origin) });
  if (request.method !== "POST") return json({ ok: false, error: "method_not_allowed" }, 405, origin);
  if (!env.PUSHPLUS_TOKEN) return json({ ok: false, error: "not_configured" }, 503, origin);

  const contentLength = Number.parseInt(request.headers.get("Content-Length") || "0", 10);
  if (contentLength > MAX_BODY_BYTES) return json({ ok: false, error: "payload_too_large" }, 413, origin);

  let payload;
  try {
    const rawBody = await request.text();
    if (new TextEncoder().encode(rawBody).length > MAX_BODY_BYTES) {
      return json({ ok: false, error: "payload_too_large" }, 413, origin);
    }
    payload = JSON.parse(rawBody);
  } catch {
    return json({ ok: false, error: "invalid_json" }, 400, origin);
  }

  const rateLimit = await rateLimitState(request, env);
  if (rateLimit.limited) return json({ ok: true, deduplicated: true }, 202, origin);

  const details = {
    time: new Intl.DateTimeFormat("zh-CN", {
      timeZone: "Asia/Shanghai",
      dateStyle: "medium",
      timeStyle: "medium",
    }).format(new Date()),
    path: safePath(payload.path),
    referrer: safeReferrer(payload.referrer),
    country: request.cf?.country || "未知",
    device: deviceType(request.headers.get("User-Agent")),
    language: safeText(payload.language, "未知", 40),
    viewport: safeText(payload.viewport, "未知", 30),
  };

  try {
    await sendPushPlus(env, details);
    await rateLimit.remember();
  } catch (error) {
    console.error(error);
    return json({ ok: false, error: "notification_failed" }, 502, origin);
  }

  return json({ ok: true }, 202, origin);
}

export default {
  fetch(request, env) {
    return handleRequest(request, env);
  },
};
