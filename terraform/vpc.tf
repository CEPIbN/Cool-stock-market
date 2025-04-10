# 1. Создаем сеть
resource "yandex_vpc_network" "mynet" {
  name = "mynet"
}

# 2. Создаем подсеть в зоне d
resource "yandex_vpc_subnet" "mysubnet" {
  name           = "mysubnet"
  zone           = "ru-central1-d"
  network_id     = yandex_vpc_network.mynet.id
  v4_cidr_blocks = ["10.5.0.0/24"]
}
