from supabase import create_client

SUPABASE_URL = "https://kcetgbmtjsjsalyaifsf.supabase.co"
SERVICE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImtjZXRnYm10anNqc2FseWFpZnNmIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3NTM4MTE3MywiZXhwIjoyMDkwOTU3MTczfQ.o75VMwtI3c5S8xpJbIzI6Fm97MpVN8phzf2Dh-sqNN8"

client = create_client(SUPABASE_URL, SERVICE_KEY)

email = "admin@bepi.io"
password = "AdminPass123!"

result = client.auth.sign_up({
    "email": email,
    "password": password,
})

if result.user:
    print(f"User created: {result.user.id}")
else:
    print("Signup failed")