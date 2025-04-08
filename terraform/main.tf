terraform {
  required_providers {
    yandex = {
      source = "yandex-cloud/yandex"
    }
  }
  required_version = ">= 0.13"
}

provider "yandex" {
  zone = "ru-central1-d"
}

resource "yandex_container_registry" "my-reg" {
  name = "project-registry"
  folder_id = "b1gr31hq6bsesq941vg8"
}

resource "yandex_mdb_postgresql_cluster" "project-cluster" {
  name                = "project-cluster-db"
  environment         = "PRODUCTION"
  network_id          = "enp8csulc2l7e6mp6o74"

  config {
    version = "15"
    resources {
      resource_preset_id = "s1.micro"
      disk_type_id       = "network-ssd"
      disk_size          = 50
    }
    pooler_config {
      pool_discard = true
      pooling_mode = "SESSION"
    }
  }

  host {
    zone             = "ru-central1-d"
    name             = "project-db-host"
    subnet_id        = "fl8ibp8ekoutoojp7hf3"
    assign_public_ip = true
  }
}

resource "yandex_mdb_postgresql_database" "db1" {
  cluster_id = yandex_mdb_postgresql_cluster.project-cluster.id
  name       = "db1"
  owner      = "admin"
}

resource "yandex_mdb_postgresql_user" "admin" {
  cluster_id = yandex_mdb_postgresql_cluster.project-cluster.id
  name       = "admin"
  password   = "123456"
}

resource "yandex_vpc_network" "dev-stock-market-network" { name = "dev-stock-market-network" }

resource "yandex_vpc_subnet" "dev-stock-market-network-ru-central1-d" {
  name           = "dev-stock-market-network-ru-central1-d"
  zone           = "ru-central1-d"
  network_id     = "enp8csulc2l7e6mp6o74"
  v4_cidr_blocks = ["0.0.0.0/0"]
}

