import requests

def _auth_error(response, fallback):
    try:
        data = response.json()
        message = data.get("msg") or data.get("message") or data.get("error_description") or data.get("error") or fallback
    except Exception:
        message = fallback
    return f"{message} (HTTP {response.status_code})"

def sign_up(cfg, email, password):
    if not cfg.supabase_url or not cfg.supabase_key:
        raise RuntimeError("Configure SUPABASE_URL and SUPABASE_PUBLISHABLE_KEY in .env.")
    try:
        response = requests.post(
            f"{cfg.supabase_url}/auth/v1/signup",
            headers={"apikey": cfg.supabase_key, "Content-Type": "application/json"},
            json={"email": email, "password": password},
            timeout=cfg.request_timeout,
        )
    except requests.RequestException as exc:
        raise RuntimeError(f"Supabase connection failed: {exc}") from exc
    if not response.ok:
        raise RuntimeError(_auth_error(response, "Supabase sign-up failed."))
    data = response.json()
    user = data.get("user") or data
    return {"access_token": data.get("access_token"), "refresh_token": data.get("refresh_token"),
            "email": user.get("email") or email, "user_id": user.get("id"),
            "confirmation_required": not bool(data.get("access_token"))}

def sign_in(cfg,email,password):
    if not cfg.supabase_url or not cfg.supabase_key:raise RuntimeError("Configure SUPABASE_URL and SUPABASE_PUBLISHABLE_KEY in .env.")
    try:r=requests.post(f"{cfg.supabase_url}/auth/v1/token?grant_type=password",
      headers={"apikey":cfg.supabase_key,"Content-Type":"application/json"},
      json={"email":email,"password":password},timeout=cfg.request_timeout)
    except requests.RequestException as e:raise RuntimeError(f"Supabase connection failed: {e}") from e
    if not r.ok:
        try:
            d=r.json();msg=d.get("msg") or d.get("message") or d.get("error_description") or "Supabase sign-in failed."
        except Exception:msg="Supabase sign-in failed."
        raise RuntimeError(f"{msg} (HTTP {r.status_code})")
    data=r.json()
    if not data.get("access_token"):raise RuntimeError("Supabase did not return an access token.")
    u=data.get("user") or {}
    return {"access_token":data["access_token"],"refresh_token":data.get("refresh_token"),"email":u.get("email"),"user_id":u.get("id")}
def sign_out_local(cfg,token):
    if token and cfg.supabase_url:
        try:
            requests.post(f"{cfg.supabase_url}/auth/v1/logout",headers={"apikey":cfg.supabase_key,"Authorization":f"Bearer {token}"},timeout=10)
        except requests.RequestException:pass
