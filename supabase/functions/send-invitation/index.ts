import { serve } from "https://deno.land/std@0.177.0/http/server.ts"

const SENDGRID_API_KEY = Deno.env.get("SENDGRID_API_KEY")
const SENDER_EMAIL = Deno.env.get("SENDER_EMAIL") || "matteo.marcon24@gmail.com"
const BEPI_URL = Deno.env.get("BEPI_URL") || "https://bepi-space.streamlit.app"

const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
}

serve(async (req) => {
  if (req.method === "OPTIONS") {
    return new Response("ok", { headers: corsHeaders })
  }

  if (req.method !== "POST") {
    return new Response("Method not allowed", { status: 405 })
  }

  try {
    const { recipient_email, recipient_name, mission_name, invite_code } = await req.json()

    if (!recipient_email || !invite_code) {
      return new Response(
        JSON.stringify({ error: "recipient_email and invite_code are required" }),
        { status: 400, headers: { ...corsHeaders, "Content-Type": "application/json" } }
      )
    }

    if (!SENDGRID_API_KEY) {
      return new Response(
        JSON.stringify({ error: "SENDGRID_API_KEY not configured" }),
        { status: 500, headers: { ...corsHeaders, "Content-Type": "application/json" } }
      )
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
      <p>Hi <strong>${recipient_name || "there"}</strong>,</p>
      <p>You've been invited to join the mission:</p>
      <div class="mission-badge">🚀 ${mission_name}</div>
      <p>Use the invite code below to access the project:</p>
      <div class="code-box">
        <p>Your invite code</p>
        <div class="code">${invite_code}</div>
      </div>
      <div class="cta">
        <a href="${BEPI_URL}" class="btn">Open BEPI</a>
      </div>
      <div class="steps">
        <p>How to join</p>
        <ol>
          <li>Open BEPI at <a href="${BEPI_URL}">${BEPI_URL}</a></li>
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

    const res = await fetch("https://api.sendgrid.com/v3/mail/send", {
      method: "POST",
      headers: {
        "Authorization": `Bearer ${SENDGRID_API_KEY}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        personalizations: [{ to: [{ email: recipient_email, name: recipient_name || "" }] }],
        from: { email: SENDER_EMAIL, name: "BEPI Space" },
        subject: `You're invited to join ${mission_name} on BEPI`,
        content: [{ type: "text/html", value: emailHtml }],
      }),
    })

    if (!res.ok) {
      const data = await res.json().catch(() => ({}))
      console.error("SendGrid error:", data)
      return new Response(
        JSON.stringify({ error: data.errors?.[0]?.message || "Failed to send email" }),
        { status: 500, headers: { ...corsHeaders, "Content-Type": "application/json" } }
      )
    }

    return new Response(
      JSON.stringify({ success: true }),
      { status: 200, headers: { ...corsHeaders, "Content-Type": "application/json" } }
    )
  } catch (err) {
    console.error("Unexpected error:", err)
    return new Response(
      JSON.stringify({ error: err.message }),
      { status: 500, headers: { ...corsHeaders, "Content-Type": "application/json" } }
    )
  }
})
