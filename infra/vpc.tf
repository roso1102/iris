# IRIS — Task 0.5: VPC + Private Service Connect boundary.
# Enforces NFR-4: no public access to Qdrant or Firestore.

# --- VPC + subnet for the ingestion/retrieval services.
resource "google_compute_network" "iris_vpc" {
  name                    = "iris-vpc"
  project                 = var.project_id
  auto_create_subnetworks = false
  depends_on              = [google_project_service.api]
}

resource "google_compute_subnetwork" "iris_subnet" {
  name                     = "iris-subnet"
  project                  = var.project_id
  region                   = var.region
  network                  = google_compute_network.iris_vpc.id
  ip_cidr_range            = "10.0.0.0/20"
  private_ip_google_access = true
  depends_on               = [google_project_service.api]
}

# --- Firewall: Qdrant HTTP API accessible from Cloud Run VPC connector only.
resource "google_compute_firewall" "qdrant_api" {
  name    = "qdrant-api"
  network = google_compute_network.iris_vpc.name
  project = var.project_id

  allow {
    protocol = "tcp"
    ports    = ["6333"]
  }

  source_ranges = ["10.0.0.0/20"]
  target_tags   = ["qdrant"]
  depends_on    = [google_project_service.api]
}

# --- Stable internal address for the Qdrant VM.
resource "google_compute_address" "qdrant_internal" {
  name         = "iris-qdrant-internal-ip"
  project      = var.project_id
  region       = var.region
  address_type = "INTERNAL"
  subnetwork   = google_compute_subnetwork.iris_subnet.id
  depends_on   = [google_project_service.api]
}

# --- Cloud Router + NAT for private outbound egress (docker pull, apt updates).
resource "google_compute_router" "iris_router" {
  name       = "iris-router"
  project    = var.project_id
  region     = var.region
  network    = google_compute_network.iris_vpc.id
  depends_on = [google_project_service.api]
}

resource "google_compute_router_nat" "iris_nat" {
  name                               = "iris-nat"
  project                            = var.project_id
  region                             = var.region
  router                             = google_compute_router.iris_router.name
  nat_ip_allocate_option             = "AUTO_ONLY"
  source_subnetwork_ip_ranges_to_nat = "ALL_SUBNETWORKS_ALL_IP_RANGES"
  depends_on                         = [google_project_service.api]
}

# --- Firewall: Allow IAP SSH access to all instances in iris-vpc (35.235.240.0/20).
resource "google_compute_firewall" "allow_iap_ssh" {
  name    = "allow-iap-ssh"
  network = google_compute_network.iris_vpc.name
  project = var.project_id

  allow {
    protocol = "tcp"
    ports    = ["22"]
  }

  source_ranges = ["35.235.240.0/20"]
  target_tags   = ["qdrant"]
  depends_on    = [google_project_service.api]
}
