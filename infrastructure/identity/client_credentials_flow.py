import requests
from neo4j import GraphDatabase, bearer_auth

TENANT_ID     = "<TENANT_ID>"
CLIENT_ID     = "<CLIENT_ID>"
CLIENT_SECRET = "<CLIENT_SECRET>"

ISSUER     = f"https://login.microsoftonline.com/{TENANT_ID}/v2.0"
WELL_KNOWN = f"{ISSUER}/.well-known/openid-configuration"

# Client credentials flow uses .default scope on the target resource
SCOPES    = "api://<CLIENT_ID>/.default"
NEO4J_URI = "neo4j://<IP>:7687"


def get_well_known():
    r = requests.get(WELL_KNOWN, timeout=20)
    r.raise_for_status()
    return r.json()


def get_access_token_via_client_credentials():
    wk = get_well_known()
    token_endpoint = wk["token_endpoint"]

    data = {
        "grant_type": "client_credentials",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "scope": SCOPES,
    }

    resp = requests.post(
        token_endpoint,
        data=data,
        headers={"Accept": "application/json"},
        timeout=20,
    )

    if resp.status_code != 200:
        try:
            print("Token error:", resp.json())
        except Exception:
            print("Token error (raw):", resp.text)
        resp.raise_for_status()

    token = resp.json()

    access_token = token.get("access_token")
    if not access_token:
        raise RuntimeError("No access_token returned. Check scopes and app registration configuration.")

    return access_token


access_token = get_access_token_via_client_credentials()

print(access_token)

with GraphDatabase.driver(NEO4J_URI, auth=bearer_auth(access_token)) as driver:
    with driver.session() as s:
        print("Current user:", s.run("SHOW CURRENT USER").single())