terraform {
  required_providers {
    yandex = {
      source = "yandex-cloud/yandex"
    }
  }
  required_version = ">= 0.13"
}

provider "yandex" {
  token     = var.yc_token
  cloud_id  = var.cloud_id
  folder_id = var.folder_id
}

resource "yandex_vpc_network" "main" {
  name = "main-network"
}

resource "yandex_vpc_subnet" "subnet-a" {
  name           = "subnet-a"
  zone           = "ru-central1-a"
  network_id     = yandex_vpc_network.main.id
  v4_cidr_blocks = ["10.0.1.0/24"]
}

resource "yandex_vpc_subnet" "subnet-b" {
  name           = "subnet-b"
  zone           = "ru-central1-b"
  network_id     = yandex_vpc_network.main.id
  v4_cidr_blocks = ["10.0.2.0/24"]
}

resource "yandex_vpc_subnet" "subnet-d" {
  name           = "subnet-d"
  zone           = "ru-central1-d"
  network_id     = yandex_vpc_network.main.id
  v4_cidr_blocks = ["10.0.3.0/24"]
}

resource "yandex_mdb_postgresql_cluster" "pg_cluster" {
  name        = "my-pg-cluster"
  environment = "PRODUCTION"
  network_id  = yandex_vpc_network.main.id

  config {
    version = "14"
    resources {
      resource_preset_id = "s2.micro"
      disk_size          = 30
      disk_type_id       = "network-ssd"
    }
  }

  host {
    zone      = "ru-central1-a"
    subnet_id = yandex_vpc_subnet.subnet-a.id
  }

  host {
    zone      = "ru-central1-b"
    subnet_id = yandex_vpc_subnet.subnet-b.id
  }

  host {
    zone      = "ru-central1-d"
    subnet_id = yandex_vpc_subnet.subnet-d.id
  }
}

resource "yandex_mdb_postgresql_database" "market-db" {
  cluster_id = yandex_mdb_postgresql_cluster.pg_cluster.id
  name       = "marketdb"
  owner      = "admin"
}

resource "yandex_mdb_postgresql_user" "admin" {
  cluster_id = yandex_mdb_postgresql_cluster.pg_cluster.id
  name       = "admin"
  password   = var.db_password
}

data "yandex_compute_image" "ubuntu" {
  family = "ubuntu-2204-lts"
}

resource "yandex_compute_instance_group" "web_group" {
  name               = "web-group"
  service_account_id = var.sa_id
  folder_id          = var.folder_id

  instance_template {
    platform_id = "standard-v1"

    resources {
      cores  = 2
      memory = 2
    }

    boot_disk {
      initialize_params {
        image_id = data.yandex_compute_image.ubuntu.id
      }
    }

    network_interface {
      subnet_ids = [
        yandex_vpc_subnet.subnet-a.id,
        yandex_vpc_subnet.subnet-b.id,
        yandex_vpc_subnet.subnet-d.id,
      ]
      nat = true
    }

    metadata = {
      user-data = templatefile("${path.module}/cloud-init.tftpl", {
        ycr_token     = var.ycr_token,
        db_user       = "admin",
        db_password   = var.db_password,
        db_name       = "marketdb",
        db_host       = yandex_mdb_postgresql_cluster.pg_cluster.host[0].fqdn,
        docker_compose = templatefile("${path.module}/docker-compose.tftpl", {
          db_user     = "admin",
          db_password = var.db_password,
          db_name     = "marketdb",
          db_host     = yandex_mdb_postgresql_cluster.pg_cluster.host[0].fqdn,
          image_path  = var.ycr_image_path
        })
      })
    }
  }

  scale_policy {
    fixed_scale {
      size = 3
    }
  }

  allocation_policy {
    zones = ["ru-central1-a", "ru-central1-b", "ru-central1-d"]
  }

  deploy_policy {
     max_unavailable = 1
     max_expansion   = 1
   }
}

resource "yandex_lb_target_group" "web_targets" {
  name = "web-targets"

  target {
    subnet_id  = yandex_vpc_subnet.subnet-a.id
    address    = yandex_compute_instance_group.web_group.instances[0].network_interface[0].ip_address
  }

  target {
    subnet_id  = yandex_vpc_subnet.subnet-b.id
    address    = yandex_compute_instance_group.web_group.instances[1].network_interface[0].ip_address
  }

  target {
    subnet_id  = yandex_vpc_subnet.subnet-d.id
    address    = yandex_compute_instance_group.web_group.instances[2].network_interface[0].ip_address
  }
}

resource "yandex_lb_network_load_balancer" "web_nlb" {
  name       = "web-nlb"
  network_id = yandex_vpc_network.main.id

  listener {
    name = "listener-80"
    port = 80
    external_address_spec {
      ip_version = "IPV4"
    }
  }

  attached_target_group {
    target_group_id = yandex_lb_target_group.web_targets.id

    healthcheck {
      name = "tcp-health"
      tcp_options {
        port = 80
      }
    }
  }
}




