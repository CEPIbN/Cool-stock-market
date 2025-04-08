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

resource "yandex_container_registry" "my-reg" {
  name = "project-registry"
  folder_id = "b1gr31hq6bsesq941vg8"
}
