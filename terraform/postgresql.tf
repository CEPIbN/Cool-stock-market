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
  depends_on = [
    yandex_mdb_postgresql_user.project-db-user
  ]
}

