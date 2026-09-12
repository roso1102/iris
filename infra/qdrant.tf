# IRIS — Phase 1.0 Integration Testing: minimal Qdrant GCE VM.
# Upgraded to full production shape in Phase 2.0 (Task 2.1–2.2).

resource "google_compute_instance" "qdrant_vm" {
  name                = "qdrant-1"
  machine_type        = "e2-small"
  zone                = "${var.region}-b"
  project             = var.project_id
  deletion_protection = true
  depends_on          = [google_project_service.api]

  tags = ["qdrant"]

  boot_disk {
    initialize_params {
      # Disposable staging VM: keep the OS disk small and inexpensive.
      size  = 10
      type  = "pd-standard"
      image = "ubuntu-os-cloud/ubuntu-2204-lts"
    }
  }

  attached_disk {
    source      = google_compute_disk.qdrant_data.id
    device_name = "qdrant-data"
    mode        = "READ_WRITE"
  }

  network_interface {
    network    = google_compute_network.iris_vpc.id
    subnetwork = google_compute_subnetwork.iris_subnet.id
    network_ip = google_compute_address.qdrant_internal.address
    # No access_config block = no public IP; the VM is internal-only.
  }

  metadata_startup_script = <<-EOT
    #!/bin/bash
    set -euo pipefail
    DATA_DISK=/dev/disk/by-id/google-qdrant-data
    until test -b "$DATA_DISK"; do sleep 2; done
    if ! blkid "$DATA_DISK" >/dev/null 2>&1; then mkfs.ext4 -F "$DATA_DISK"; fi
    mkdir -p /data/qdrant
    UUID=$(blkid -s UUID -o value "$DATA_DISK")
    grep -q "$UUID" /etc/fstab || echo "UUID=$UUID /data/qdrant ext4 discard,defaults,nofail 0 2" >> /etc/fstab
    mount -a
    apt-get update && apt-get install -y docker.io
    docker run -d --restart=unless-stopped \
      -p 6333:6333 \
      -v /data/qdrant:/qdrant/storage \
      qdrant/qdrant:v1.13.0
  EOT

  service_account {
    email = google_service_account.qdrant_vm.email
    scopes = [
      "https://www.googleapis.com/auth/logging.write",
      "https://www.googleapis.com/auth/monitoring.write",
    ]
  }
}

resource "google_compute_disk" "qdrant_data" {
  name    = "qdrant-data"
  project = var.project_id
  zone    = "${var.region}-b"
  type    = "pd-balanced"
  # The test corpus is small; grow this disk when utilization approaches 70%.
  size                      = 10
  physical_block_size_bytes = 4096
  depends_on                = [google_project_service.api]

  lifecycle {
    prevent_destroy = true
  }
}
