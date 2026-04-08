agregar el archivo terraform.tfvars con lo siguiente:

aws_access_key = "zzzzzzzzzzzz
aws_secret_key = "zzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzz"

Ejecutar terraform (terminal)
terraform apply -var-file="terraform.tfvars"

eliminar todo
terraform destroy -auto-approve

auto aprove
terraform apply -var-file="terraform.tfvars" -auto-approve