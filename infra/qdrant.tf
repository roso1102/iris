# IRIS — Phase 1.0 Integration Testing: minimal Qdrant GCE VM.
# Upgraded to full production shape in Phase 2.0 (Task 2.1–2.2).

resource "google_compute_instance" "qdrant_vm" {
  name         = "qdrant-1"
  machine_type = "e2-small"
  zone         = "${var.region}-b"
  project      = var.project_id

  tags = ["qdrant"]

  boot_disk {
    initialize_params {
      size  = 20
      image = "ubuntu-os-cloud/ubuntu-2204-lts"
    }
  }

  network_interface {
    network    = google_compute_network.iris_vpc.id
    subnetwork = google_compute_subnetwork.iris_subnet.id
    # No access_config block = no public IP — internal only, reached via VPC connector.
  }

  metadata_startup_script = <<-EOT
    #!/bin/bash
    apt-get update && apt-get install -y docker.io
    docker run -d --restart=unless-stopped \
      -p 6333:6333 \
      -v /data/qdrant:/qdrant/storage \
      qdrant/qdrant:v1.13.0
  EOT

  service_account {
    scopes = ["cloud-platform"]
  }
}
