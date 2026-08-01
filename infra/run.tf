# IRIS — Cloud Run service definitions (Phase 0.8).
#
# NOTE: these services are created by scripts/deploy.sh AFTER building the
# container images (Cloud Run requires the image to exist at deploy time),
# so they are NOT created by `terraform apply`. deploy.sh uses `gcloud run
# deploy` with the same spec (region, SA, VPC connector, scaling) so the
# IAM bindings below match what the CLI creates.
#
# The IAM bindings (kill-switch run.admin, trigger run.invoker) are applied by
# deploy.sh too, via --service-account flags + gcloud run services add-iam-policy-binding.

# (Services are intentionally not defined as Terraform resources here to
#  avoid the chicken-and-egg problem of images not existing at apply time.)
