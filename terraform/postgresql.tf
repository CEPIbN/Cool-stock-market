resource "yandex_vpc_security_group" "pgsql-sg" {
  name       = "pgsql-sg"
  network_id = yandex_vpc_network.mynet.id

  ingress {
    description    = "PostgreSQL"
    port           = 6432
    protocol       = "TCP"
    v4_cidr_blocks = ["0.0.0.0/0"]
  }
}

# 4. Создаем кластер PostgreSQL
resource "yandex_mdb_postgresql_cluster" "mypg" {
  name                = "mypg"
  environment         = "PRESTABLE"
  network_id          = yandex_vpc_network.mynet.id
  security_group_ids  = [yandex_vpc_security_group.pgsql-sg.id]
  deletion_protection = false

  config {
    version = 17
    resources {
      resource_preset_id = "s2.micro"
      disk_type_id       = "network-ssd"
      disk_size          = 20
    }
  }

  host {
    zone      = "ru-central1-d"
    name      = "mypg-host-d"
    subnet_id = yandex_vpc_subnet.mysubnet.id
  }
}

# 5. Создаем пользователя
resource "yandex_mdb_postgresql_user" "user1" {
  cluster_id = yandex_mdb_postgresql_cluster.mypg.id
  name       = "user1"
  password   = "user1user1"
  depends_on = [yandex_mdb_postgresql_cluster.mypg]
}

# 6. Создаем БД 
resource "yandex_mdb_postgresql_database" "db1" {
  cluster_id = yandex_mdb_postgresql_cluster.mypg.id
  name       = "db1"
  owner      = "user1"
  depends_on = [yandex_mdb_postgresql_user.user1]
}
