import json
import os

import boto3

def call_aws_lambda(function_name: str,  payload: dict, region_name:str) -> dict:
    # Create a Lambda client
    client = boto3.client(service_name='lambda', region_name=region_name)
    payload = json.dumps(payload)
    try:
        # Invoke the Lambda function and pass the parameters in the payload
        response = client.invoke(FunctionName=function_name, InvocationType='RequestResponse', Payload=payload)  # 'RequestResponse' for synchronous, 'Event' for async

        # Parse the response payload
        response_payload = response['Payload'].read()

        response_payload = json.loads(response_payload.decode('utf-8'))

        return response_payload['body']

    except Exception as e:
        print("Error invoking Lambda function:", str(e))

# Configuración de documentos y variables
docs = ['cmf.txt', 'bienesRaices.txt', 'vehiculos.txt']
# Cargar documentos JSON
json_strings = {}
for doc in docs:
    key = doc.replace(".txt", "")
    with open(f"data_examples/{doc}", 'r') as file:
        value = file.read()
    value = json.loads(value)
    json_strings[key] = value

json_strings['edad'] = 24
json_strings['ingreso_mensual'] = 100000
json_strings['enfoque'] = "Busco un enfoque en futuras inversiones"

function_name = "queryWriting"

region_name= 'us-east-1'
response = call_aws_lambda(function_name, json_strings, region_name)
print(response)