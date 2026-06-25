# Deploying LLMController to Oracle Cloud (Always Free)

Forever-free public deployment on a single Oracle Cloud VM running the app +
Postgres + Redis via Docker Compose, provisioned with Terraform.

## Prerequisites (one-time)

1. **Oracle Cloud account** — https://signup.cloud.oracle.com (needs a card for
   identity verification; Always-Free resources are never charged).
2. **OCI CLI** — `brew install oci-cli`, then `oci setup config`
   (creates `~/.oci/config` with your tenancy/user OCID, API key, region).
   Upload the generated public key in the OCI console: Profile → API Keys.
3. **Terraform** — `brew install terraform`.
4. **An SSH key** — `ssh-keygen -t ed25519` if you don't have one.

## Deploy

```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars: region, compartment_ocid (tenancy OCID is fine),
# ssh_public_key (contents of ~/.ssh/id_ed25519.pub), anthropic_api_key, admin_token

terraform init
terraform plan
terraform apply        # type "yes"
```

When it finishes, Terraform prints:

```
app_url   = "http://<public-ip>:8000"
public_ip = "<public-ip>"
```

The VM's cloud-init installs Docker, clones the repo, writes `.env`, and runs
`docker compose -f docker-compose.prod.yml up -d --build`. First boot takes
**3-5 minutes** to build the image and run migrations.

## Verify

```bash
curl http://<public-ip>:8000/health           # {"status":"healthy"}
open http://<public-ip>:8000/                  # the chat UI
```

In the UI: expand "Generate a key (admin)", paste your `admin_token`, click
Generate, then send a message.

## Capacity note

`VM.Standard.A1.Flex` (ARM, the generous free shape) is sometimes "out of
capacity" in busy regions. If `apply` fails with that error, either retry, pick
a different region, or fall back to the always-available AMD micro shape in
`terraform.tfvars`:

```hcl
instance_shape      = "VM.Standard.E2.1.Micro"
instance_ocpus      = 1
instance_memory_gbs = 1
```

(1 GB RAM is tight with Postgres+Redis+app; A1 is strongly preferred.)

## TLS (optional, later)

The base deploy serves plain HTTP on :8000. For HTTPS, add Caddy as a reverse
proxy with a free domain — Caddy auto-provisions Let's Encrypt certs.

## Tear down

```bash
terraform destroy
```
