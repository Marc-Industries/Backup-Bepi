# Setup Email Invitations with Supabase Edge Functions

## Overview

BEPI uses **Supabase Edge Functions** to send invitation emails. This is **completely free** and doesn't require external SMTP services.

The flow:
1. When you invite a team member, a code is generated and stored in the `email_queue` table
2. The `send-invitation` Edge Function reads from `email_queue` and sends emails
3. Emails are sent via **Resend API** (free tier: 100 emails/day)

## Quick Setup (5 minutes)

### 1. Create Resend Account (FREE)

1. Go to [resend.com](https://resend.com)
2. Sign up with your email
3. Go to API Keys section
4. Copy your API key (starts with `re_`)

### 2. Deploy the Edge Function

**Note for macOS 12 users:** Docker Desktop is not supported on macOS versions older than Sonoma. Use Colima instead:

```bash
# Install Colima and qemu (if not already installed)
brew install colima qemu

# Start Colima VM
colima start

# Verify Docker works
docker ps
```

Then proceed with Supabase CLI:

```bash
# Install Supabase CLI if not already installed
brew install supabase/tap/supabase

# Link to your Supabase project
supabase link

# Set the Resend API key as a secret
supabase secrets set RESEND_API_KEY=re_YOUR_KEY_HERE

# Deploy the function
supabase functions deploy send-invitation
```

**For other OS (Linux/Windows/macOS Sonoma+):**

```bash
# Install Supabase CLI if not already installed
brew install supabase/tap/supabase  # macOS/Linux
# or npm install -g supabase  # alternative

# Link to your Supabase project
supabase link

# Set the Resend API key as a secret
supabase secrets set RESEND_API_KEY=re_YOUR_KEY_HERE

# Deploy the function
supabase functions deploy send-invitation
```

### 3. Set the BEPI URL (Optional)

If you want the email link to point to a specific URL:

```bash
supabase secrets set BEPI_URL=https://bepi-space.streamlit.app
```

## Verify it Works

### Test via CLI:

```bash
supabase functions invoke send-invitation --auth-level anon \
  -H "Authorization: Bearer YOUR_ANON_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "recipient_email": "test@example.com",
    "recipient_name": "Test User",
    "mission_name": "BEPI-SAT",
    "invite_code": "ABC123XY"
  }'
```

### Test via Streamlit:

1. Go to Team & Roles tab
2. Invite a team member
3. Check if email was received

## Monitoring

### View Email Queue Status:

```sql
-- Check pending emails
select id, recipient_email, status, created_at, error_message 
from email_queue 
where status = 'pending' 
order by created_at desc;

-- Check failed emails
select id, recipient_email, error_message, retry_count
from email_queue 
where status = 'failed' 
order by created_at desc;
```

### View Function Logs:

```bash
supabase functions list
supabase functions logs send-invitation
```

## Customization

### Change Email Template

Edit `supabase/functions/send-invitation/index.ts` and modify the `emailHtml` variable.

### Use Different Email Provider

The function is designed to work with any email provider:

- **Resend** (current): Free tier, 100 emails/day
- **SendGrid**: Free tier available
- **Mailgun**: Free tier available
- **AWS SES**: Pay-as-you-go

To change providers, update the fetch call to use their API.

### Increase Email Rate

Upgrade your Resend account to send more emails (unlimited in paid tier).

## Troubleshooting

### "Edge Function not found" in Streamlit

The function might not be deployed yet. The system automatically falls back to showing the code to copy manually.

### "Email not sent"

1. Check Resend API key is correct: `supabase secrets list`
2. Check function logs: `supabase functions logs send-invitation`
3. Verify RESEND_API_KEY is set: `supabase secrets list | grep RESEND`

### Emails going to spam

Configure DKIM/SPF for your domain in Resend dashboard (optional).

## Cost Analysis

- **Supabase Edge Functions**: FREE (5K invocations/month free tier)
- **Resend**: FREE (100 emails/day free tier)
- **Total**: $0/month for typical usage

## Fallback Mode

If the Edge Function fails for any reason:

1. The invite code is always generated and stored
2. The system shows "Share this code manually"
3. Users can still join by pasting the code in Settings → Join Mission

This ensures the system works offline and without external dependencies.

## Next Steps

1. ✅ Deploy the Edge Function (see above)
2. ✅ Test by inviting a team member
3. ✅ Monitor email_queue table for issues
4. ✅ Scale email volume if needed

Questions? Check Supabase docs: https://supabase.com/docs/guides/functions
