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
  #count = var.use_existing_vpc_address ? 0 : 1
  external_ipv4_address {
    zone_id = "ru-central1-d"
  }
}

resource "yandex_mdb_postgresql_cluster" "pg_cluster" {
  name        = "my-pg-cluster"
  environment = "PRODUCTION"
  network_id  = local.vpc_id

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

resource "yandex_mdb_postgresql_user" "admin" {
  cluster_id = yandex_mdb_postgresql_cluster.pg_cluster.id
  name       = "market-owner"
  password   = var.db_password
}

resource "yandex_mdb_postgresql_database" "market-db" {
  cluster_id = yandex_mdb_postgresql_cluster.pg_cluster.id
  name       = "marketdb"
  owner      = "market-owner"
}

data "yandex_compute_image" "ubuntu" {
  family = "ubuntu-2204-lts"
}

resource "yandex_compute_instance_group" "web_group" {
  name               = "web-group"
  service_account_id = var.sa_id
  folder_id          = var.folder_id

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
    max_unavailable = 1
    max_expansion   = 1
  }

  load_balancer {
    target_group_name = "market-balancer-target-group"
  }
}

# load balancer
resource "yandex_lb_network_load_balancer" "lb-1" {
  name = "market-network-lb"

  listener {
    name = "http-listener"
    port = 80
    external_address_spec {
      address    = yandex_vpc_address.addr.external_ipv4_address[0].address
      ip_version = "ipv4"
    }
  }

  attached_target_group {
    target_group_id = yandex_compute_instance_group.web_group.load_balancer[0].target_group_id

    healthcheck {
      name = "tcp-healthcheck"
      tcp_options {
        port = 80
      }
      interval = 2
      timeout  = 1
    }
  }
}

output "lb_external_ip" {
  value = yandex_vpc_address.addr.external_ipv4_address[0].address
}

locals {
  raw_docker_compose = templatefile("${path.module}/docker-compose.tftpl", {
    db_user     = "market-owner",
    db_password = var.db_password,
    db_name     = "marketdb",
    db_host     = yandex_mdb_postgresql_cluster.pg_cluster.host[0].fqdn,
    image_path  = var.ycr_image_path
  })

  # Add tab to each line
  docker_compose = join("\n", [for line in split("\n", local.raw_docker_compose) : "      ${line}"])

  cloud_init = templatefile("${path.module}/cloud-init.tftpl", {
    ycr_token = var.ycr_token
    docker_compose = local.docker_compose
  })

  vpc_id = var.use_existing_vpc ? var.existing_vpc_id : yandex_vpc_network.main[0].id
  #vpc_address = var.use_existing_vpc_address ? var.existing_vpc_address_id : yandex_vpc_address.addr[0].external_ipv4_address[0].address
}




