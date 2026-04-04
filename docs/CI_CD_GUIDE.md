# CI/CD Pipeline Guide

## Overview

This project uses GitHub Actions for automated testing, building, and deployment. The pipeline ensures code quality, runs comprehensive tests, and manages deployments to staging and production environments.

## Pipeline Architecture

```
Code Push
   ↓
┌─────────────────────────────────────┐
│      CI Jobs (Parallel)             │
├─────────────────────────────────────┤
│ • Unit Tests (3.9, 3.10, 3.11)     │
│ • Code Quality (lint, type-check)  │
│ • Security Scanning (bandit)       │
│ • Docker Build (cache optimization)│
└─────────────────────────────────────┘
         ↓
   All CI Passed?
   /              \
  Y                N
  ↓                ↓
 CD            Notify & Fail
  ↓
┌─────────────────────────────────────┐
│  CD Pipeline                        │
├─────────────────────────────────────┤
│ 1. Build & Push Docker Image        │
│ 2. Deploy to Staging (develop)      │
│ 3. Deploy to Production (main/tags) │
│ 4. Verify & Notify                  │
└─────────────────────────────────────┘
```

## GitHub Actions Workflows

### CI Workflow (`.github/workflows/ci.yaml`)

**Triggers:**
- Push to any branch
- Pull requests to main/develop

**Jobs:**

#### 1. Test Job
```yaml
Runs on: ubuntu-latest
Matrix: Python 3.9, 3.10, 3.11

Steps:
  1. Checkout code
  2. Setup Python
  3. Cache pip dependencies
  4. Install requirements
  5. Run pytest (unit + integration tests)
  6. Upload coverage to Codecov
  7. Linting (flake8)
  8. Type checking (mypy)
```

**Environment Variables:**
- `PYTHONPATH=/app`
- `TF_CPP_MIN_LOG_LEVEL=2` (reduce TF verbosity)

**Coverage Thresholds:**
- Minimum overall: 80%
- src/: 85%
- tests/: 70%

#### 2. Security Job
```yaml
Runs on: ubuntu-latest

Steps:
  1. Checkout code
  2. Setup Python
  3. Install bandit & safety
  4. Scan for security vulnerabilities
  5. Check for known CVEs
```

#### 3. Docker Build Job
```yaml
Depends on: test job
Runs on: ubuntu-latest

Steps:
  1. Setup BuildX (buildkit)
  2. Build Docker image (cache optimization)
  3. Test image (TensorFlow import)
  4. Note: Push only on CD workflow
```

### CD Workflow (`.github/workflows/cd.yaml`)

**Triggers:**
- Push to main or develop branches
- Git tags (v*)

**Jobs:**

#### 1. Build & Push
```yaml
Runs on: ubuntu-latest

Steps:
  1. Checkout code
  2. Login to GitHub Container Registry
  3. Extract metadata (version, tags, labels)
  4. Build and push Docker image
  
Tags Generated:
  - branch:latest (main, develop)
  - semver:v1.2.3
  - sha:commit-hash
```

#### 2. Deploy Staging (develop)
```yaml
Trigger: develop branch push
Environment: staging

Steps:
  1. Pull latest image
  2. Start services (docker-compose)
  3. Run smoke tests
  4. Health checks
```

#### 3. Deploy Production (main + tags)
```yaml
Trigger: main branch push OR tags
Environment: production
Approval: Required

Steps:
  1. Pull latest image
  2. Blue-green deployment
  3. Health check validation
  4. Rollback on failure
  5. Create GitHub deployment
```

#### 4. Notifications
```yaml
Slack integration on:
  - Pipeline failure
  - Production deployment
  - Security issues
```

## Local Development

### Prerequisites

```bash
# Python 3.9+
python3 --version

# Docker & Docker Compose
docker --version
docker-compose --version

# Git
git --version
```

### Quick Start

```bash
# 1. Clone and setup
git clone git@github.com:aaimeraud/prediction-de-retard-sncf.git
cd prediction-de-retard-sncf
git worktree add ./worktrees/develop develop

# 2. Activate worktree
cd worktrees/develop

# 3. Install dependencies
make install

# 4. Run tests
make test

# 5. Start services
make docker-compose-up
```

### Makefile Commands

#### Installation
```bash
make install          # Production deps (pip3)
make dev              # +Development deps
```

#### Testing
```bash
make test             # Run tests (pytest)
make test-coverage    # +Coverage report
make lint             # Code style (flake8)
make type-check       # Type annotations (mypy)
make security         # Vulnerabilities (bandit)
```

#### Docker
```bash
make docker                 # Build image
make docker-run             # Run interactively
make docker-test            # Tests in container
make docker-compose-up      # Start all services
make docker-compose-down    # Stop services
```

#### Utilities
```bash
make format           # Auto-format code
make clean            # Remove build artifacts
make docs             # List doc files
```

## Configuration

### Environment Variables

**Development:**
```bash
export PYTHONPATH=/app
export TF_CPP_MIN_LOG_LEVEL=2
export SNCF_API_KEY=your_key_here
```

**GitHub Actions Secrets** (Settings → Secrets):
```
DOCKER_REGISTRY_TOKEN      # GitHub Container Registry
SLACK_WEBHOOK              # Notifications
PRODUCTION_DEPLOY_KEY      # SSH key for production
```

### GitHub Secrets Setup

```bash
# 1. Authenticate with GitHub
gh auth login

# 2. Add Docker registry token
gh secret set GITHUB_TOKEN --body "your_github_token"

# 3. Add Slack webhook
gh secret set SLACK_WEBHOOK --body "https://hooks.slack.com/services/..."

# 4. List secrets
gh secret list
```

## Deployment

### Staging Deployment

**Trigger:** Push to `develop` branch

```bash
# What happens automatically:
1. CI tests run (all pass)
2. Docker image built & pushed to ghcr.io
3. docker-compose pulls latest image
4. Services restart with new version
5. Smoke tests run
6. Slack notification sent
```

### Production Deployment

**Trigger:** Push to `main` or create release tag

```bash
# Option 1: Merge develop → main
git checkout main
git merge develop
git push origin main

# Option 2: Create release tag
git tag -a v1.1.0 -m "Release 1.1.0"
git push origin v1.1.0

# What happens:
1. All CI checks run
2. Docker image built with version tag
3. Manual approval required (GitHub environment)
4. Blue-green deployment
5. Health checks validated
6. GitHub deployment created
7. Slack notification sent
```

### Rollback

```bash
# 1. List available versions
docker ps -a | grep sncf

# 2. Revert deployment
docker-compose -f compose.yaml down
docker-compose -f compose.yaml up -d   # Uses previous image

# 3. Verify services
curl http://localhost:5000/health
```

## Monitoring

### Test Results

```bash
# View results locally
make test
pytest tests/ --html=report.html

# View in GitHub Actions
GitHub → Actions → Latest workflow → Artifacts
```

### Coverage Reports

```bash
# Generate locally
make test-coverage

# View report
open htmlcov/index.html

# GitHub: Upload to Codecov
Actions → Workflows reports
```

### Docker Logs

```bash
# Development
docker-compose logs -f ml-engine

# Production
kubectl logs -f deployment/ml-engine  # If using Kubernetes
```

## Troubleshooting

### Tests Fail Locally but Pass in CI

```bash
# Ensure Python version matches
python3 --version  # Should be 3.9+

# Run in same environment as CI
docker build -f Dockerfile -t test-env .
docker run --rm test-env python3 -m pytest tests/
```

### Docker Build Fails

```bash
# Clear cache
docker system prune -a
docker image rm sncf-delay-prediction:latest

# Rebuild
make docker

# Check Dockerfile
docker build --no-cache -f Dockerfile .
```

### Deployment Stuck

```bash
# Check service status
docker-compose ps

# View logs
docker-compose logs ml-engine

# Force restart
docker-compose restart ml-engine
```

### Security Scan Issues

```bash
# Run locally
bandit -r src/

# Fix common issues
pip install -U --security | pip3 install

# Update dependencies
pip3 list --outdated
pip3 install --upgrade package-name
```

## Best Practices

### Code Review Checklist

Before merging:
- [ ] All CI checks pass
- [ ] Coverage maintained (≥80%)
- [ ] Security scan passes
- [ ] Linting clean
- [ ] Type hints complete
- [ ] Docstrings present
- [ ] Tests added/updated
- [ ] Documentation updated

### Release Process

```
1. Develop feature on feature branch
   git checkout -b feat/new-feature

2. Push and create PR
   git push origin feat/new-feature

3. GitHub Actions runs CI
   - Tests
   - Coverage
   - Security
   - Lint

4. Code review & approval

5. Merge to develop
   - Automatic deployment to staging

6. Test on staging environment
   - Smoke tests
   - Manual validation

7. Create release PR (develop → main)

8. Merge to main
   - Automatic deployment to production

9. Tag release
   git tag -a v1.1.0 -m "Release 1.1.0"
```

### Version Tagging

```bash
# Semantic versioning
git tag v1.0.0          # Major release
git tag v1.1.0          # Minor release
git tag v1.0.1          # Patch release
git tag v1.1.0-alpha.1  # Prerelease

# Push tags
git push origin --tags
```

## CI/CD Optimization

### Build Cache Strategy

```yaml
# GitHub Actions
cache-from: type=gha       # Use GitHub Actions cache
cache-to: type=gha,mode=max  # Save for next builds

# Result: ~2-3x faster builds after first run
```

### Parallel Testing

```yaml
# Matrix testing across Python versions
strategy:
  matrix:
    python-version: ["3.9", "3.10", "3.11"]

# Result: 3 jobs run in parallel
```

### Dependency Caching

```yaml
# Cache pip downloads
- uses: actions/cache@v3
  with:
    path: ~/.cache/pip
    key: ${{ runner.os }}-pip-${{ hashFiles('**/requirements.txt') }}

# Result: ~60% faster dependency installation
```

## Accessing Logs

### GitHub Actions UI

1. Go to GitHub repo
2. Click "Actions" tab
3. Select workflow run
4. Click job name
5. View step logs

### Download Artifacts

```bash
# Via GitHub CLI
gh run download <RUN_ID> -D artifacts/

# View artifacts in UI
Actions → Run → Artifacts section
```

## Future Enhancements

1. **Performance Benchmarking**: Track model inference time across versions
2. **SonarQube Integration**: Code quality metrics beyond linting
3. **Automated Scaling**: Scale based on deployment type
4. **Feature Flags**: Gradual rollout of new models
5. **Cost Monitoring**: Track CI/CD pipeline execution costs
6. **Advanced Monitoring**: Prometheus/Grafana integration

## References

- [GitHub Actions Docs](https://docs.github.com/en/actions)
- [Docker Best Practices](https://docs.docker.com/develop/dev-best-practices/)
- [Semantic Versioning](https://semver.org/)
- [pytest Coverage](https://pytest-cov.readthedocs.io/)
