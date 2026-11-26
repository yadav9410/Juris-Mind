import os
import getpass
import requests
from dotenv import load_dotenv

# --------------------------------------------------
# 1. Load Supabase configuration from the .env file
# --------------------------------------------------

load_dotenv()

supabase_url = os.getenv("SUPABASE_URL")
supabase_key = (
    os.getenv("SUPABASE_PUBLISHABLE_KEY")
    or os.getenv("SUPABASE_KEY")
)

if not supabase_url:
    raise RuntimeError("SUPABASE_URL is missing from .env")

if not supabase_key:
    raise RuntimeError(
        "SUPABASE_PUBLISHABLE_KEY is missing from .env"
    )

# --------------------------------------------------
# 2. Collect test-user login credentials
# --------------------------------------------------

print("JurisMind - Supabase Test Login")

email = input("Enter test user email: ")
password = getpass.getpass("Enter test user password: ")

# --------------------------------------------------
# 3. Authenticate with Supabase
# --------------------------------------------------

url = (
    f"{supabase_url.rstrip('/')}"
    "/auth/v1/token?grant_type=password"
)

headers = {
    "apikey": supabase_key,
    "Content-Type": "application/json",
}

payload = {
    "email": email,
    "password": password,
}

try:
    response = requests.post(
        url,
        headers=headers,
        json=payload,
        timeout=30,
    )
except requests.RequestException as exc:
    raise RuntimeError(
        f"Could not connect to Supabase: {exc}"
    ) from exc

# --------------------------------------------------
# 4. Handle authentication result
# --------------------------------------------------

if response.status_code != 200:
    print("\nSupabase login failed.")
    print("HTTP status:", response.status_code)
    print("Error:", response.text)
    raise SystemExit(1)

data = response.json()

access_token = data.get("access_token")
user_info = data.get("user", {})

if not access_token:
    raise RuntimeError(
        "Supabase did not return an access token."
    )

print("\nSupabase login successful!")
print("Supabase user UUID:", user_info.get("id"))
print("Supabase user email:", user_info.get("email"))

# --------------------------------------------------
# 5. Display access token locally for Swagger
# --------------------------------------------------

print("\n" + "=" * 60)
print("SUPABASE ACCESS TOKEN")
print("=" * 60)
print(access_token)
print("=" * 60)
print("Copy this token into Swagger's Authorize dialog.")
print("Do not share this token or save it in project files.")

# --------------------------------------------------
# 6. Test the Increment 11 specialist-agent endpoint
# --------------------------------------------------

print("\nCalling JurisMind specialist-agent registry...")

api_response = requests.get(
    "http://127.0.0.1:8000/research/agents",
    headers={
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json",
    },
    timeout=30,
)

print("\nJurisMind API HTTP Status:", api_response.status_code)

try:
    result = api_response.json()
    print("API Response:")
    print(result)
except ValueError:
    print("API Response:")
    print(api_response.text)

# --------------------------------------------------
# 7. Explain the result
# --------------------------------------------------

if api_response.status_code == 200:
    print("\nSUCCESS: JurisMind accepted the authenticated request.")
elif api_response.status_code == 401:
    print("\nUNAUTHORIZED: Check the bearer token and authentication.")
elif api_response.status_code == 403:
    print(
        "\nFORBIDDEN: The token was not accepted for this operation "
        "or the JurisMind account/workspace is not provisioned."
    )
else:
    print("\nThe API returned an unexpected status. Review the response.")
