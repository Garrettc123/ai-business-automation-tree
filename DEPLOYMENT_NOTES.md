# Deployment Notes

## Important Security Reminders

### Before Production Deployment:

1. **Change All Default Passwords**
   - Database: `DB_PASSWORD`, `REDIS_PASSWORD`, `MONGO_PASSWORD`
   - Grafana: `GRAFANA_PASSWORD`
   - Default admin user password (see init-scripts/01-init-schema.sql)

2. **Generate Secure Secrets**
   ```bash
   # Generate random secrets
   python -c "import secrets; print(secrets.token_urlsafe(32))"
   ```
   - Update `SECRET_KEY`
   - Update `JWT_SECRET_KEY`

3. **Configure SSL/TLS**
   - Obtain SSL certificates (Let's Encrypt recommended)
   - Update nginx.conf to enable HTTPS section
   - Redirect HTTP to HTTPS in production

4. **Environment-Specific Configuration**
   - Use separate `.env` files per environment
   - Never commit `.env` files to version control
   - Use secrets manager for production (AWS Secrets Manager, HashiCorp Vault)

## Minimum Requirements

- **Docker**: 20.10+
- **Docker Compose**: v2.0+ (version field removed from docker-compose.yml)
- **Python**: 3.10 or 3.11 (for local development)
- **Memory**: 4GB minimum, 8GB recommended
- **Disk**: 10GB minimum

## Quick Start

```bash
# 1. Clone and enter directory
git clone https://github.com/Garrettc123/ai-business-automation-tree.git
cd ai-business-automation-tree

# 2. Configure environment
cp .env.example .env
# Edit .env with your configuration

# 3. Run deployment
chmod +x setup.sh
./setup.sh
```

## Verification

```bash
# Run automated checks
./verify-deployment.sh

# Test health endpoint
curl http://localhost:8000/health

# View service status
docker compose ps
```

## Common Issues

1. **Port conflicts**: Change ports in docker-compose.yml if already in use
2. **SSL certificate errors in build**: Normal in CI/CD environments with proxies
3. **Database connection timeout**: Increase healthcheck intervals in docker-compose.yml

## Production Checklist

- [ ] Changed all default passwords
- [ ] Generated secure random secrets
- [ ] Configured SSL/TLS certificates
- [ ] Set up firewall rules
- [ ] Configured backup strategy
- [ ] Set up monitoring and alerting
- [ ] Reviewed and restricted CORS origins
- [ ] Enabled rate limiting
- [ ] Configured log rotation
- [ ] Set up automated security updates

## Support

For deployment issues:
- Check DEPLOYMENT.md for detailed instructions
- Review logs: `docker compose logs -f`
- Run verification: `./verify-deployment.sh`
- GitHub Issues: https://github.com/Garrettc123/ai-business-automation-tree/issues
