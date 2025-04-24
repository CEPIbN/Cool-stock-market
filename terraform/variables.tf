
variable "yc_token" {}
variable "cloud_id" {}
variable "folder_id" {}
variable "sa_id" {}
variable "db_password" {
  sensitive = true
}
variable "ycr_token" {
  sensitive = true
}
