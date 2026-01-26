resource "aws_eks_cluster" "main" {
  name     = "hallucination-cluster"
  role_arn = aws_iam_role.eks_cluster.arn
  
  vpc_config {
    subnet_ids = [aws_subnet.private_1.id, aws_subnet.private_2.id]
  }
}

resource "null_resource" "update_kubeconfig" {
  depends_on = [aws_eks_cluster.main]

  provisioner "local-exec" {
    command = "aws eks update-kubeconfig --name ${aws_eks_cluster.main.name} --region your-region"
  }
}

resource "null_resource" "ansible_provisioner" {
  depends_on = [null_resource.update_kubeconfig]

  provisioner "local-exec" {
    command = "ansible-playbook -i ../ansible/inventory.ini ../ansible/setup_k8s_stack.yml"
  }
}