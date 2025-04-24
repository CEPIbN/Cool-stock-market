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

resource "yandex_vpc_subnet" "subnet-c" {
  name           = "subnet-c"
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
    subnet_id = yandex_vpc_subnet.subnet-c.id
  }
}

resource "yandex_mdb_postgresql_database" "marketdb" {
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
        yandex_vpc_subnet.subnet-c.id,
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

# Получаем список IP-адресов из instance group
output "web_instance_ips" {
  value = [for i in yandex_compute_instance_group.web_group.instances : i.network_interface[0].ip_address]
}

data "yandex_compute_instance_group" "web_group_data" {
  instance_group_id = yandex_compute_instance_group.web_group.id
  depends_on = [yandex_compute_instance_group.web_group]
}

resource "yandex_alb_target_group" "alb_group" {
  name = "web-alb-group"

  dynamic "target" {
    for_each = toset(yandex_compute_instance_group.web_group.instances.*.network_interface[0].ip_address)
    content {
      subnet_id  = element([
        yandex_vpc_subnet.subnet-a.id,
        yandex_vpc_subnet.subnet-b.id,
        yandex_vpc_subnet.subnet-c.id
      ], index(yandex_compute_instance_group.web_group.instances.*.network_interface[0].ip_address, target.value))
      ip_address = target.value
    }
  }
}

resource "yandex_alb_backend_group" "web_backend_group" {
  name = "web-backend-group"
  http_backend {
    name             = "web-backend"
    port             = 80
    target_group_ids = [yandex_alb_target_group.alb_group.id]
    load_balancing_config {
      panic_threshold = 50
    }
    healthcheck {
      timeout  = "1s"
      interval = "5s"
      http_healthcheck {
        path = "/"
      }
    }
  }
}

resource "yandex_alb_http_router" "web_router" {
  name = "web-router"
}

resource "yandex_alb_virtual_host" "web_host" {
  name           = "web-host"
  http_router_id = yandex_alb_http_router.web_router.id
  route {
    name = "default-route"
    http_route {
      http_route_action {
        backend_group_id = yandex_alb_backend_group.web_backend_group.id
      }
    }
  }
}

resource "yandex_alb_load_balancer" "web_alb" {
  name        = "web-alb"
  network_id  = yandex_vpc_network.main.id

  allocation_policy {
    location {
      zone_id   = "ru-central1-a"
      subnet_id = yandex_vpc_subnet.subnet-a.id
    }
  }

  listener {
    name = "http"
    endpoint {
      address {
        external_ipv4_address {}
      }
      ports = [80]
    }
    http {
      router_id = yandex_alb_http_router.web_router.id
    }
  }
}




