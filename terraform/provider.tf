provider "aws" {
  region = var.aws_region

  # Every resource gets these tags - handy for finding/cleaning up costs in the AWS console
  default_tags {
    tags = {
      Project   = "spendwise"
      ManagedBy = "terraform"
    }
  }
}
