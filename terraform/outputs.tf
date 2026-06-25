output "public_ip" {
  value = oci_core_instance.app.public_ip
}

output "app_url" {
  value = "http://${oci_core_instance.app.public_ip}:8000"
}
