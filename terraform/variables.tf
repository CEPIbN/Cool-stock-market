
variable "yc_token" {}
variable "cloud_id" {}
variable "folder_id" {}
variable "sa_id" {}
variable "ycr_image_path" {}
variable "db_password" {
  sensitive = true
}
variable "ycr_token" {
  sensitive = true
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

# variable "use_existing_vpc_address" {
#   type        = bool
#   default     = true
#   description = "Использовать ли существующий статичный адрес"
# }
#
# variable "existing_vpc_address_id" {
#   type        = string
#   default     = "fl8bpt2t6ri8l9f8jt5r"
#   description = "ID существующего VPC-адреса (если используется)"
# }
