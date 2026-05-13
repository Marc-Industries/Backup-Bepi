import random
import string
import httpx
from bepi.supabase_client import get_supabase, get_service_client


def _generate_invite_code(length: int = 8) -> str:
    """Genera un codice di invito casuale."""
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))


def _send_invitation_email(
    recipient_email: str,
    recipient_name: str,
    mission_name: str,
    invite_code: str,
) -> dict:
    """
    Chiama una Supabase Edge Function per inviare l'email di invito.

    Ritorna un dict strutturato con lo stato dell'invio e i dettagli di eventuali errori.
    """
    result = {
        "ok": False,
        "edge_function_url": None,
        "status_code": None,
        "response_text": None,
        "error": None,
    }

    try:
        secrets = {}
        try:
            secrets = __import__("streamlit").secrets.get("supabase", {})
        except Exception:
            pass

        url = secrets.get("url", "")
        anon_key = secrets.get("anon_key", "")

        if not url or not anon_key:
            result["error"] = "Supabase secrets not configured"
            result["response_text"] = "Missing supabase.url or supabase.anon_key in .streamlit/secrets.toml"
            return result

        # Chiama la Edge Function
        edge_fn_url = f"{url}/functions/v1/send-invitation"
        result["edge_function_url"] = edge_fn_url
        headers = {
            "Authorization": f"Bearer {anon_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "recipient_email": recipient_email,
            "recipient_name": recipient_name,
            "mission_name": mission_name,
            "invite_code": invite_code,
        }

        response = httpx.post(
            edge_fn_url,
            headers=headers,
            json=payload,
            timeout=10.0,
        )

        result["status_code"] = response.status_code
        result["response_text"] = response.text

        if response.status_code in (200, 201):
            result["ok"] = True
            return result

        try:
            result_json = response.json()
            result["error"] = result_json.get("error") or result_json.get("message")
        except Exception:
            result["error"] = response.text

        return result
    except Exception as exc:
        result["error"] = str(exc)
        result["response_text"] = "Exception while calling edge function"
        return result


def invite_team_member(mission_id: str, email: str, full_name: str, role: str, subsystem: str | None) -> dict:
    """
    Invita un membro del team tramite codice di invito.
    
    Flusso:
    1. Crea un codice di invito univoco
    2. Inserisce il record nella tabella `invitations`
    3. Un trigger PostgreSQL inserisce il record in `email_queue`
    4. Prova a inviare email tramite Edge Function (opzionale)
    5. Se Edge Function fallisce, il codice viene mostrato nell'UI per copiarlo
    
    Nessun servizio SMTP esterno richiesto - tutto è gestito via Supabase!
    """
    client = get_supabase()
    if not client:
        raise RuntimeError("Supabase client not available")

    # Genera un codice di invito univoco
    invite_code = _generate_invite_code()
    
    # Crea un entry di invito nel database
    result = client.table("invitations").insert({
        "mission_id": mission_id,
        "role": role,
        "subsystem": subsystem,
        "code": invite_code,
        "invite_email": email,
        "invite_name": full_name,
    }).execute()
    
    if not result.data:
        raise RuntimeError("Failed to create invitation in database")
    
    invitation = result.data[0]
    
    # Carica il nome della missione per l'email
    mission_result = client.table("missions").select("name").eq("id", mission_id).execute()
    mission_name = mission_result.data[0].get("name", "Mission") if mission_result.data else "Mission"
    
    # Prova a inviare email tramite Edge Function
    # Se non disponibile, il codice verrà mostrato nell'UI per copiarlo
    email_result = _send_invitation_email(email, full_name, mission_name, invite_code)
    email_sent = email_result.get("ok", False)

    # Aggiorna il flag email_sent nel database (opzionale)
    if email_sent:
        try:
            client.table("email_queue").update({"status": "sent"}).eq(
                "invitation_id", invitation.get("id")
            ).execute()
        except Exception:
            pass

    return {
        "invite_code": invite_code,
        "email": email,
        "full_name": full_name,
        "role": role,
        "mission_name": mission_name,
        "invitation_id": invitation.get("id"),
        "email_sent": email_sent,  # Indica se email è stata inviata
        "email_result": email_result,
    }

