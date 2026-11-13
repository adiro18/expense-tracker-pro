module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "~> 5.0"

  name = "${var.project_name}-vpc"
  cidr = "10.0.0.0/16"

  azs             = ["${var.aws_region}a", "${var.aws_region}b"]
  private_subnets = ["10.0.1.0/24", "10.0.2.0/24"]     # EKS nodes + RDS
  public_subnets  = ["10.0.101.0/24", "10.0.102.0/24"] # load balancers + NAT

  # One NAT gateway instead of one per AZ: cheaper, but not highly available (cost trade-off)
  enable_nat_gateway   = true
  single_nat_gateway   = true
  enable_dns_hostnames = true
  enable_dns_support   = true

  # Tags the AWS load balancer integration uses to pick subnets for Service type=LoadBalancer
  public_subnet_tags = {
    "kubernetes.io/role/elb" = 1
  }
  private_subnet_tags = {
    "kubernetes.io/role/internal-elb" = 1
  }
}
