# SSO Authentication Flows for Neo4j

## Overview

There are two categories of principals that need to authenticate against Neo4j via SSO:

- **Users** — human beings interacting through a browser or a device
- **Applications** — backend services or daemons acting autonomously

Each category requires a different OAuth 2.0 / OIDC flow.

---

## For Users

### Authorization Code Flow with PKCE

The **Authorization Code Flow with PKCE** (Proof Key for Code Exchange) is the recommended flow for any application where a human user authenticates interactively in a browser.

**How it works:**
1. The client generates a random `code_verifier` and derives a `code_challenge` from it (SHA-256 hash).
2. The user is redirected to the Identity Provider (e.g. Azure AD) with the `code_challenge`.
3. After successful login, the IdP returns an authorization `code` to the redirect URI.
4. The client exchanges the `code` + the original `code_verifier` for an `access_token` and `id_token`.

**Pros:**
- Secure even for public clients (SPAs, mobile apps) — no client secret needed.
- PKCE prevents authorization code interception attacks.
- Short-lived tokens reduce exposure window.
- Widely supported and the current industry standard for user-facing flows.

**Cons:**
- Requires a browser redirect, so it does not work in headless or terminal-only environments.
- Slightly more complex to implement than the implicit flow (which is now deprecated).

---

### Device Authorization Flow

The **Device Authorization Flow** (also called Device Code Flow) is designed for devices or CLI tools that cannot open a browser or handle redirects.

**How it works:**
1. The client requests a `device_code` and a `user_code` from the IdP.
2. The user is instructed to visit a URL on *any* device (e.g. their phone or another computer) and enter the `user_code`.
3. Meanwhile the client polls the IdP until the user completes authentication.
4. Once approved, the IdP returns an `access_token` to the polling client.

**Pros:**
- Works on headless servers, IoT devices, CLIs, and terminals with no browser.
- Delegates the actual login to a device the user already trusts.
- Supports MFA and conditional access policies.

**Cons:**
- Polling introduces latency; the user experience is less fluid than a browser redirect.
- Tokens are still user-scoped, so the session is tied to the user's identity.
- Not suitable for fully automated, unattended scenarios (use Client Credentials instead).

---

## For Applications

### Client Credentials Flow

The **Client Credentials Flow** is designed for machine-to-machine (M2M) authentication where no human user is involved. The application authenticates as itself using its own identity (a **Service Principal** in Azure AD).

**How it works:**
1. The backend application sends its `client_id` and `client_secret` (or a certificate) directly to the token endpoint.
2. The IdP validates the credentials and returns an `access_token`.
3. The application uses that token to call the target resource (e.g. Neo4j).

**Pros:**
- Fully automated — no user interaction required.
- Credentials are managed at the application level (secrets, certificates, managed identities).
- Suitable for scheduled jobs, ETL pipelines, and backend services.

**Cons:**
- No user identity in the token — the token represents the app, not a person.
- If the client secret is leaked, the entire service account is compromised.
- Role/permission management is done via **App Roles** (not user group membership — see below).

---

## Neo4j Configuration for Combined User and Application Authentication

Neo4j supports multiple simultaneous OIDC providers. Each provider is identified by an `<idp-id>` and has its own block of settings in `neo4j.conf`. The number of provider blocks you need depends on your app registration setup:

- **Single provider block** — works when both user tokens (PKCE) and application tokens (Client Credentials) share the **same audience value**. This is the case when both flows use the same app registration. The `auth_flow=pkce` setting only controls what the browser-based client (Neo4j Browser, Bloom) initiates; Neo4j validates all incoming bearer tokens against the configured provider regardless of which flow produced them.
```
dbms.security.authentication_providers=oidc-myidp,native
dbms.security.authorization_providers=oidc-myidp,native
```

- **Two provider blocks** — required when the user-facing application and the backend service use **separate app registrations** with different audience values. In that case, list both providers:

```
dbms.security.authentication_providers=oidc-users,oidc-app,native
dbms.security.authorization_providers=oidc-users,oidc-app,native

# Prevent display in Neo4j browser SSO list
dbms.security.oidc.app.visible=false
```

### Why audience values matter

The `aud` claim in a JWT identifies the intended recipient. Neo4j validates it strictly against the `audience` setting of the matching provider block.

If you use a **single provider block** for both flows, both token types must produce the same `aud` value. This is achievable when both flows target the same app registration (e.g. with `accessTokenAcceptedVersion=2` on Azure AD, both yield `aud = client_id GUID`).

If you use **two provider blocks** (separate app registrations), each block has its own `audience` setting:

| Flow | Token subject | `audience` to configure in Neo4j |
|---|---|---|
| PKCE / Device Code | User identity | Audience of user-flow tokens |
| Client Credentials | Service Principal / App identity | Audience of application tokens (different value) |

---

## Neo4j Aura and Programmatic Access

If you are running Neo4j on **Aura** (the managed cloud service), configuring SSO for programmatic / backend access is **not fully self-service**. Unlike a self-hosted Neo4j instance where you can edit `neo4j.conf` directly, Aura's infrastructure configuration is managed by Neo4j.

- To set up an application (Service Principal / Client Credentials flow) connecting to an Aura instance via SSO, You cannot apply these settings yourself through the Aura console. **You must contact Neo4j Support** and open a support ticket.

- To set up user-facing SSO (browser login via Neo4j, Bloom, Neodash), you can set it up following https://neo4j.com/docs/aura/security/single-sign-on/

---


