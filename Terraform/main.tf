# ==================================================
# cargar credenciales
# ==================================================
provider "aws" {
  region     = "us-east-1"
  access_key = var.aws_access_key
  secret_key = var.aws_secret_key
}

# ==================================================
# Bucket S3
# ==================================================
resource "aws_s3_bucket" "luishdr-data-bucket" {
  bucket = "luishdr-data-bucket"
}

resource "aws_s3_bucket_ownership_controls" "luishdr-data-bucket" {
  bucket = aws_s3_bucket.luishdr-data-bucket.id
  rule {
    object_ownership = "BucketOwnerEnforced"
  }
}

resource "aws_s3_bucket_public_access_block" "luishdr-data-bucket" {
  bucket                  = aws_s3_bucket.luishdr-data-bucket.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Carpetas Bronce / Silver / Gold / Reject

resource "aws_s3_object" "folders" {
  for_each = toset(["bronce/", "silver/", "gold/", "reject/"])

  bucket  = aws_s3_bucket.luishdr-data-bucket.id
  key     = each.value
  content = ""
}

# ==================================================
# Step fuctions
# ==================================================

resource "aws_sfn_state_machine" "step-lambda-to-glue-superstore" {
  name     = "step-lambda-to-glue-superstore"
  role_arn = aws_iam_role.role-step-lambda-to-glue-superstore.arn

  definition = file("${path.module}/stepfuctions/step_superstore.json")
}

# rol para Step fuctions

resource "aws_iam_role" "role-step-lambda-to-glue-superstore" {
  name = "role-step-lambda-to-glue-superstore"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "states.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })
}

# police para que step use glue
resource "aws_iam_policy" "policy-rol-step-lambda-to-glue-superstore" {
  name = "policy-rol-step-lambda-to-glue-superstore"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "glue:StartJobRun",
          "glue:GetJobRun",
          "glue:GetJobRuns",
          "glue:BatchStopJobRun"
        ]
        Resource = aws_glue_job.glue-bronce-to-silver-superstore.arn
      }
    ]
  })
}

# atach 
resource "aws_iam_role_policy_attachment" "attach_glue_policy" {
  role       = aws_iam_role.role-step-lambda-to-glue-superstore.name
  policy_arn = aws_iam_policy.policy-rol-step-lambda-to-glue-superstore.arn
}

# ==================================================
# Lambda
# ==================================================

# empaquetar lambda en zip
data "archive_file" "lambda_zip_superstore" {
  type        = "zip"
  source_file = "${path.module}/lambda/lambda_function.py"
  output_path = "${path.module}/lambda/lambda_function.py.zip"
}

# levantar lambda
resource "aws_lambda_function" "Lamdbda_bronce_superstore_upload" {
  function_name = "Lamdbda_bronce_superstore_upload"

  role = aws_iam_role.role-execution-lambda-superstore.arn  

  handler = "lambda_function.lambda_handler"
  runtime = "python3.11"

  filename         = data.archive_file.lambda_zip_superstore.output_path
  source_code_hash = data.archive_file.lambda_zip_superstore.output_base64sha256

  timeout = 10

  environment {
    variables = {
      STATE_MACHINE_ARN_SUPERSTORE = aws_sfn_state_machine.step-lambda-to-glue-superstore.arn
    }
  }

  depends_on = [
    aws_iam_role_policy_attachment.lambda_basic_execution,
  ]
}

# IAM Role para Lambda
resource "aws_iam_role" "role-execution-lambda-superstore" {
  name = "role-execution-lambda-superstore"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })
}

# POLÍTICA 1: Logs básicos (CloudWatch)

resource "aws_iam_role_policy_attachment" "lambda_basic_execution" {
  role       = aws_iam_role.role-execution-lambda-superstore.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# POLÍTICA 2: acceso a stepfuctions

resource "aws_iam_role_policy" "role_lambda_stepfunctions_superstore" {
  name = "lambda-stepfunctions-policy"
  role = aws_iam_role.role-execution-lambda-superstore.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "states:StartExecution"
        ]
        Resource = aws_sfn_state_machine.step-lambda-to-glue-superstore.arn
      }
    ]
  })
}

# configura notificación de S3 hacia Lambda cuando ocurre un evento en bronce/superstore (tigger)
resource "aws_s3_bucket_notification" "bucket_notification" {
  bucket     = aws_s3_bucket.luishdr-data-bucket.id
  depends_on = [aws_lambda_permission.allow_s3]

  lambda_function {
    lambda_function_arn = aws_lambda_function.Lamdbda_bronce_superstore_upload.arn
    events              = ["s3:ObjectCreated:*"]
    filter_prefix       = "bronce/superstore/"
    filter_suffix       = ".csv"
  }
}

# permite que el servicio S3 invoque la Lambda
resource "aws_lambda_permission" "allow_s3" {
  statement_id  = "AllowS3Invoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.Lamdbda_bronce_superstore_upload.function_name
  principal     = "s3.amazonaws.com"

  source_arn = aws_s3_bucket.luishdr-data-bucket.arn
}

# ==================================================
# Glue
# ==================================================

resource "aws_glue_job" "glue-bronce-to-silver-superstore" {
  name     = "glue-bronce-to-silver-superstore"
  role_arn = aws_iam_role.rol-glue-superstore.arn

  command {
    script_location = "s3://${aws_s3_bucket.luis-bucket-glue-script-superstore.bucket}/${aws_s3_object.glue_script-superstore.key}"
    python_version  = "3"
  }

  worker_type       = "G.1X"
  number_of_workers = 2   
  glue_version      = "5.1"
  max_retries       = 1
  timeout           = 10

  execution_property {
    max_concurrent_runs = 1
  }
  
  depends_on = [
    aws_s3_object.glue_script-superstore,
    aws_iam_role_policy_attachment.glue_s3_attach_superstore,
    aws_iam_role_policy_attachment.glue_service_policy
  ]
}

# bucket para glue
resource "aws_s3_bucket" "luis-bucket-glue-script-superstore" {
  bucket = "luis-bucket-glue-script-superstore"
}

# cargar script
resource "aws_s3_object" "glue_script-superstore" {
  bucket = aws_s3_bucket.luis-bucket-glue-script-superstore.id
  key    = "scripts/script.py"
  source = "${path.module}/glue/script.py"
}

# rol para glue
resource "aws_iam_role" "rol-glue-superstore" {
  name = "rol-glue-superstore"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "glue.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })
}

# police para glue — bucket de scripts y bucket de datos
resource "aws_iam_policy" "glue_s3_policy_superstore" {
  name = "glue_s3_policy_superstore"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = ["s3:GetObject", "s3:PutObject", "s3:ListBucket", "s3:DeleteObject"]
        Resource = [
          aws_s3_bucket.luis-bucket-glue-script-superstore.arn,
          "${aws_s3_bucket.luis-bucket-glue-script-superstore.arn}/*",
          aws_s3_bucket.luishdr-data-bucket.arn,
          "${aws_s3_bucket.luishdr-data-bucket.arn}/*"
        ]
      }
    ]
  })
}

# atach
resource "aws_iam_role_policy_attachment" "glue_s3_attach_superstore" {
  role       = aws_iam_role.rol-glue-superstore.name
  policy_arn = aws_iam_policy.glue_s3_policy_superstore.arn
}

resource "aws_iam_role_policy_attachment" "glue_service_policy" {
  role       = aws_iam_role.rol-glue-superstore.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSGlueServiceRole"
}