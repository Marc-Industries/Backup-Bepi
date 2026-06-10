import { serve } from "https://deno.land/std@0.177.0/http/server.ts"

const BREVO_API_KEY = Deno.env.get("BREVO_API_KEY")
const SENDER_EMAIL = Deno.env.get("SENDER_EMAIL") || "matteo.marcon24@gmail.com"
const BEPI_URL = Deno.env.get("BEPI_URL") || "https://bepi-space.streamlit.app"
// Auto-injected by Supabase into every Edge Function runtime.
const SUPABASE_URL = Deno.env.get("SUPABASE_URL")
const SERVICE_ROLE_KEY = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")

// Lock CORS to the app origin. The real caller is server-side (Streamlit, no
// Origin header, so unaffected); this just denies browser-based abuse.
const corsHeaders = {
  "Access-Control-Allow-Origin": BEPI_URL,
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
}

const json = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), {
    status,
    headers: { ...corsHeaders, "Content-Type": "application/json" },
  })

// Escape interpolated values so an attacker-controlled name/mission/code cannot
// inject HTML into the email body (phishing payloads, broken markup).
const esc = (s: unknown) =>
  String(s ?? "")
    .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;").replace(/'/g, "&#39;")

const isEmail = (s: string) => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(s)

serve(async (req) => {
  if (req.method === "OPTIONS") return new Response("ok", { headers: corsHeaders })
  if (req.method !== "POST") return new Response("Method not allowed", { status: 405 })

  try {
    const body = await req.json().catch(() => ({}))
    const invite_code = String(body.invite_code ?? "").trim()

    // invite_code is the only trusted input; recipient/mission come from the DB.
    if (!/^[A-Z0-9]{6,16}$/.test(invite_code)) {
      return json({ error: "invalid invite_code" }, 400)
    }
    if (!BREVO_API_KEY) return json({ error: "BREVO_API_KEY not configured" }, 500)
    if (!SUPABASE_URL || !SERVICE_ROLE_KEY) {
      return json({ error: "Supabase env not available" }, 500)
    }

    // --- Server-side validation: the code must match a real, unredeemed
    // invitation. This is what stops the function being an open email relay:
    // a caller cannot send mail to an arbitrary address, only (re)send the
    // invite to the address already stored for a pending code. ---
    const sb = (path: string) =>
      fetch(`${SUPABASE_URL}/rest/v1/${path}`, {
        headers: { apikey: SERVICE_ROLE_KEY!, Authorization: `Bearer ${SERVICE_ROLE_KEY}` },
      })

    const invRes = await sb(
      `invitations?code=eq.${encodeURIComponent(invite_code)}&used_at=is.null` +
      `&select=invite_email,invite_name,mission_id&limit=1`
    )
    if (!invRes.ok) return json({ error: "invitation lookup failed" }, 502)
    const invRows = await invRes.json().catch(() => [])
    const inv = Array.isArray(invRows) ? invRows[0] : null
    if (!inv) return json({ error: "no pending invitation for this code" }, 404)

    const recipient_email = String(inv.invite_email ?? "")
    if (!isEmail(recipient_email)) return json({ error: "invitation has no valid email" }, 422)
    const recipient_name = String(inv.invite_name ?? "")

    // Mission name from the DB (fall back to "your mission" if unavailable).
    let mission_name = "your mission"
    if (inv.mission_id) {
      const mRes = await sb(`missions?id=eq.${encodeURIComponent(inv.mission_id)}&select=name&limit=1`)
      if (mRes.ok) {
        const mRows = await mRes.json().catch(() => [])
        if (Array.isArray(mRows) && mRows[0]?.name) mission_name = String(mRows[0].name)
      }
    }

    const emailHtml = `
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <style>
    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #f5f5f5; margin: 0; padding: 40px 20px; }
    .container { max-width: 560px; margin: 0 auto; background: white; border-radius: 12px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.08); }
    .header { background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%); padding: 40px 40px 30px; text-align: center; }
    .header h1 { color: white; margin: 0; font-size: 28px; font-weight: 700; letter-spacing: -0.5px; }
    .header p { color: #a8b8d8; margin: 8px 0 0; font-size: 14px; }
    .body { padding: 40px; }
    .body p { color: #374151; line-height: 1.6; margin: 0 0 16px; }
    .mission-badge { display: inline-block; background: #eff6ff; color: #1d4ed8; border: 1px solid #bfdbfe; border-radius: 6px; padding: 6px 14px; font-size: 14px; font-weight: 600; margin: 8px 0 20px; }
    .code-box { background: #f8fafc; border: 2px dashed #e2e8f0; border-radius: 8px; padding: 20px; text-align: center; margin: 24px 0; }
    .code-box p { color: #64748b; font-size: 12px; text-transform: uppercase; letter-spacing: 1px; margin: 0 0 8px; }
    .code { font-family: 'Courier New', monospace; font-size: 28px; font-weight: 700; color: #1a1a2e; letter-spacing: 4px; }
    .cta { text-align: center; margin: 28px 0; }
    .btn { display: inline-block; background: #0f3460; color: white; text-decoration: none; padding: 14px 32px; border-radius: 8px; font-weight: 600; font-size: 15px; }
    .steps { background: #f8fafc; border-radius: 8px; padding: 20px 24px; margin: 24px 0; }
    .steps p { font-size: 13px; color: #64748b; margin: 0 0 8px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; }
    .steps ol { margin: 0; padding-left: 20px; color: #374151; font-size: 14px; line-height: 1.8; }
    .footer { padding: 20px 40px; border-top: 1px solid #f1f5f9; }
    .footer p { color: #94a3b8; font-size: 12px; margin: 0; }
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <h1>B.E.P.I.</h1>
      <p>Budget, Engineering &amp; Project Integration</p>
    </div>
    <div class="body">
      <p>Hi <strong>${esc(recipient_name) || "there"}</strong>,</p>
      <p>You've been invited to join the mission:</p>
      <div class="mission-badge">🚀 ${esc(mission_name)}</div>
      <p>Use the invite code below to access the project:</p>
      <div class="code-box">
        <p>Your invite code</p>
        <div class="code">${esc(invite_code)}</div>
      </div>
      <div class="cta">
        <a href="${BEPI_URL}" class="btn">Open BEPI</a>
      </div>
      <div class="steps">
        <p>How to join</p>
        <ol>
          <li>Open BEPI at <a href="${BEPI_URL}">${esc(BEPI_URL)}</a></li>
          <li>Go to <strong>Settings → Join Mission</strong></li>
          <li>Paste your invite code</li>
        </ol>
      </div>
    </div>
    <div class="footer">
      <p>You received this email because a team member invited you to BEPI. If this was unexpected, you can safely ignore this email.</p>
    </div>
  </div>
</body>
</html>`

    const res = await fetch("https://api.brevo.com/v3/smtp/email", {
      method: "POST",
      headers: { "api-key": BREVO_API_KEY!, "Content-Type": "application/json" },
      body: JSON.stringify({
        sender: { name: "BEPI Space", email: SENDER_EMAIL },
        to: [{ email: recipient_email, name: recipient_name }],
        subject: `You're invited to join ${mission_name} on BEPI`,
        htmlContent: emailHtml,
      }),
    })

    if (!res.ok) {
      const data = await res.json().catch(() => ({}))
      console.error("Brevo error:", data)
      return json({ error: data.message || "Failed to send email" }, 500)
    }

    return json({ success: true })
  } catch (err) {
    console.error("Unexpected error:", err)
    return json({ error: String((err as Error)?.message ?? err) }, 500)
  }
})
