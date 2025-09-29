# Deployment Guide

This guide describes how to deploy the FastAPI threat intelligence platform to Azure using the cost-efficient architecture outlined in `architecture.md`. The steps assume Azure CLI 2.50+ and Python 3.11+ on your workstation.

## 1. Prerequisites

1. Azure subscription with permissions to create resource groups, App Service, PostgreSQL Flexible Server, Storage Accounts, and Azure OpenAI resources.
2. Azure OpenAI access approved in the target tenant.
3. Microsoft Entra ID app registration with the following configuration:
   - Application type: **Web**.
   - Redirect URIs: `https://<app-service-name>.azurewebsites.net/docs/oauth2-redirect` and any UI origins.
   - App roles: `admin`, `analyst`, `integration` (string values matching `UserRole`).
   - Optional: assign Azure AD groups to these roles.
4. Docker (for local container builds) if you plan to use container-based deployment.
5. Poetry or pip to install dependencies for local validation (`python -m compileall app`).

## 2. Prepare Azure Resources

```bash
# Variables
RESOURCE_GROUP=ti-platform-rg
LOCATION=eastus
APP_SERVICE_PLAN=ti-plan
WEBAPP_NAME=ti-platform-api
POSTGRES_NAME=tipgsql
STORAGE_NAME=tipstorage$RANDOM
LOG_ANALYTICS=tilogs
OPENAI_NAME=ti-openai
OPENAI_SKU=gpt-4o-mini
```

1. **Create resource group**

```bash
az group create --name $RESOURCE_GROUP --location $LOCATION
```

2. **Provision PostgreSQL Flexible Server (B1ms)**

```bash
az postgres flexible-server create \
  --resource-group $RESOURCE_GROUP \
  --name $POSTGRES_NAME \
  --location $LOCATION \
  --sku-name Standard_B1ms \
  --storage-size 32 \
  --tier Burstable \
  --version 15 \
  --admin-user tiadmin \
  --admin-password <StrongPassword> \
  --public-access 0.0.0.0 \
  --storage-auto-grow Disabled
```

> For production lock down networking using VNET integration or firewall rules.

3. **Create Azure Storage account**

```bash
az storage account create \
  --name $STORAGE_NAME \
  --resource-group $RESOURCE_GROUP \
  --location $LOCATION \
  --sku Standard_LRS \
  --kind StorageV2
```

4. **Create Log Analytics workspace (optional but recommended)**

```bash
az monitor log-analytics workspace create \
  --resource-group $RESOURCE_GROUP \
  --workspace-name $LOG_ANALYTICS \
  --location $LOCATION
```

5. **Create Azure App Service plan and Web App**

```bash
az appservice plan create \
  --name $APP_SERVICE_PLAN \
  --resource-group $RESOURCE_GROUP \
  --location $LOCATION \
  --is-linux \
  --sku B1

az webapp create \
  --name $WEBAPP_NAME \
  --plan $APP_SERVICE_PLAN \
  --resource-group $RESOURCE_GROUP \
  --runtime "PYTHON|3.11"
```

6. **Enable Always On and configure logging**

```bash
az webapp config set \
  --name $WEBAPP_NAME \
  --resource-group $RESOURCE_GROUP \
  --always-on true

az webapp log config \
  --name $WEBAPP_NAME \
  --resource-group $RESOURCE_GROUP \
  --application-logging filesystem \
  --level information
```

7. **Provision Azure OpenAI (if not already created)**

```bash
az cognitiveservices account create \
  --name $OPENAI_NAME \
  --resource-group $RESOURCE_GROUP \
  --location $LOCATION \
  --kind OpenAI \
  --sku S0 \
  --yes
```

Create a deployment for GPT-4 Turbo or GPT-4o Mini via the Azure portal or CLI after approval.

## 3. Configure Application Settings

Collect connection strings and secrets:

- PostgreSQL connection string: `postgresql+asyncpg://tiadmin:<password>@<host>:5432/postgres`
- Storage account connection string for Blob container (optional if using SAS tokens).
- Azure OpenAI endpoint and API key.
- Entra ID tenant ID, application (client) ID, and allowed audience/client ID for API validation.

```bash
az webapp config appsettings set --resource-group $RESOURCE_GROUP --name $WEBAPP_NAME --settings \
  APP_NAME="Threat Intel Platform" \
  API_V1_PREFIX="/api/v1" \
  DATABASE_URL="postgresql+asyncpg://tiadmin:<password>@<host>:5432/postgres" \
  TENANT_ID="<tenant-id>" \
  CLIENT_ID="<app-client-id>" \
  ALLOWED_AUDIENCES="<app-client-id>" \
  AUTHORITY_HOST="https://login.microsoftonline.com" \
  JWKS_CACHE_TTL="3600" \
  SCHEDULER_TIMEZONE="UTC" \
  INGESTION_INTERVAL_MINUTES="60" \
  RETENTION_DAYS="31" \
  OPENAI_ENDPOINT="https://$OPENAI_NAME.openai.azure.com/" \
  OPENAI_API_KEY="<openai-key>" \
  STORAGE_ACCOUNT_URL="https://$STORAGE_NAME.blob.core.windows.net" \
  STORAGE_SAS_TOKEN="<optional-sas-token>"
```

Use Azure Key Vault for secrets in production and reference them via `@Microsoft.KeyVault(...)` syntax.

## 4. Build and Deploy

### Option A – Zip Deploy from source

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r <(poetry export --without-hashes)
python -m compileall app  # optional validation
zip -r deploy.zip app docs pyproject.toml README.md
az webapp deploy --resource-group $RESOURCE_GROUP --name $WEBAPP_NAME --src-path deploy.zip
```

### Option B – Container Deploy

1. Create an Azure Container Registry or use Docker Hub.
2. Build and push image:

```bash
docker build -t <registry>/<repo>/ti-platform:latest .
docker push <registry>/<repo>/ti-platform:latest
```

3. Configure Web App for container:

```bash
az webapp config container set \
  --name $WEBAPP_NAME \
  --resource-group $RESOURCE_GROUP \
  --docker-custom-image-name <registry>/<repo>/ti-platform:latest \
  --docker-registry-server-url https://<registry>
```

4. Restart the app to apply settings:

```bash
az webapp restart --name $WEBAPP_NAME --resource-group $RESOURCE_GROUP
```

## 5. Database Initialization

The application automatically creates tables on startup. To run migrations manually in future, integrate Alembic and execute migrations via a GitHub Actions workflow or Azure CLI.

For initial data (e.g., seed feeds), use the API or connect with `psql`:

```bash
psql "host=<host> dbname=postgres user=tiadmin password=<password> sslmode=require"
```

## 6. Post-Deployment Tasks

1. **Assign Roles** – In Azure AD, grant users/applications the `admin`, `analyst`, or `integration` app roles. Analysts automatically provisioned on first sign-in default to `analyst` role; adjust via `/api/v1/users` (admin only).
2. **Configure Entra ID Authentication** – Enable App Service Authentication (Easy Auth) if you prefer Azure-managed token validation for the UI. The API still validates JWTs using `app/services/auth.py`.
3. **Create Blob Containers** – Example: `intel-pdfs` for newsletters and `reference-data` for ATT&CK/CVE snapshots.
4. **Set Up Monitoring** – Connect the Web App to Application Insights (`az monitor app-insights component connect-webapp`) and configure alerts for HTTP 5xx errors or scheduler failures.
5. **Backup & Retention** – Ensure PostgreSQL automated backups meet policy. Consider exporting newsletters before retention jobs prune data older than 31 days.

## 7. Rolling Updates and CI/CD

- Use GitHub Actions or Azure DevOps pipelines with `azure/webapps-deploy` action to automate deployments.
- Run unit or integration tests (`python -m compileall app` or custom suites) before deploying.
- Use deployment slots (Standard tier and above) for zero-downtime releases. For B1 keep manual rollback strategy by redeploying previous artifact.

## 8. Troubleshooting Checklist

| Symptom | Resolution |
| --- | --- |
| HTTP 500 on API calls | Check App Service logs (`az webapp log tail`). Ensure DB firewall allows App Service outbound IPs. |
| OAuth failures | Verify Entra ID app roles and update `CLIENT_ID`, `ALLOWED_AUDIENCES`, `TENANT_ID`. Confirm tokens include roles. |
| Scheduler not running | Confirm Always On is enabled. Review application logs for APScheduler startup errors. |
| Feed ingestion slow | Reduce `INGESTION_INTERVAL_MINUTES` temporarily, monitor CPU. Scale up App Service if necessary. |
| GPT calls failing | Ensure Azure OpenAI deployment name matches environment variables and that quota is not exhausted. |

With these steps the platform should be online in under an hour while keeping monthly spend near the $45 estimate.
