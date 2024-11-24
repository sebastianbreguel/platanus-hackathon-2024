import json
import os

import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv

load_dotenv()


class ModelClient:
    def __init__(
        self,
        region_name: str = "us-east-1",
        model_id: str = "anthropic.claude-3-haiku-20240307-v1:0",
    ):
        # Create a Bedrock Runtime client in the AWS Region of your choice.
        self.client = boto3.client("bedrock-runtime", region_name=region_name)
        # Create a Bedrock Agent Runtime client
        self.agent_client = boto3.client(
            "bedrock-agent-runtime", region_name=region_name
        )
        # Set the model ID, e.g., Claude 3 Haiku.
        self.model_id = model_id
        self.knowledge_base_id = os.getenv("KNOWLEDGE_BASE_ID")

    def invoke(
        self,
        prompt: str,
        user_input: str,
        max_tokens: int = 1024,
        temperature: float = 0,
    ) -> str:
        # Format the request payload using the model's native structure.
        native_request = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": max_tokens,
            "temperature": temperature,
            "system": prompt,
            "messages": [
                {
                    "role": "user",
                    "content": [{"type": "text", "text": user_input}],
                }
            ],
        }

        # Convert the native request to JSON.
        request = json.dumps(native_request)

        max_retries = 3
        retry_delay = 1  # Start with 1 second delay

        for attempt in range(max_retries):
            try:
                # Invoke the model with the request.
                response = self.client.invoke_model(modelId=self.model_id, body=request)
                response = self.extract_output(response)

                break  # If successful, break out of retry loop

            except ClientError as e:
                error_code = e.response.get("Error", {}).get("Code", "")
                if error_code == "ThrottlingException" and attempt < max_retries - 1:
                    import time

                    time.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                    continue
                print(f"ERROR: Can't invoke '{self.model_id}'. Reason: {e}")
                exit(1)

            except Exception as e:
                print(f"ERROR: Can't invoke '{self.model_id}'. Reason: {e}")
                exit(1)

        return response

    def extract_output(self, response: str) -> str:
        model_response = json.loads(response["body"].read())

        # Extract and print the response text.
        response_text = model_response["content"][0]["text"]
        return response_text

    def retrieve(
        self, query_text: str, specific_system_prompt: str = "", num_results: int = 10
    ) -> str:
        """
        Retrieve documents from a Bedrock knowledge base and process them with the model.
        """
        # Construct the retrieval query
        retrieval_query = {"text": query_text}

        # Get documents from knowledge base
        response = self.agent_client.retrieve(
            knowledgeBaseId=self.knowledge_base_id,
            retrievalQuery=retrieval_query,
            retrievalConfiguration={
                "vectorSearchConfiguration": {
                    "numberOfResults": num_results,
                    "overrideSearchType": "HYBRID",
                }
            },
        )

        # Process retrieval results
        text = ""
        for idx, result in enumerate(response.get("retrievalResults", []), 1):
            content = result.get("content", {}).get("text", "")
            text += f"Documento {idx}: \n- {content}\n"

        # Define system prompt
        system_prompt = f"""Eres un experto en finanzas y analisis de riesgo. Se te entregara un contexto y una serie de documentos, la idea esque basado en el contexto logres resumir los documentos.

Sigue los sigueintes pasos:

1. Lee los documentos, que son notas personales de una persona sobre sus finanzas.
2. Basado en la informacion de los documentos, intenta obtener la informacion mas util.
3. Sintetiza los documentos en un solo documento con un titulo general y una descripcion mas general de la situacion financiera de la persona. {specific_system_prompt}
4. El formato esperado es:

## {{titulo}}

- {{informacion_util}}

Recuerda pensar paso a paso y ser consico siguiendo el formato unicamente en el punteo.
"""
        user_input = "\n<Documentos> \n" + text + "\n</Documentos>"

        # Process with the model
        return self.invoke(system_prompt, user_input)


def obtener_deuda_total_y_documentos(json_dict):
    bienes_raices = json_dict.get("bienesRaices", [])
    vehiculos = json_dict.get("vehiculos", [])
    cmf_data = json_dict.get("cmf", {})

    direct_debt_details = cmf_data.get("direct_debt_details", [])
    indirect_debt_details = cmf_data.get("indirect_debt_details", [])

    deuda_total = 0
    cantidad_documentos = 0
    detalle_documentos_no_pagados = []

    # Procesar deuda directa
    if direct_debt_details:
        for detalle in direct_debt_details:
            deuda = (
                detalle.get("total_credit", "0")
                .replace("$", "")
                .replace(".", "")
                .replace(",", "")
            )
            deuda_total += int(deuda)
            cantidad_documentos += 1

            current = (
                detalle.get("current", "0")
                .replace("$", "")
                .replace(".", "")
                .replace(",", "")
            )
            if int(current) > 0:
                detalle_documentos_no_pagados.append(
                    {
                        "tipo": "directa",
                        "institucion": detalle.get(
                            "financial_institution", "Desconocida"
                        ),
                        "cantidad": int(current),
                    }
                )

    # Procesar deuda indirecta
    if indirect_debt_details:
        for detalle in indirect_debt_details:
            deuda_indirecta = (
                detalle.get("total_credit", "0")
                .replace("$", "")
                .replace(".", "")
                .replace(",", "")
            )
            deuda_total += int(deuda_indirecta)
            cantidad_documentos += 1

            current = (
                detalle.get("current", "0")
                .replace("$", "")
                .replace(".", "")
                .replace(",", "")
            )
            if int(current) > 0:
                detalle_documentos_no_pagados.append(
                    {
                        "tipo": "indirecta",
                        "institucion": detalle.get(
                            "financial_institution", "Desconocida"
                        ),
                        "cantidad": int(current),
                    }
                )

    valoracion_bienes_raices = 0
    valoracion_vehiculos = 0

    # Calcular valoración de bienes raíces
    if bienes_raices:
        for bien in bienes_raices:
            print(bien)
            print(bien.keys())
            lista_keys = list(bien.keys())
            print(lista_keys)
            avaluo = bien.get("Avalúo Fiscal", "0")
            avaluo = avaluo.replace("$", "").replace(".", "").replace(",", "")
            valoracion_bienes_raices += int(avaluo)

    # Calcular valoración de vehículos
    if vehiculos:
        for vehiculo in vehiculos:
            precio = vehiculo.get("Precio", 0)
            valoracion_vehiculos += int(precio)

    nombre = json_dict.get("nombre", "No especificado")
    edad = json_dict.get("edad", "No especificado")

    return {
        "deuda_total": deuda_total,
        "cantidad_documentos": cantidad_documentos,
        "valoracion_bienes_raices": valoracion_bienes_raices,
        "valoracion_vehiculos": valoracion_vehiculos,
        "nombre": nombre,
        "edad": edad,
        "detalle_documentos_no_pagados": detalle_documentos_no_pagados,
    }
