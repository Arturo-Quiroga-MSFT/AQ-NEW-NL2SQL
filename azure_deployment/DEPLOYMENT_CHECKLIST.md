# 📋 Azure Container Apps Deployment Checklist

Use this checklist to ensure a successful deployment of the NL2SQL Multi-Model app.

## Pre-Deployment

### Azure Account Setup
- [ ] Have active Azure subscription
- [ ] Have Contributor role on subscription or resource group
- [ ] Have Azure CLI installed (`az --version`)
- [ ] Logged in to Azure (`az login`)
- [ ] Correct subscription selected (`az account show`)

### Credentials Ready
- [ ] Azure OpenAI API key
- [ ] Azure OpenAI endpoint URL
- [ ] Azure OpenAI model deployments created:
  - [ ] gpt-4o-mini (for intent extraction)
  - [ ] gpt-4.1 or gpt-5-mini (for SQL generation)
  - [ ] gpt-4.1-mini (for result formatting)
- [ ] Azure SQL Server hostname
- [ ] Azure SQL Database name
- [ ] Azure SQL username
- [ ] Azure SQL password
- [ ] SQL firewall rules allow Azure services

### Local Setup
- [ ] Code repository cloned
- [ ] `.env.template` copied to `.env.azure`
- [ ] `.env.azure` configured with all credentials
- [ ] `deploy.sh` is executable (`chmod +x deploy.sh`)

## Deployment Phase

### Initial Deployment
- [ ] Run `./deploy.sh --preview` to preview changes
- [ ] Review what will be created
- [ ] Run `./deploy.sh` for full deployment
- [ ] Wait for deployment to complete (5-15 minutes)
- [ ] Note the application URL from output

### Verify Infrastructure
- [ ] Resource group created
- [ ] Azure Container Registry created
- [ ] Managed identity created
- [ ] Container Apps Environment created
- [ ] Container App created
- [ ] Log Analytics workspace created

### Verify Deployment
- [ ] Docker image built and pushed to ACR
- [ ] Container app shows "Running" status
- [ ] Application URL is accessible
- [ ] Streamlit UI loads without errors

## Post-Deployment Validation

### Functional Testing
- [ ] Test with sample question from docs
- [ ] Verify intent extraction works
- [ ] Verify SQL generation works
- [ ] Verify SQL execution against database
- [ ] Verify result formatting works
- [ ] Check token usage is tracked
- [ ] Check cost estimates display correctly
- [ ] Verify .txt log file is saved
- [ ] Verify .md log file is saved

### Performance Testing
- [ ] Test with complex query
- [ ] Test with multiple concurrent users (optional)
- [ ] Verify auto-scaling works (optional)
- [ ] Check response times are acceptable

### Monitoring Setup
- [ ] View logs: `az containerapp logs show --name <app> --resource-group <rg> --follow`
- [ ] Logs are being collected in Log Analytics
- [ ] Set up Application Insights (optional)
- [ ] Create cost alerts (optional)
- [ ] Set up availability monitoring (optional)

## Security Verification

### Authentication & Authorization
- [ ] Managed identity has AcrPull role on ACR
- [ ] Container app using managed identity (not admin credentials)
- [ ] Secrets stored in Container App secrets (not environment variables)
- [ ] HTTPS enabled on ingress
- [ ] SQL connection uses secure credentials

### Network Security
- [ ] External ingress configured for public access
- [ ] SQL firewall allows Container Apps (if needed)
- [ ] No admin credentials stored in code
- [ ] Environment variables properly configured

## Optimization

### Cost Optimization
- [ ] Review replica configuration (min/max)
- [ ] Review CPU and memory allocation
- [ ] Consider consumption-only tier for dev
- [ ] Set up cost alerts
- [ ] Monitor token usage for OpenAI

### Performance Optimization
- [ ] Test query response times
- [ ] Adjust replica count if needed
- [ ] Consider increasing resources if slow
- [ ] Enable caching (if applicable)

## Documentation

### Record Information
- [ ] Note application URL: ____________________________
- [ ] Note resource group name: ____________________________
- [ ] Note ACR name: ____________________________
- [ ] Note container app name: ____________________________
- [ ] Document any customizations made
- [ ] Update team wiki/documentation

### Share Access
- [ ] Share application URL with team
- [ ] Configure authentication (if needed)
- [ ] Set up user access controls (if needed)
- [ ] Document usage instructions

## Ongoing Maintenance

### Regular Tasks
- [ ] Monitor costs weekly
- [ ] Check logs for errors
- [ ] Review Application Insights (if enabled)
- [ ] Update dependencies periodically
- [ ] Monitor Azure OpenAI quota usage

### Update Workflow
- [ ] Know how to update app: `./deploy.sh --skip-infra`
- [ ] Know how to view logs: `az containerapp logs show ...`
- [ ] Know how to scale: `az containerapp update ...`
- [ ] Know how to roll back if needed

## Troubleshooting

### If Container Won't Start
- [ ] Check logs: `az containerapp logs show --name <app> --resource-group <rg> --tail 100`
- [ ] Verify environment variables are set correctly
- [ ] Check if image exists in ACR
- [ ] Verify managed identity has proper permissions

### If Application Has Errors
- [ ] Check application logs in Container Apps
- [ ] Verify Azure OpenAI endpoint is accessible
- [ ] Verify SQL database is accessible
- [ ] Check firewall rules
- [ ] Verify model deployments exist in Azure OpenAI

### If High Costs
- [ ] Review replica count (scale down min replicas)
- [ ] Check Azure OpenAI token usage
- [ ] Review SQL database usage
- [ ] Consider lower-tier resources for dev/test

## Cleanup (If Needed)

### Remove Deployment
To delete all resources and stop incurring costs:

```bash
az group delete --name <resource-group-name> --yes --no-wait
```

- [ ] Backup any important data first
- [ ] Confirm resource group name before deleting
- [ ] Verify deletion completed
- [ ] Check billing to confirm charges stopped

## Success Criteria

Your deployment is production-ready when ALL of these are true:

- ✅ Application accessible via HTTPS URL
- ✅ All test queries execute successfully
- ✅ Logs show no errors
- ✅ Costs are within expected range
- ✅ Monitoring is configured
- ✅ Team has access and documentation
- ✅ Update process is documented
- ✅ Backup/recovery plan exists (if critical)

## Resources

- **Quick Start**: See `QUICKSTART.md`
- **Full Guide**: See `DEPLOYMENT_GUIDE.md`
- **Summary**: See `AZURE_DEPLOYMENT.md`
- **Azure Docs**: https://learn.microsoft.com/azure/container-apps/

---

**Deployment Date**: _______________

**Deployed By**: _______________

**Application URL**: _______________

**Resource Group**: _______________

**Notes**: _______________________________________________

_________________________________________________________

_________________________________________________________

---

**Status**: [ ] In Progress  [ ] Complete  [ ] Needs Review
