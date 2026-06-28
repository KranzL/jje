variable "region" {
  description = "AWS region for the document ingest pipeline."
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Deployment environment name."
  type        = string

  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "environment must be one of dev, staging, prod."
  }
}

variable "name_prefix" {
  description = "Prefix applied to all named resources."
  type        = string
  default     = "doc-ingest"
}

variable "vpc_id" {
  description = "VPC the processing Lambda is attached to."
  type        = string
}

variable "private_subnet_ids" {
  description = "Private subnets for the processing Lambda ENIs."
  type        = list(string)
}

variable "ingest_lvpc_cidr" {
  description = "CIDR block of the VPC, used for intra-VPC SG rules."
  type        = string
}

variable "lambda_memory_mb" {
  description = "Memory allocation for the processing Lambda."
  type        = number
  default     = 512

  validation {
    condition     = var.lambda_memory_mb >= 128 && var.lambda_memory_mb <= 3008
    error_message = "lambda_memory_mb must be between 128 and 3008."
  }
}

variable "visibility_timeout_seconds" {
  description = "SQS visibility timeout; must exceed Lambda timeout."
  type        = number
  default     = 180
}

variable "max_receive_count" {
  description = "Redrive count before a message lands in the DLQ."
  type        = number
  default     = 5
}

variable "log_retention_days" {
  description = "CloudWatch log retention for the processing Lambda."
  type        = number
  default     = 30
}
