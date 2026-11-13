variable "aws_region" {
  description = "AWS region to deploy into"
  type        = string
  default     = "ap-south-1"
}

variable "project_name" {
  description = "Prefix for resource names"
  type        = string
  default     = "spendwise"
}

variable "db_username" {
  description = "RDS master username"
  type        = string
  default     = "spendwise_admin"
}

variable "db_password" {
  description = "RDS master password - supply via TF_VAR_db_password, never commit it"
  type        = string
  sensitive   = true
  # no default on purpose
}

variable "cluster_version" {
  description = "EKS Kubernetes version"
  type        = string
  default     = "1.31"
}

variable "node_instance_type" {
  description = "EKS worker instance type (t3.medium was rejected as not free-tier eligible)"
  type        = string
  default     = "t3.micro"
}

variable "node_min_size" {
  type    = number
  default = 1
}

variable "node_max_size" {
  type    = number
  default = 4
}

variable "node_desired_size" {
  description = "t3.micro allows only 4 pods per node, so 3 nodes are needed for app + monitoring"
  type        = number
  default     = 3
}

variable "mysql_version" {
  description = "RDS MySQL major version"
  type        = string
  default     = "8.0"
}
