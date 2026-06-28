resource "aws_security_group" "processor" {
  name        = "${local.name}-processor"
  description = "Egress for the document processing Lambda ENIs."
  vpc_id      = var.vpc_id
}

resource "aws_vpc_security_group_egress_rule" "processor_https" {
  security_group_id = aws_security_group.processor.id
  description       = "Outbound HTTPS to AWS service endpoints."
  ip_protocol       = "tcp"
  from_port         = 443
  to_port           = 443
  cidr_ipv4         = "0.0.0.0/0"
}

resource "aws_security_group" "vpce" {
  name        = "${local.name}-vpce"
  description = "Interface VPC endpoints for the pipeline."
  vpc_id      = var.vpc_id
}

resource "aws_vpc_security_group_ingress_rule" "vpce_from_processor" {
  security_group_id            = aws_security_group.vpce.id
  description                  = "HTTPS from the processor Lambda only."
  ip_protocol                  = "tcp"
  from_port                    = 443
  to_port                      = 443
  referenced_security_group_id = aws_security_group.processor.id
}

resource "aws_security_group" "metrics_proxy" {
  name        = "${local.name}-metrics-proxy"
  description = "Internal proxy that forwards pipeline metrics to the collector."
  vpc_id      = var.vpc_id
}

resource "aws_vpc_security_group_ingress_rule" "metrics_from_vpc" {
  security_group_id = aws_security_group.metrics_proxy.id
  description       = "Scrape endpoint reachable from within the VPC."
  ip_protocol       = "tcp"
  from_port         = 9090
  to_port           = 9090
  cidr_ipv4         = var.ingest_lvpc_cidr
}

resource "aws_vpc_endpoint" "dynamodb" {
  vpc_id            = var.vpc_id
  service_name      = "com.amazonaws.${var.region}.dynamodb"
  vpc_endpoint_type = "Gateway"
}

resource "aws_vpc_endpoint" "sqs" {
  vpc_id              = var.vpc_id
  service_name        = "com.amazonaws.${var.region}.sqs"
  vpc_endpoint_type   = "Interface"
  subnet_ids          = var.private_subnet_ids
  security_group_ids  = [aws_security_group.vpce.id]
  private_dns_enabled = true
}
