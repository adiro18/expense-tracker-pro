module "eks" {
  source  = "terraform-aws-modules/eks/aws"
  version = "~> 20.0"

  cluster_name    = "${var.project_name}-eks"
  cluster_version = var.cluster_version

  vpc_id     = module.vpc.vpc_id
  subnet_ids = module.vpc.private_subnets

  # Public API endpoint so kubectl works from a laptop
  cluster_endpoint_public_access = true

  # Gives the IAM identity that runs terraform admin access inside the cluster
  enable_cluster_creator_admin_permissions = true

  eks_managed_node_groups = {
    default = {
      ami_type       = "AL2023_x86_64_STANDARD"
      instance_types = [var.node_instance_type]

      min_size = var.node_min_size
      max_size = var.node_max_size
      # NOTE: the module ignores changes to desired_size after creation (so autoscalers
      # don't fight Terraform). To scale an existing cluster use:
      #   aws eks update-nodegroup-config --cluster-name spendwise-eks \
      #     --nodegroup-name <name> --scaling-config minSize=1,maxSize=4,desiredSize=4
      desired_size = var.node_desired_size
    }
  }
}
