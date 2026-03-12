# Modulo Cognito — Autenticazione Multi-Scenario

Responsabilita': Cognito User Pool, Identity Pool e Federation,
configurabili per 3 scenari di autenticazione.

## Scenari Supportati

| Scenario                | Risorse create                                   | Caso d'uso                                   |
|-------------------------|--------------------------------------------------|----------------------------------------------|
| A — User Pool classico  | User Pool, App Client, Domain                    | Login utenti (signup, signin, MFA, recovery) |
| B — User Pool + Identity | Tutto di A + Identity Pool, IAM roles            | Login + accesso diretto risorse AWS          |
| C — Federation only     | User Pool (no signup), SAML/OIDC IdP, App Client | SSO via Active Directory SIAE o IdP aziendale |

Selezione via variabile `auth_scenario`: `"user_pool"` | `"user_pool_identity"` | `"federation"`

## File Structure

```text
modules/cognito/
├── _input.tf                  # standard + auth_scenario, user_pool_name,
│                              #   password_policy, mfa_configuration,
│                              #   auto_verified_attributes, callback_urls,
│                              #   logout_urls, identity_providers,
│                              #   identity_pool_name,
│                              #   allow_unauthenticated, config
├── _local.tf                  # prefix, pool_name, domain_prefix
├── _output.tf                 # user_pool_id, user_pool_arn, app_client_id,
│                              #   app_client_secret_arn, identity_pool_id,
│                              #   user_pool_endpoint, hosted_ui_url
├── cognito-user-pool.tf       # aws_cognito_user_pool (schema attributes,
│                              #   password policy, MFA, account recovery,
│                              #   email verification, lambda triggers)
├── cognito-app-client.tf      # aws_cognito_user_pool_client
│                              #   (OAuth flows, scopes, callback/logout URLs,
│                              #   token validity, secret in Secrets Manager)
├── cognito-domain.tf          # aws_cognito_user_pool_domain
│                              #   (prefix-based o custom domain)
├── cognito-identity-pool.tf   # aws_cognito_identity_pool (solo scenario B)
│                              #   + IAM roles authenticated/unauthenticated
│                              #   count = var.auth_scenario == "user_pool_identity" ? 1 : 0
├── cognito-idp.tf             # aws_cognito_identity_provider (solo scenario C)
│                              #   SAML: metadata_url da IdP aziendale
│                              #   OIDC: issuer, client_id, client_secret
│                              #   for_each = var.auth_scenario == "federation" ? var.identity_providers : {}
├── cognito-lambda-triggers.tf # (opzionale) Lambda triggers per:
│                              #   pre_sign_up, post_confirmation,
│                              #   pre_token_generation, custom_message
└── cognito-iam.tf             # IAM roles per Identity Pool (scenario B):
                               #   authenticated_role, unauthenticated_role
```

## Dependency

Nessuna dipendenza da vpc (Cognito e' fully managed).
Dipendenza opzionale: se Lambda triggers → security group da vpc per VPC Lambda.

## Password Policy (default template)

| Param                            | Valore |
|----------------------------------|--------|
| minimum_length                   | 12     |
| require_lowercase                | true   |
| require_uppercase                | true   |
| require_numbers                  | true   |
| require_symbols                  | true   |
| temporary_password_validity_days | 7      |

## MFA Configuration

| Modo     | Quando                    |
|----------|---------------------------|
| OFF      | Sviluppo (solo per debug) |
| OPTIONAL | Collaudo, certificazione  |
| ON       | Produzione — obbligatorio |

MFA methods: `SOFTWARE_TOKEN_MFA` (TOTP) come default.
SMS_MFA opzionale (richiede SNS + spend limit).

## OAuth Flows

| Flow               | Quando                                  |
|--------------------|-----------------------------------------|
| code (PKCE)        | Default — SPA, mobile, server-side apps |
| implicit           | MAI — deprecato, insicuro               |
| client_credentials | Machine-to-machine (API-to-API)         |

## Federation — Scenario C

```hcl
identity_providers = {
  "SIAE-AD" = {
    provider_type = "SAML"
    metadata_url  = "https://adfs.siae.it/federationmetadata/..."
    attribute_mapping = {
      email    = "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress"
      name     = "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/name"
      username = "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/upn"
    }
  }
}
```

User Pool con `allow_admin_create_user_only = true` (no self-signup).

## Token Validity

| Token         | Sviluppo  | Collaudo  | Certificazione | Produzione |
|---------------|-----------|-----------|----------------|------------|
| Access token  | 1 ora     | 1 ora     | 30 minuti      | 15 minuti  |
| ID token      | 1 ora     | 1 ora     | 30 minuti      | 15 minuti  |
| Refresh token | 30 giorni | 30 giorni | 14 giorni      | 7 giorni   |

## Security

- Client secret in Secrets Manager (mai in variabili TF — V8)
- HTTPS-only callback URLs (no `http://` in prod)
- Prevent user existence errors: `ENABLED`
- Advanced security mode: `ENFORCED` in prod (adaptive auth, compromised credentials)

## Sizing per ambiente

| Param               | Sviluppo | Collaudo | Cert.    | Produzione  |
|---------------------|----------|----------|----------|-------------|
| mfa_configuration   | OFF      | OPTIONAL | OPTIONAL | ON          |
| advanced_security   | OFF      | AUDIT    | AUDIT    | ENFORCED    |
| token_validity      | estesa   | estesa   | standard | restrittiva |
| deletion_protection | false    | false    | true     | true        |
| lambda_triggers     | {}       | {}       | opzionali | attivi     |
