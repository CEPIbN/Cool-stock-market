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

# VPC & Subnets
resource "yandex_vpc_network" "main" {
  name  = "main-network"
  count = var.use_existing_vpc ? 0 : 1
}

resource "yandex_vpc_subnet" "subnet-a" {
  name           = "subnet-a"
  zone           = "ru-central1-a"
  network_id     = local.vpc_id
  v4_cidr_blocks = ["10.0.1.0/24"]
}

resource "yandex_vpc_subnet" "subnet-b" {
  name           = "subnet-b"
  zone           = "ru-central1-b"
  network_id     = local.vpc_id
  v4_cidr_blocks = ["10.0.2.0/24"]
}

resource "yandex_vpc_subnet" "subnet-d" {
  name           = "subnet-d"
  zone           = "ru-central1-d"
  network_id     = local.vpc_id
  v4_cidr_blocks = ["10.0.3.0/24"]
}

resource "yandex_vpc_address" "addr" {
  name = "project-ip"
  external_ipv4_address {
    zone_id = "ru-central1-d"
  }
}

# PostgreSQL cluster
resource "yandex_mdb_postgresql_cluster" "pg_cluster" {
  name        = "my-pg-cluster"
  environment = "PRODUCTION"
  network_id  = local.vpc_id

  config {
    version = "14"
    resources {
      resource_preset_id = "s2.micro"
      disk_size          = 30
      disk_type_id       = "network-hdd"
    }
  }
  
  host {
    zone      = "ru-central1-d"
    subnet_id = yandex_vpc_subnet.subnet-d.id
  }
}

resource "yandex_mdb_postgresql_user" "admin" {
  cluster_id = yandex_mdb_postgresql_cluster.pg_cluster.id
  name       = "market-owner"
  password   = var.db_password
}

resource "yandex_mdb_postgresql_database" "market-db" {
  cluster_id = yandex_mdb_postgresql_cluster.pg_cluster.id
  name       = "marketdb"
  owner      = yandex_mdb_postgresql_user.admin.name

  depends_on = [yandex_mdb_postgresql_user.admin]
}

# Compute instance group
data "yandex_compute_image" "ubuntu" {
  family = "ubuntu-2204-lts"
}

resource "yandex_compute_instance_group" "web_group" {
  name               = "web-group"
  service_account_id = var.sa_id
  folder_id          = var.folder_id

  depends_on = [
    yandex_mdb_postgresql_user.admin,
    yandex_mdb_postgresql_database.market-db
  ]

  instance_template {
    platform_id = "standard-v2"

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
      ssh-keys  = "ubuntu:${file("~/.ssh/id_rsa.pub")}"
      user-data = local.cloud_init
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
    max_unavailable = 2
    max_expansion   = 3
    max_creating    = 3
    max_deleting    = 1
  }

}

# ALB target and backend group
resource "yandex_alb_target_group" "alb_target_group" {
  name = "alb-target-group"

  target {
    subnet_id  = yandex_vpc_subnet.subnet-a.id
    ip_address = yandex_compute_instance_group.web_group.instances[0].network_interface[0].ip_address
  }

  target {
    subnet_id  = yandex_vpc_subnet.subnet-b.id
    ip_address = yandex_compute_instance_group.web_group.instances[1].network_interface[0].ip_address
  }

  target {
    subnet_id  = yandex_vpc_subnet.subnet-d.id
    ip_address = yandex_compute_instance_group.web_group.instances[2].network_interface[0].ip_address
  }
}

resource "yandex_alb_backend_group" "bg" {
  name = "market-backend-group"

  http_backend {
    name             = "http-backend"
    target_group_ids = [yandex_alb_target_group.alb_target_group.id]
    port             = 80

    load_balancing_config {
      panic_threshold = 50
    }

    healthcheck {
      timeout  = "1s"
      interval = "2s"

      http_healthcheck {
        path = "/"
      }
    }
  }
}

resource "yandex_alb_http_router" "router" {
  name = "market-router"
}

resource "yandex_alb_virtual_host" "vhost" {
  name           = "market-vhost"
  http_router_id = yandex_alb_http_router.router.id

  route {
    name = "default-route"

    http_route {
      http_route_action {
        backend_group_id = yandex_alb_backend_group.bg.id
      }
    }
  }
}

resource "yandex_alb_load_balancer" "alb" {
  name       = "market-alb"
  network_id = local.vpc_id

  allocation_policy {
    location {
      zone_id   = "ru-central1-a"
      subnet_id = yandex_vpc_subnet.subnet-a.id
    }
    location {
      zone_id   = "ru-central1-b"
      subnet_id = yandex_vpc_subnet.subnet-b.id
    }
    location {
      zone_id   = "ru-central1-d"
      subnet_id = yandex_vpc_subnet.subnet-d.id
    }
  }

  listener {
    name = "https-listener"

    endpoint {
      address {
        external_ipv4_address {
          address = yandex_vpc_address.addr.external_ipv4_address[0].address
        }
      }
      ports = [443]
    }

    tls {
      default_handler {
        certificate_ids = [var.certificate_id]

        http_handler {
          http_router_id = yandex_alb_http_router.router.id
        }
      }
    }
  }

  depends_on = [
    yandex_alb_backend_group.bg,
    yandex_alb_virtual_host.vhost
  ]
}

# Output
output "alb_external_ip" {
  value = yandex_vpc_address.addr.external_ipv4_address[0].address
}

# Locals
locals {
  raw_docker_compose = templatefile("${path.module}/docker-compose.tftpl", {
    db_user     = yandex_mdb_postgresql_user.admin.name,
    db_password = var.db_password,
    db_name     = yandex_mdb_postgresql_database.market-db.name,
    db_host     = yandex_mdb_postgresql_cluster.pg_cluster.host[0].fqdn,
    image_path  = var.ycr_image_path
  })

  docker_compose = join("\n", [for line in split("\n", local.raw_docker_compose) : "      ${line}"])

  cloud_init = templatefile("${path.module}/cloud-init.tftpl", {
    ycr_token      = var.ycr_token,
    docker_compose = local.docker_compose
  })

  vpc_id = var.use_existing_vpc ? var.existing_vpc_id : yandex_vpc_network.main[0].id
}

