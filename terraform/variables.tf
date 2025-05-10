variable "yc_token" {}
variable "cloud_id" {}
variable "folder_id" {}
variable "sa_id" {}
variable "ycr_image_path" {}
variable "domain_name" {}

variable "db_password" {
  sensitive = true
}

variable "ycr_token" {
  sensitive = true
}

variable "certificate_id" {
  description = "ID сертификата в Yandex Certificate Manager"
  type        = string
}

variable "use_existing_vpc" {
  type        = bool
  default     = false
  description = "Использовать ли существующую VPC-сеть"
}

variable "existing_vpc_id" {
  type        = string
  default     = "enpabvcpqisuj64t4u4p"
  description = "ID существующей VPC-сети (если используется)"
}

