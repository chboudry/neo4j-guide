## Azure AD / Entra ID Specificities

> The behaviors described in this section are **specific to Microsoft Azure AD / Entra ID**. Other IdPs (Keycloak, Okta, Auth0, etc.) handle these concerns differently.

### Token version and the `aud` claim value

Azure AD can issue two token versions, controlled by the `accessTokenAcceptedVersion` property in the app manifest:

| `accessTokenAcceptedVersion` | Token version | `aud` claim value |
|---|---|---|
| `null` or `1` | v1 | Application ID URI — e.g. `api://<client-id>` |
| `2` | v2 | Bare GUID — e.g. `12345678-...` |

The value you set for `dbms.security.oidc.<idp-id>.audience` in Neo4j must exactly match what Azure puts in the `aud` claim, so this manifest setting directly determines what you configure in Neo4j.

Setting `accessTokenAcceptedVersion` to `2` is generally recommended since it simplifies the audience value and is required to use v2 token endpoint features.

### Exposing an API on the app registration

For Azure AD to issue tokens that target your app as a resource (rather than a Microsoft resource like Graph), you must expose an API on the app registration:

1. In **App registrations** → your app → **Expose an API**, set the **Application ID URI** (e.g. `api://<client-id>`).
2. Add at least one scope (e.g. `access_as_user` for delegated flows, or any name for application flows).
3. Grant the client applications permission to that scope under **API Permissions**.

Without this, Azure AD does not recognize your app as a valid resource server and will refuse to issue tokens targeting it — regardless of what audience you configure in Neo4j.

### Group claims are not included by default

On Azure AD, the `groups` claim is **not included in tokens by default**, for any principal type (user or Service Principal). To enable it, you must configure `groupMembershipClaims` in the app manifest or add it as an optional claim:

```json
"groupMembershipClaims": "SecurityGroup"
```

Be aware that if a user belongs to many groups, Azure AD may omit the `groups` claim and include an overage indicator instead, requiring a separate Graph API call to retrieve the full list.

### App Roles for Service Principal authorization

For Client Credentials tokens, relying on group membership for authorization is unreliable on Azure AD. The standard and recommended approach is to use **App Roles**:

1. Define App Roles on the app registration (e.g. `Reader`, `Architect`).
2. Assign those roles to the Service Principal via the Enterprise Application → **Users and groups** screen.
3. Azure AD includes the assigned roles in the `roles` claim of the application token.
4. Map the `roles` claim in Neo4j: `dbms.security.oidc.<idp-id>.claims.groups=roles`.

### Service Principals have no username claim by default

Unlike users, a Service Principal does not have standard identity claims such as `preferred_username` or `email`. To provide Neo4j with a username, you must create a **custom claim** using an attribute mapping or a fixed value transformation in the Enterprise Application → **Single Sign-On** → **Attributes & Claims** configuration.

Additionally, for custom claim transformations to work, `acceptMappedClaims` must be set to `true` in the app manifest.
