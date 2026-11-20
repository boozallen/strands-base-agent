---
sidebar_position: 3
---

# TLS Posture Configuration

The [Strands Base Agent](../index.md) requires an explicit TLS posture declaration. The server
will not start if `STRANDS_TLS_MODE` is unset. This ensures every deployment has a
conscious decision about how TLS is handled.

## Configuration

Set `STRANDS_TLS_MODE` in `.env` ([`env.template`](../../../env.template) ships it as `off`) or in the environment. The server reads TLS settings only from environment variables, not from [`config.yaml`](../../../config.yaml).

```bash
STRANDS_TLS_MODE=off
```

## Modes

### Off mode

TLS is terminated by the deployment platform (ingress controller, envoy
sidecar, cloud load balancer). Uvicorn serves plain HTTP inside the cluster.

```bash
STRANDS_TLS_MODE=off
```

This is the standard configuration for EKS deployments with a service mesh.
The application trusts that the platform enforces TLS on all external traffic.

### Native mode

TLS is terminated directly by uvicorn. Use this when running standalone without
a proxy or service mesh in front.

```bash
STRANDS_TLS_MODE=native
STRANDS_TLS_KEYFILE=/etc/tls/key.pem
STRANDS_TLS_CERTFILE=/etc/tls/cert.pem
```

The cert and key files must exist and be readable at startup. The server will
refuse to start if either file is missing.

Certificate provisioning (generation, rotation, renewal) is outside the scope
of this application. Use cert-manager, Kubernetes secrets, or your
organization's PKI process to place the files at the configured paths.

### Native mode with mTLS

To require client certificate verification (mutual TLS), provide a CA
certificate file. When configured, the server rejects connections from clients
that do not present a certificate signed by the trusted CA.

```bash
STRANDS_TLS_MODE=native
STRANDS_TLS_KEYFILE=/etc/tls/key.pem
STRANDS_TLS_CERTFILE=/etc/tls/cert.pem
STRANDS_TLS_CA_CERTFILE=/etc/tls/ca.pem
```

When `STRANDS_TLS_CA_CERTFILE` is set, the server enforces `ssl.CERT_REQUIRED`.
Only clients presenting a certificate signed by the CA in that file can connect.

When `STRANDS_TLS_CA_CERTFILE` is not set, native mode uses one-way TLS
(server presents its cert, clients are not verified). This is backward-compatible
with existing deployments.

The CA cert file must exist and be readable at startup. The server will refuse to
start if the file is missing.

## Startup behavior

| Condition | Result |
|-----------|--------|
| `STRANDS_TLS_MODE` unset | Server exits with error |
| `STRANDS_TLS_MODE` invalid value | Server exits with error |
| `STRANDS_TLS_MODE=off` | Uvicorn starts on HTTP |
| `STRANDS_TLS_MODE=native`, cert and key exist | Uvicorn starts on HTTPS (TLS) |
| `STRANDS_TLS_MODE=native`, cert, key, and CA exist | Uvicorn starts on HTTPS (mTLS) |
| `STRANDS_TLS_MODE=native`, cert or key missing | Server exits with error |
| `STRANDS_TLS_MODE=native`, CA cert file missing | Server exits with error |

## Verifying TLS termination

### Off mode

Verify that TLS is enforced at the ingress layer:

1. Check ingress annotations or gateway configuration for TLS settings
2. Confirm the service mesh policy requires mTLS between pods (if applicable)
3. Test externally: `curl -v https://<external-url>` should show a valid
   certificate from your ingress/LB

### Native mode

Verify that uvicorn is serving HTTPS:

1. Check startup logs for "TLS posture: native"
2. Test locally: `curl -v https://localhost:8000/api/v1/health`
3. Verify cert expiry: `openssl x509 -in /etc/tls/cert.pem -noout -enddate`

## STIG compliance

This configuration satisfies STIG V-222596 (APSC-DV-002440) by ensuring:

- TLS protection is explicitly declared (not implicit or assumed)
- The application fails closed if TLS posture is not configured
- Audit logs record which TLS mode is active at startup

The mTLS capability satisfies STIG V-222532 and V-222534 by providing the
ability to enforce mutual authentication when required by policy or data
classification. Enabling mTLS is a deployment decision based on whether the
data handled requires non-repudiation or endpoint device authentication.
