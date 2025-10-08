// ============================================================================
// Azure Container Apps Infrastructure for NL2SQL Multi-Model App
// ============================================================================
// This Bicep template deploys a complete infrastructure for the NL2SQL app:
// - Azure Container Registry (ACR) for storing Docker images
// - User-assigned Managed Identity for secure authentication
// - Container Apps Environment (isolated network boundary)
// - Container App running the Streamlit multi-model UI
// - Role assignments for managed identity to pull from ACR
// ============================================================================

targetScope = 'resourceGroup'

// ============================================================================
// Parameters
// ============================================================================

@description('Base name for all resources (will be used to generate unique names)')
param projectName string = 'nl2sql'

@description('Azure region for deployment')
param location string = resourceGroup().location

@description('Environment name (dev, staging, prod)')
@allowed([
  'dev'
  'staging'
  'prod'
])
param environment string = 'dev'

@description('Container image name')
param imageName string = 'nl2sql-multimodel'

@description('Container image tag')
param imageTag string = 'latest'

@description('Azure OpenAI API Key')
@secure()
param azureOpenAiApiKey string

@description('Azure OpenAI Endpoint')
param azureOpenAiEndpoint string

@description('Azure OpenAI API Version')
param azureOpenAiApiVersion string = '2025-04-01-preview'

@description('Azure SQL Server hostname')
param azureSqlServer string

@description('Azure SQL Database name')
param azureSqlDatabase string

@description('Azure SQL Username')
param azureSqlUser string

@description('Azure SQL Password')
@secure()
param azureSqlPassword string

@description('Minimum number of replicas')
@minValue(0)
@maxValue(10)
param minReplicas int = 1

@description('Maximum number of replicas')
@minValue(1)
@maxValue(30)
param maxReplicas int = 3

@description('CPU cores per container (0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 1.75, 2.0)')
param cpuCores string = '1.0'

@description('Memory in GB per container (0.5, 1.0, 1.5, 2.0, 3.0, 4.0)')
param memorySize string = '2.0Gi'

// ============================================================================
// Variables
// ============================================================================

var resourceSuffix = uniqueString(resourceGroup().id)
var acrName = 'acr${projectName}${resourceSuffix}'
var containerAppEnvName = '${projectName}-env-${environment}'
var containerAppName = '${projectName}-app-${environment}'
var userIdentityName = '${projectName}-identity-${environment}'
var logAnalyticsWorkspaceName = '${projectName}-logs-${environment}'

// Tags for resource management
var tags = {
  Environment: environment
  Project: projectName
  ManagedBy: 'Bicep'
  Application: 'NL2SQL-MultiModel'
}

// ============================================================================
// Log Analytics Workspace (required for Container Apps)
// ============================================================================

resource logAnalyticsWorkspace 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: logAnalyticsWorkspaceName
  location: location
  tags: tags
  properties: {
    sku: {
      name: 'PerGB2018'
    }
    retentionInDays: 30
    features: {
      enableLogAccessUsingOnlyResourcePermissions: true
    }
  }
}

// ============================================================================
// Azure Container Registry
// ============================================================================

resource containerRegistry 'Microsoft.ContainerRegistry/registries@2023-07-01' = {
  name: acrName
  location: location
  tags: tags
  sku: {
    name: 'Basic'
  }
  properties: {
    adminUserEnabled: false // Use managed identity instead
    publicNetworkAccess: 'Enabled'
    zoneRedundancy: 'Disabled'
  }
}

// ============================================================================
// User-Assigned Managed Identity
// ============================================================================

resource userIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: userIdentityName
  location: location
  tags: tags
}

// ============================================================================
// Role Assignment: Grant Managed Identity AcrPull access to ACR
// ============================================================================

resource acrPullRoleDefinition 'Microsoft.Authorization/roleDefinitions@2022-04-01' existing = {
  scope: subscription()
  name: '7f951dda-4ed3-4680-a7ca-43fe172d538d' // AcrPull role ID
}

resource acrPullRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: containerRegistry
  name: guid(containerRegistry.id, userIdentity.id, acrPullRoleDefinition.id)
  properties: {
    roleDefinitionId: acrPullRoleDefinition.id
    principalId: userIdentity.properties.principalId
    principalType: 'ServicePrincipal'
  }
}

// ============================================================================
// Container Apps Environment
// ============================================================================

resource containerAppEnvironment 'Microsoft.App/managedEnvironments@2024-03-01' = {
  name: containerAppEnvName
  location: location
  tags: tags
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: logAnalyticsWorkspace.properties.customerId
        sharedKey: logAnalyticsWorkspace.listKeys().primarySharedKey
      }
    }
    zoneRedundant: false
  }
}

// ============================================================================
// Container App - NL2SQL Multi-Model Streamlit App
// ============================================================================

resource containerApp 'Microsoft.App/containerApps@2024-03-01' = {
  name: containerAppName
  location: location
  tags: tags
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${userIdentity.id}': {}
    }
  }
  properties: {
    environmentId: containerAppEnvironment.id
    configuration: {
      ingress: {
        external: true
        targetPort: 8501
        transport: 'auto'
        allowInsecure: false
        traffic: [
          {
            latestRevision: true
            weight: 100
          }
        ]
      }
      registries: [
        {
          server: containerRegistry.properties.loginServer
          identity: userIdentity.id
        }
      ]
      secrets: [
        {
          name: 'azure-openai-api-key'
          value: azureOpenAiApiKey
        }
        {
          name: 'azure-sql-password'
          value: azureSqlPassword
        }
      ]
    }
    template: {
      containers: [
        {
          name: containerAppName
          image: '${containerRegistry.properties.loginServer}/${imageName}:${imageTag}'
          resources: {
            cpu: json(cpuCores)
            memory: memorySize
          }
          env: [
            {
              name: 'AZURE_OPENAI_API_KEY'
              secretRef: 'azure-openai-api-key'
            }
            {
              name: 'AZURE_OPENAI_ENDPOINT'
              value: azureOpenAiEndpoint
            }
            {
              name: 'AZURE_OPENAI_API_VERSION'
              value: azureOpenAiApiVersion
            }
            {
              name: 'AZURE_SQL_SERVER'
              value: azureSqlServer
            }
            {
              name: 'AZURE_SQL_DB'
              value: azureSqlDatabase
            }
            {
              name: 'AZURE_SQL_USER'
              value: azureSqlUser
            }
            {
              name: 'AZURE_SQL_PASSWORD'
              secretRef: 'azure-sql-password'
            }
            {
              name: 'PYTHONUNBUFFERED'
              value: '1'
            }
          ]
        }
      ]
      scale: {
        minReplicas: minReplicas
        maxReplicas: maxReplicas
        rules: [
          {
            name: 'http-scaling'
            http: {
              metadata: {
                concurrentRequests: '10'
              }
            }
          }
        ]
      }
    }
  }
  dependsOn: [
    acrPullRoleAssignment
  ]
}

// ============================================================================
// Outputs
// ============================================================================

@description('The URL of the deployed Container App')
output containerAppUrl string = 'https://${containerApp.properties.configuration.ingress.fqdn}'

@description('The name of the Container Registry')
output containerRegistryName string = containerRegistry.name

@description('The login server of the Container Registry')
output containerRegistryLoginServer string = containerRegistry.properties.loginServer

@description('The resource ID of the user-assigned managed identity')
output userIdentityId string = userIdentity.id

@description('The client ID of the user-assigned managed identity')
output userIdentityClientId string = userIdentity.properties.clientId

@description('The principal ID of the user-assigned managed identity')
output userIdentityPrincipalId string = userIdentity.properties.principalId

@description('The name of the Container App')
output containerAppName string = containerApp.name

@description('The name of the Container Apps Environment')
output containerAppEnvironmentName string = containerAppEnvironment.name

@description('The name of the Log Analytics Workspace')
output logAnalyticsWorkspaceName string = logAnalyticsWorkspace.name
