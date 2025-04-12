# 1. Создаем сеть
resource "yandex_vpc_network" "project-net" {
  name = "project-net"
}

# 2. Создаем подсеть в зоне a
resource "yandex_vpc_subnet" "project-subnet-a" {
  name           = "project-subnet-a"
  zone           = "ru-central1-a"
  network_id     = yandex_vpc_network.project-net.id
  v4_cidr_blocks = ["10.128.0.0/24"]
}

# 3. Создаем подсеть в зоне b
resource "yandex_vpc_subnet" "project-subnet-b" {
  name           = "project-subnet-b"
  zone           = "ru-central1-b"
  network_id     = yandex_vpc_network.project-net.id
  v4_cidr_blocks = ["10.129.0.0/24"]
}

# 4. Создаем подсеть в зоне d
resource "yandex_vpc_subnet" "project-subnet-d" {
  name           = "project-subnet-d"
  zone           = "ru-central1-d"
  network_id     = yandex_vpc_network.project-net.id
  v4_cidr_blocks = ["10.130.0.0/24"]
}

# 5. Зарезервирование статического публичного IP-адреса
resource "yandex_vpc_address" "addr" {
  name = "project-ip"
  external_ipv4_address {
    zone_id = "ru-central1-d"
  }
}
