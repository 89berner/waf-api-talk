### VARIABLES ###
variable "project_name" {}

provider "google" {
  project = "${var.project_name}"
  region  = "europe-west1"
}

### PUBSUB ###

resource "google_pubsub_topic" "enriched_events_topic" {
  name = "enriched_events"
}

resource "google_pubsub_subscription" "enriched-events" {
  name  = "logstash-sub"
  topic = "enriched_events"

  ack_deadline_seconds = 10
  depends_on = ["google_pubsub_topic.enriched_events_topic"]
}

resource "google_pubsub_topic" "raw_events_topic" {
  name = "raw_events"
}

resource "google_pubsub_subscription" "raw-events" {
  name  = "beam-sub"
  topic = "raw_events"

  ack_deadline_seconds = 10
  depends_on = ["google_pubsub_topic.raw_events_topic"]
}

resource "google_pubsub_topic" "waf_alerts_topic" {
  name = "waf_alerts"
}

resource "google_pubsub_subscription" "waf-alerts" {
  name  = "waf-alerts-sub"
  topic = "waf_alerts"

  ack_deadline_seconds = 10
  depends_on = ["google_pubsub_topic.waf_alerts_topic"]
}

### GKE ###
resource "google_container_cluster" "primary" {
  name = "cluster-waf-api-talk"
  zone = "europe-west1-b"
  initial_node_count = 3

  node_config {
    oauth_scopes = [
      "https://www.googleapis.com/auth/compute",
      "https://www.googleapis.com/auth/devstorage.read_only",
      "https://www.googleapis.com/auth/logging.write",
      "https://www.googleapis.com/auth/monitoring",
    ]
  }

  addons_config {
    kubernetes_dashboard {
      disabled = true
    }
  }
}

### BIGQUERY ###
resource "google_bigquery_dataset" "default" {
  dataset_id                  = "raw_dataset"
  friendly_name               = "raw-dataset"
  description                 = "Raw data dataset"

  labels {
    env = "default"
  }
}