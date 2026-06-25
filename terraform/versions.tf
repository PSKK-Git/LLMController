terraform {
  required_version = ">= 1.5"
  required_providers {
    oci = {
      source  = "oracle/oci"
      version = ">= 5.0"
    }
  }
}

# Auth comes from ~/.oci/config (run `oci setup config`).
provider "oci" {
  region = var.region
}
