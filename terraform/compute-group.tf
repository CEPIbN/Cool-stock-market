# 1. Создание группы ВМ
resource "yandex_compute_instance_group" "ig-1" {
  name                = "project-instance-group"
  folder_id           = "b1gr31hq6bsesq941vg8"
  service_account_id  = "ajedk3jflri3hp4f3sc7"
  deletion_protection = false
  instance_template {
    platform_id = "standard-v3"
    resources {
      memory = 4
      cores  = 4
    }

    boot_disk {
      mode = "READ_WRITE"
      initialize_params {
        image_id = "fd8pfd17g205ujpmpb0a"
      }
    }

    network_interface {
      network_id         = yandex_vpc_network.project-net.id
      subnet_ids         = [yandex_vpc_subnet.project-subnet-d.id]
      nat = true
    }

    metadata = {
      ssh-keys = "cepib:ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABgQDTtIwz/3tExIclIYWscZw/YmvO0W56KgYKSuyA7EvzqylMpwjtFxT038SJXPHScrXn7yRqVdQmkjRjHGg0G9e1BMG4+/3/DRjbsOaxfqOQhjoSznEMgJKZncQgcaefPtjhnBId6lepqJFVEjNyrsv4pGVdmBYCxsv7EQVSJzT8nwoknACJyXJsp+OJuIjyZpuiEI3vUM+i4XwKDSLRkZXE/mgYh51S9gAys6OClKcBb77Fyd4MEWtzR0lBuVXCObKo/Bxj7ZBR7dSlPg8eXh3JqdzPTRimX5HM/Ojxi8aGwIBW7nEt6e5v4KHh+KBHK6//S5LolgkdqW1RQHZlBMgaV/LQs+JQ1Fw4qM9EPrp2MDj7v4V+iaJmRYXxDXhH6VkpRgQ9jOni1JOV6TDrnUyZxqqwNCxrgt1uYWMZ3IXqT/gmcHKtY1b+VlO7h0hbh/3tY20dZLpsvsmKNJZKBNlR0UcLRsjlpVWD8uZr086resDmD5yxXjIu++jT5ZiNi7M="
    }
  }

  scale_policy {
    fixed_scale {
      size = 3
    }
  }

  allocation_policy {
    zones = ["ru-central1-d"]
  }

  deploy_policy {
    max_unavailable = 1
    max_expansion   = 1
  }

  load_balancer {
    target_group_name        = "target-group"
    target_group_description = "Целевая группа Network Load Balancer"
  }
}

# 2. Создание сетевого балансировщика
resource "yandex_lb_network_load_balancer" "lb-1" {
  name = "network-load-balancer-1"

  listener {
    name = "network-load-balancer-1-listener"
    port = 80
    external_address_spec {
      address = yandex_vpc_address.addr.external_ipv4_address[0].address
      ip_version = "ipv4"
    }
  }

  attached_target_group {
    target_group_id = yandex_compute_instance_group.ig-1.load_balancer.0.target_group_id

    healthcheck {
      name = "tcp"
      tcp_options {
        port = 22
      }
    }
  }
}
