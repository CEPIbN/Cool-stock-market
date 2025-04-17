# 1. Создание диска
resource "yandex_compute_disk" "project-disk" {
  name     = "project-disk"
  type     = "network-ssd"
  zone     = "ru-central1-d"
  size     = "20"
  image_id = "fd8pfd17g205ujpmpb0a"
}

# 2. Создание ВМ
resource "yandex_compute_instance" "vm" {
  name                      = "linux-vm"
  allow_stopping_for_update = true
  platform_id               = "standard-v3"
  zone                      = "ru-central1-d"

  resources {
    cores  = 2
    memory = 2
  }

  boot_disk {
    auto_delete = true
    disk_id = yandex_compute_disk.project-disk.id
  }

  network_interface {
    subnet_id = "${yandex_vpc_subnet.project-subnet-d.id}"
    nat       = true
  }

  metadata = {
    ssh-keys = "cepib:ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABgQDTtIwz/3tExIclIYWscZw/YmvO0W56KgYKSuyA7EvzqylMpwjtFxT038SJXPHScrXn7yRqVdQmkjRjHGg0G9e1BMG4+/3/DRjbsOaxfqOQhjoSznEMgJKZncQgcaefPtjhnBId6lepqJFVEjNyrsv4pGVdmBYCxsv7EQVSJzT8nwoknACJyXJsp+OJuIjyZpuiEI3vUM+i4XwKDSLRkZXE/mgYh51S9gAys6OClKcBb77Fyd4MEWtzR0lBuVXCObKo/Bxj7ZBR7dSlPg8eXh3JqdzPTRimX5HM/Ojxi8aGwIBW7nEt6e5v4KHh+KBHK6//S5LolgkdqW1RQHZlBMgaV/LQs+JQ1Fw4qM9EPrp2MDj7v4V+iaJmRYXxDXhH6VkpRgQ9jOni1JOV6TDrnUyZxqqwNCxrgt1uYWMZ3IXqT/gmcHKtY1b+VlO7h0hbh/3tY20dZLpsvsmKNJZKBNlR0UcLRsjlpVWD8uZr086resDmD5yxXjIu++jT5ZiNi7M="
  }
}

