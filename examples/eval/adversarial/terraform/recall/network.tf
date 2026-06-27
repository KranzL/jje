locals {
  vpc_id      = "vpc-0a1b2c3d4e5f6a7b8"
  environment = "production"
  app_port    = 8080
  db_port     = 5432

  common_tags = {
    Environment = local.environment
    ManagedBy   = "terraform"
    Team        = "platform"
  }
}

resource "aws_security_group" "public_alb" {
  name_prefix = "edge-alb-"
  description = "Public load balancer for the storefront"
  vpc_id      = local.vpc_id

  ingress {
    description = "TLS from internet"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = local.common_tags
}

resource "aws_security_group" "app_tier" {
  name_prefix = "app-tier-"
  description = "Application servers behind the ALB"
  vpc_id      = local.vpc_id

  ingress {
    description     = "App traffic from the load balancer"
    from_port       = local.app_port
    to_port         = local.app_port
    protocol        = "tcp"
    security_groups = [aws_security_group.public_alb.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = local.common_tags
}

resource "aws_security_group" "ops_agent" {
  name_prefix = "ops-agent-"
  description = "Host running the metrics and log shipping agent"
  vpc_id      = local.vpc_id

  ingress {
    description = "Agent administration"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "Scrape endpoint"
    from_port   = 9100
    to_port     = 9100
    protocol    = "tcp"
    cidr_blocks = ["10.0.0.0/8"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = local.common_tags
}

resource "aws_security_group" "data_store" {
  name_prefix = "data-store-"
  description = "Primary Postgres cluster"
  vpc_id      = local.vpc_id

  ingress {
    description     = "Postgres from application tier"
    from_port       = local.db_port
    to_port         = local.db_port
    protocol        = "tcp"
    security_groups = [aws_security_group.app_tier.id]
  }

  ingress {
    description     = "Postgres for operational tooling"
    from_port       = local.db_port
    to_port         = local.db_port
    protocol        = "tcp"
    security_groups = [aws_security_group.ops_agent.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["10.0.0.0/8"]
  }

  tags = local.common_tags
}
