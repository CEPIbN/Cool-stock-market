# 1. Создание группы безопастности
resource "yandex_vpc_security_group" "pgsql-sg" {
  name       = "pgsql-sg"
  network_id = yandex_vpc_network.project-net.id

  ingress {
    description    = "PostgreSQL"
    port           = 6432
    protocol       = "TCP"
    v4_cidr_blocks = ["0.0.0.0/0"]
  }
}

# 2. Создание кластер PostgreSQL
resource "yandex_mdb_postgresql_cluster" "project-pg" {
  name                = "project-pg"
  environment         = "PRODUCTION"
  network_id          = yandex_vpc_network.project-net.id
  security_group_ids  = [yandex_vpc_security_group.pgsql-sg.id]
  deletion_protection = false

  config {
    version = 17
    resources {
      resource_preset_id = "s2.micro"
      disk_type_id       = "network-ssd"
      disk_size          = 50
    }
  }

  host {
    zone      = "ru-central1-d"
    name      = "project-pg-host-d"
    subnet_id = yandex_vpc_subnet.project-subnet-d.id
  }
}

# 3. Создание пользователя
resource "yandex_mdb_postgresql_user" "project" {
  cluster_id = yandex_mdb_postgresql_cluster.project-pg.id
  name       = "project"
  password   = "MySecurePassword123!"
  depends_on = [yandex_mdb_postgresql_cluster.project-pg]
}

# 4. Создание БД 
resource "yandex_mdb_postgresql_database" "database" {
  cluster_id = yandex_mdb_postgresql_cluster.project-pg.id
  name       = "project-db"
  owner      = yandex_mdb_postgresql_user.project.name
  depends_on = [yandex_mdb_postgresql_user.project]
}
