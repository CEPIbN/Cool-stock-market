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

# Сетевые ресурсы
resource "yandex_vpc_network" "project-net" {
  name = "project-net"
}

resource "yandex_vpc_subnet" "project-subnet-a" {
  name           = "project-subnet-a"
  zone           = "ru-central1-a"
  network_id     = yandex_vpc_network.project-net.id
  v4_cidr_blocks = ["10.128.0.0/24"]
}

resource "yandex_vpc_subnet" "project-subnet-b" {
  name           = "project-subnet-b"
  zone           = "ru-central1-b"
  network_id     = yandex_vpc_network.project-net.id
  v4_cidr_blocks = ["10.129.0.0/24"]
}

resource "yandex_vpc_subnet" "project-subnet-d" {
  name           = "project-subnet-d"
  zone           = "ru-central1-d"
  network_id     = yandex_vpc_network.project-net.id
  v4_cidr_blocks = ["10.130.0.0/24"]
}

resource "yandex_vpc_address" "addr" {
  name = "project-ip"
  external_ipv4_address {
    zone_id = "ru-central1-d"
  }
}

# Группа ВМ
resource "yandex_compute_instance_group" "ig-1" {
  name                = "project-instance-group"
  folder_id           = "b1gr31hq6bsesq941vg8"
  service_account_id  = "ajeuc770a12co3oggj39"
  deletion_protection = false

  instance_template {
    platform_id = "standard-v3"
    
    resources {
      memory = 2
      cores  = 2
    }

    boot_disk {
      initialize_params {
        image_id = "fd85f00o4du5m341f29p"
        size     = 30
      }
    }

    network_interface {
      network_id  = yandex_vpc_network.project-net.id
      subnet_ids  = [yandex_vpc_subnet.project-subnet-d.id]
      nat         = true
    }
  }

  scale_policy {
    fixed_scale {
      size = 3
    }
  }

  allocation_policy {
    zones = ["ru-central1-d"] # Исправлено на зону подсети
  }

  deploy_policy {
    max_unavailable = 1
    max_expansion   = 1
  }

  load_balancer {
    target_group_name = "project-balancer-target-group"
  }
}

# Балансировщик нагрузки
resource "yandex_lb_network_load_balancer" "lb-1" {
  name = "project-network-lb"

  listener {
    name = "http-listener"
    port = 80
    external_address_spec {
      address    = yandex_vpc_address.addr.external_ipv4_address[0].address
      ip_version = "ipv4"
    }
  }

  attached_target_group {
    target_group_id = yandex_compute_instance_group.ig-1.load_balancer[0].target_group_id

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

# База данных
resource "yandex_mdb_postgresql_cluster" "project-db-cluster" {
  name                = "project-db-cluster"
  environment         = "PRODUCTION"
  network_id          = yandex_vpc_network.project-net.id
  deletion_protection = false

  config {
    version = 17
    resources {
      resource_preset_id = "c3-c2-m4"
      disk_type_id       = "network-ssd"
      disk_size          = 50
    }
    pooler_config {
      pool_discard = false
    }
  }

  host {
    zone             = "ru-central1-d"
    name             = "project-master-host"
    subnet_id        = yandex_vpc_subnet.project-subnet-d.id
    assign_public_ip = false
  }
  host {
    zone             = "ru-central1-a"
    name             = "project-host-a"
    subnet_id        = yandex_vpc_subnet.project-subnet-a.id
    assign_public_ip = false
  }
  host {
    zone             = "ru-central1-b"
    name             = "project-host-b"
    subnet_id        = yandex_vpc_subnet.project-subnet-b.id
    assign_public_ip = false
  }
}

resource "yandex_mdb_postgresql_user" "project-db-user" {
  cluster_id = yandex_mdb_postgresql_cluster.project-db-cluster.id
  name       = "project-db-user"
  password   = "ThisIsSecretPassword321!"
}

resource "yandex_mdb_postgresql_database" "project-database" {
  cluster_id = yandex_mdb_postgresql_cluster.project-db-cluster.id
  name       = "project-database"
  owner      = "project-db-user"
}

output "lb_external_ip" {
  value = yandex_vpc_address.addr.external_ipv4_address[0].address
}
