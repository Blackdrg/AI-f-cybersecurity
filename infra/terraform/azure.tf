# Azure Government/Multi-cloud Infrastructure for AI-f
# Azure deployment supporting sovereign cloud requirements including Azure Government

variable "resource_group_name" {
  description = "Resource group name"
  type        = string
  default     = "ai-f-rg"
}

variable "location" {
  description = "Azure region"
  type        = string
  default     = "East US"
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "production"
}

provider "azurerm" {
  features {}
}

# Create Resource Group
resource "azurerm_resource_group" "main" {
  name     = var.resource_group_name
  location = var.location
}

# Virtual Network
resource "azurerm_virtual_network" "main" {
  name                = "ai-f-vnet"
  address_space       = ["10.0.0.0/16"]
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
}

resource "azurerm_subnet" "backend" {
  name                 = "ai-f-backend"
  resource_group_name  = azurerm_resource_group.main.name
  virtual_network_name = azurerm_virtual_network.main.name
  address_prefixes     = ["10.0.1.0/24"]
  service_endpoints    = ["Microsoft.Sql", "Microsoft.Storage"]
}

resource "azurerm_subnet" "aks" {
  name                 = "ai-f-aks"
  resource_group_name  = azurerm_resource_group.main.name
  virtual_network_name = azurerm_virtual_network.main.name
  address_prefixes     = ["10.0.2.0/24"]
}

# Network Security Group
resource "azurerm_network_security_group" "main" {
  name                = "ai-f-nsg"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  
  security_rule {
    name                       = "AllowHTTPS"
    priority                   = 1000
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "443"
    source_address_prefix      = "Internet"
    destination_address_prefix = "*"
  }
}

# PostgreSQL Server
resource "azurerm_postgresql_flexible_server" "main" {
  name                   = "ai-f-postgres"
  resource_group_name    = azurerm_resource_group.main.name
  location               = azurerm_resource_group.main.location
  version                = "15"
  administrator_login    = "ai_f_admin"
  administrator_password = var.db_password
  
  storage_mb   = 32768
  sku_name     = "GP_Standard_D2s_v3"
  
  high_availability {
    mode = "ZoneRedundant"
  }
  
  identity {
    type = "SystemAssigned"
  }
}

resource "azurerm_postgresql_flexible_server_firewall_rule" "allow_azure" {
  name                = "AllowAzure"
  resource_group_name = azurerm_resource_group.main.name
  server_name         = azurerm_postgresql_flexible_server.main.name
  start_ip_address    = "0.0.0.0"
  end_ip_address      = "0.0.0.0"
}

# Redis Cache
resource "azurerm_redis_cache" "main" {
  name                = "ai-f-redis"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  capacity            = 1
  family              = "C"
  sku_name            = "Standard"
  enable_non_ssl_port = false
  
  redis_configuration {
    maxmemory_policy = "allkeys-lru"
  }
}

# AKS Cluster
resource "azurerm_kubernetes_cluster" "main" {
  name                = "ai-f-aks"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  dns_prefix          = "ai-f-aks"
  kubernetes_version  = "1.29"
  
  default_node_pool {
    name                = "default"
    node_count          = 2
    vm_size             = "Standard_D2s_v3"
    vnet_subnet_id      = azurerm_subnet.aks.id
    zones               = ["1", "2", "3"]
    
    upgrade_settings {
      max_surge = "33%"
    }
  }
  
  identity {
    type = "SystemAssigned"
  }
  
  network_profile {
    network_plugin = "azure"
    service_cidr   = "10.100.0.0/16"
    dns_service_ip = "10.100.0.10"
  }
  
  oms_agent {
    log_analytics_workspace_id = azurerm_log_analytics_workspace.main.id
  }
  
  key_vault_secrets_provider {
    secret_rotation_enabled = true
  }
}

# Log Analytics
resource "azurerm_log_analytics_workspace" "main" {
  name                = "ai-f-logs"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  sku                 = "PerGB2018"
  retention_in_days   = 30
}

# Key Vault for secrets
resource "azurerm_key_vault" "main" {
  name                        = "ai-f-kv"
  location                    = azurerm_resource_group.main.location
  resource_group_name         = azurerm_resource_group.main.name
  tenant_id                   = data.azurerm_client_config.current.tenant_id
  sku_name                    = "standard"
  purge_protection_enabled    = true
  soft_delete_retention_days  = 7
  
  network_acls {
    default_action = "Deny"
    bypass         = "AzureServices"
  }
}

data "azurerm_client_config" "current" {}

# Storage Account for model weights
resource "azurerm_storage_account" "models" {
  name                     = "aifmodels"
  resource_group_name      = azurerm_resource_group.main.name
  location                 = azurerm_resource_group.main.location
  account_tier             = "Standard"
  account_replication_type = "GRS"
  
  identity {
    type = "SystemAssigned"
  }
  
  blob_properties {
    delete_retention_policy {
      days = 30
    }
  }
}

resource "azurerm_storage_container" "models" {
  name                  = "models"
  storage_account_name  = azurerm_storage_account.models.name
  container_access_type = "private"
}

# Application Gateway for global traffic routing
resource "azurerm_application_gateway" "main" {
  name                = "ai-f-appgw"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  
  sku {
    name     = "WAF_v2"
    tier     = "WAF_v2"
    capacity = 2
  }
  
  gateway_ip_configuration {
    name      = "appgw-ip-config"
    subnet_id = azurerm_subnet.backend.id
  }
  
  frontend_ip_configuration {
    name                 = "appgw-frontend-ip"
    public_ip_address_id = azurerm_public_ip.main.id
  }
  
  frontend_port {
    name = "https"
    port = 443
  }
  
  ssl_certificate {
    name                = "ssl-cert"
    key_vault_secret_id = azurerm_key_vault_certificate.ssl.id
  }
  
  backend_http_settings {
    name                  = "backend"
    cookie_based_affinity = "Disabled"
    port                  = 80
    protocol              = "Http"
    request_timeout       = 30
  }
  
  http_listener {
    name                           = "https"
    frontend_ip_configuration_name = "appgw-frontend-ip"
    frontend_port_name             = "https"
    protocol                       = "Https"
    ssl_certificate_name           = "ssl-cert"
  }
  
  request_routing_rule {
    name                       = "routing"
    rule_type                  = "PathBasedRouting"
    http_listener_name         = "https"
    url_path_map_name          = "pathmap"
    priority                   = 10
  }
}

resource "azurerm_public_ip" "main" {
  name                = "ai-f-pip"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  allocation_method   = "Static"
  sku                 = "Standard"
}

# Key Vault Certificate (for SSL termination)
resource "azurerm_key_vault_certificate" "ssl" {
  name         = "ssl-cert"
  key_vault_id = azurerm_key_vault.main.id
  
  certificate_policy {
    issuer_parameters {
      name = "Self"
    }
    
    key_properties {
      key_size   = 2048
      key_type   = "RSA"
      reuse_key  = true
    }
    
    secret_properties {
      content_type = "application/x-pkcs12"
    }
    
    x509_certificate_properties {
      key_usage = [
        "digitalSignature",
        "keyEncipherment"
      ]
      
      subject            = "CN=ai-f.example.com"
      validity_in_months = 12
    }
  }
}

# Output values
output "aks_kube_config" {
  value = azurerm_kubernetes_cluster.main.kube_config_raw
  sensitive = true
}

output "database_fqdn" {
  value = azurerm_postgresql_flexible_server.main.fully_qualified_domain_name
}

output "redis_hostname" {
  value = azurerm_redis_cache.main.hostname
}

output "storage_account_name" {
  value = azurerm_storage_account.models.name
}