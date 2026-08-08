# IRIS — Task 0.5: VPC + Private Service Connect boundary.
# Enforces NFR-4: no public access to Qdrant or Firestore.

# --- VPC + subnet for the ingestion/retrieval services.
resource "google_compute_network" "iris_vpc" {
  name                    = "iris-vpc"
  project                 = var.project_id
  auto_create_subnetworks = false
}

resource "google_compute_subnetwork" "iris_subnet" {
  name          = "iris-subnet"
  project       = var.project_id
  region        = var.region
  network       = google_compute_network.iris_vpc.id
  ip_cidr_range = "10.0.0.0/20"
  private_ip_google_access = true
}

# --- Cloud Run VPC connector so services reach Qdrant VM + Firestore privately.
# Connector requires its own dedicated /28 subnet (cannot share iris-subnet).
resource "google_compute_subnetwork" "connector_subnet" {
  name          = "iris-connector-subnet"
  project       = var.project_id
  region        = var.region
  network       = google_compute_network.iris_vpc.id
  ip_cidr_range = "10.0.16.0/28"
  private_ip_google_access = true
}

resource "google_vpc_access_connector" "iris_connector" {
  name          = "iris-connector"
  project       = var.project_id
  region        = var.region
  subnet {
    name = google_compute_subnetwork.connector_subnet.name
  }
  machine_type  = "e2-micro"
  min_instances = 2
  max_instances = 10
}

# --- Firestore VPC peering (Service Networking).
resource "google_compute_global_address" "firestore_peering" {
  name          = "iris-firestore-peering"
  project       = var.project_id
  purpose       = "VPC_PEERING"
  address_type  = "INTERNAL"
  prefix_length = 16
  network       = google_compute_network.iris_vpc.id
}

resource "google_service_networking_connection" "firestore" {
  network                = google_compute_network.iris_vpc.id
  service                = "servicenetworking.googleapis.com"
  reserved_peering_ranges = [google_compute_global_address.firestore_peering.name]
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

  source_ranges = ["10.0.16.0/28"]
  target_tags   = ["qdrant"]
}

# --- Qdrant Private Service Connect endpoint.
# Phase 2.0 provisions the Qdrant VM + service attachment and attaches this
# endpoint. We reserve the address now so the boundary exists from day one.
resource "google_compute_address" "qdrant_psc" {
  name         = "iris-qdrant-psc-address"
  project      = var.project_id
  region       = var.region
  address_type = "INTERNAL"
  subnetwork   = google_compute_subnetwork.iris_subnet.id
  purpose      = "GCE_ENDPOINT"
}

# --- Cloud Router + NAT for private outbound egress (docker pull, apt updates).
resource "google_compute_router" "iris_router" {
  name    = "iris-router"
  project = var.project_id
  region  = var.region
  network = google_compute_network.iris_vpc.id
}

resource "google_compute_router_nat" "iris_nat" {
  name                               = "iris-nat"
  project                            = var.project_id
  region                             = var.region
  router                             = google_compute_router.iris_router.name
  nat_ip_allocate_option             = "AUTO_ONLY"
  source_subnetwork_ip_ranges_to_nat = "ALL_SUBNETWORKS_ALL_IP_RANGES"
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
}

