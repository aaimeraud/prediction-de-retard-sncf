"""
SNCF Delay Prediction - Security Guidelines

This document outlines security best practices for developers and deployers.
"""

# Security Configuration

## For Developers (Local Development)

### 1. Setup OpenSSL (macOS)

Install OpenSSL to replace LibreSSL:

```bash
brew install openssl
export LDFLAGS="-L/usr/local/opt/openssl/lib"
export CPPFLAGS="-I/usr/local/opt/openssl/include"
pip3 install --upgrade urllib3 requests
```

### 2. Run with Docker (Development)

```bash
export UID=$(id -u)
export GID=$(id -g)
docker compose up -d dev
```

This container includes:
- ✅ OpenSSL explicitly installed
- ✅ Non-root user (developer)
- ✅ UID/GID mapping for file permissions
- ✅ Security-hardened base image

### 3. Verify Security Before Committing

```bash
python3 -m pytest tests/ -v
python3 -c "import ssl; print(f'SSL Version: {ssl.OPENSSL_VERSION}')"
```

## For Deployment (Production)

### 1. Use Production Dockerfile

```bash
docker build -f Dockerfile.prod -t sncf-api:prod .
```

**Security improvements:**
- ✅ Multi-stage build (reduced attack surface, smaller image)
- ✅ Slim base image (tensorflow:2.15.0-python3.11-slim)
- ✅ OpenSSL installed and validated
- ✅ Non-root user (developer:developer)
- ✅ HEALTHCHECK endpoint
- ✅ Pinned dependency versions (requirements-prod.txt)

### 2. Deploy with Secure Compose

```bash
docker compose -f compose-prod.yaml up -d api
```

**Security features:**
- ✅ port: 127.0.0.1:8000 (localhost only, requires reverse proxy)
- ✅ read_only_root_filesystem: false (needed for models)
- ✅ security_opt: no-new-privileges:true
- ✅ cap_drop: ALL (drop all capabilities)
- ✅ cap_add: NET_BIND_SERVICE (only needed capability)
- ✅ Memory limits: 4GB hard, 2GB soft reservation
- ✅ CPU limits: 2.0 max, 1.0 reserved
- ✅ Restart policy: on-failure:3 (limit restart loops)
- ✅ Logging: json-file with rotation (max 10MB, 3 files)

### 3. Use a Reverse Proxy (nginx/Caddy)

**nginx example:**
```nginx
server {
    listen 443 ssl http2;
    server_name api.example.com;

    ssl_certificate /etc/ssl/certs/cert.pem;
    ssl_certificate_key /etc/ssl/private/key.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Request size limits
        client_max_body_size 10M;
        
        # Timeouts
        proxy_connect_timeout 10s;
        proxy_send_timeout 30s;
        proxy_read_timeout 30s;
    }
}
```

### 4. Environment Variables (Secrets Management)

Create `.env.prod` (never commit this file):

```bash
# .env.prod
TF_CPP_MIN_LOG_LEVEL=2
PYTHONUNBUFFERED=1

# Optional: For future API key management
# API_KEY=your-secret-key-here
# DATABASE_URL=postgresql://user:pass@host/db
```

Add to `.gitignore`:
```bash
.env
.env.prod
.env.local
*.pem
*.key
```

### 5. Input Validation & Rate Limiting

API automatically validates:
- ✅ hour_of_day: 0-23
- ✅ stop_lat: -90 to 90
- ✅ stop_lon: -180 to 180
- ✅ Batch size: 1-1000 items
- ✅ Pydantic type validation

For production, add rate limiting (e.g., with nginx):
```nginx
limit_req_zone $binary_remote_addr zone=api_limit:10m rate=10r/s;

location / {
    limit_req zone=api_limit burst=20 nodelay;
    proxy_pass http://127.0.0.1:8000;
}
```

## Security Checklist

### Before Deploying to Production

- [ ] Build with `Dockerfile.prod` (multi-stage, slim base)
- [ ] Use `requirements-prod.txt` (pinned versions)
- [ ] Deploy with `compose-prod.yaml` (resource limits, no-new-privileges)
- [ ] Use reverse proxy with TLS 1.2+
- [ ] Enable HEALTHCHECK monitoring
- [ ] Configure logging and log rotation
- [ ] Setup firewall rules (port 8000 only for reverse proxy)
- [ ] Verify non-root user is running container
- [ ] Test `/health` endpoint returns 200
- [ ] Monitor `/model/info` for model status

### Regular Maintenance

- [ ] **Weekly:** Check Docker image for vulnerabilities
  ```bash
  docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
    aquasec/trivy image sncf-api:prod
  ```

- [ ] **Monthly:** Update base images and dependencies
  ```bash
  pip3 install -U pip
  pip3 install --upgrade -r requirements-prod.txt
  ```

- [ ] **Quarterly:** Audit API logs for suspicious activity
  ```bash
  docker logs sncf-api-prod | grep -i error
  ```

## Known Warnings (Not Security Issues)

### 1. Pydantic V1 Style Validators (⚠️ Deprecation)
- Status: Non-blocking, validation works
- Action: Plan migration to `@field_validator` before Pydantic V3.0

### 2. Keras Early Stopping (⚠️ Information)
- Status: Training completes normally
- Action: None required

### 3. NumPy Conversion Warning (⚠️ Future)
- Status: Non-blocking
- Action: Will auto-fix in NumPy 1.26+

## Reporting Security Issues

If you discover a security vulnerability:
1. **DO NOT** open a public GitHub issue
2. Contact: [Your security contact email]
3. Provide reproducible proof-of-concept
4. Allow 7 days for patch before disclosure

## References

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [Docker Security Best Practices](https://docs.docker.com/develop/security-best-practices/)
- [TensorFlow Security](https://www.tensorflow.org/security)
- [FastAPI Security](https://fastapi.tiangolo.com/tutorial/security/)
