import json
import boto3
import os

sf = boto3.client('stepfunctions', region_name='us-east-1')

def lambda_handler(event, context):

    # extraer datos del evento S3
    bucket = event['Records'][0]['s3']['bucket']['name']
    key    = event['Records'][0]['s3']['object']['key']

    # extraer nombre del archivo sin extension
    filename   = key.split("/")[-1].replace(".csv", "")

    # quitar el nombre del archivo del key para output y reject
    key_folder = "/".join(key.split("/")[:-1]) + "/"

    # construir rutas de salida reemplazando solo la subcarpeta inicial
    silver_key = key_folder.replace("bronce/", "silver/", 1) + filename + "/"
    reject_key = key_folder.replace("bronce/", "reject/", 1) + filename + "/"

    # construir JSON para Step Functions
    step_input = {
        "input_path":  f"s3://{bucket}/{key}",
        "output_path": f"s3://{bucket}/{silver_key}",
        "reject_path": f"s3://{bucket}/{reject_key}",
    }

    # ejecutar Step Functions
    response = sf.start_execution(
        stateMachineArn=os.environ["STATE_MACHINE_ARN_SUPERSTORE"],
        input=json.dumps(step_input)
    )

    print("Ejecucion iniciada:", response)

    return {
        "status":       "OK",
        "executionArn": response.get("executionArn")
    }