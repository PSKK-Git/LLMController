variable "region" {
  description = "OCI region, e.g. eu-frankfurt-1"
  type        = string
}

variable "compartment_ocid" {
  description = "Compartment OCID to deploy into (often your tenancy/root OCID)"
  type        = string
}

variable "ssh_public_key" {
  description = "SSH public key contents for the VM 'opc' user"
  type        = string
}

variable "anthropic_api_key" {
  description = "Anthropic API key injected into the app's .env"
  type        = string
  sensitive   = true
}

variable "admin_token" {
  description = "Admin token for /admin endpoints"
  type        = string
  sensitive   = true
  default     = "change-me-admin-token"
}

variable "repo_url" {
  description = "Public git repo the VM clones to build the app"
  type        = string
  default     = "https://github.com/PSKK-Git/LLMController"
}

# Always-Free defaults. A1.Flex (ARM) is the most generous free shape.
variable "instance_shape" {
  type    = string
  default = "VM.Standard.A1.Flex"
}

variable "instance_ocpus" {
  type    = number
  default = 2
}

variable "instance_memory_gbs" {
  type    = number
  default = 12
}
