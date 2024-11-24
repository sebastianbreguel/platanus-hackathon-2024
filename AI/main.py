import json
import argparse
from utils import ModelClient, obtener_deuda_total_y_documentos
from prompts import CONSOLIDADOR, RESUMIDOR, USER_PERFONAL_INFORMATION, USER_FINANCIAL_INFORMATION, RECOMENDADOR, PUNTAJERO

def parse_arguments():
    parser = argparse.ArgumentParser(description='Process financial information')
    parser.add_argument('--edad', type=int, required=True, help='Edad del usuario')
    parser.add_argument('--ingreso_mensual', type=int, required=True, help='Ingreso mensual del usuario')
    parser.add_argument('--enfoque', type=str, required=True, help='Enfoque del análisis')
    return parser.parse_args()

def load_documents(docs):
    json_strings = {}
    for doc in docs:
        key = doc.replace(".txt", "")
        with open(f"data_examples/{doc}", 'r') as file:
            value = file.read()
        value = json.loads(value)
        json_strings[key] = value
    return json_strings

def main():
    # Parse arguments
    args = parse_arguments()
    edad = args.edad
    ingreso_mensual = args.ingreso_mensual
    enfoque = args.enfoque

    # Configure documents
    docs = ['cmf.txt', 'bienesRaices.txt', 'vehiculos.txt']
    json_strings = load_documents(docs)
    steps = obtener_deuda_total_y_documentos(json_strings)
    # Initialize model client
    model_client = ModelClient()
    retrieved_docs = ""
    
    print("# 1. Consolidate information")
    user_prompt = USER_PERFONAL_INFORMATION.format(edad=edad, ingreso_mensual=ingreso_mensual, enfoque=enfoque) + USER_FINANCIAL_INFORMATION.format(**json_strings) + "\n<Documentos> \n" + retrieved_docs + "\n</Documentos>"
    rewrited_information = model_client.invoke(CONSOLIDADOR, user_prompt)
    
    print("# 2. Summarize information")
    user_prompt = USER_PERFONAL_INFORMATION.format(edad=edad, ingreso_mensual=ingreso_mensual, enfoque=enfoque) + rewrited_information + "\n<Documentos> \n" + retrieved_docs + "\n</Documentos>"
    response = model_client.invoke(RESUMIDOR, user_prompt)
    resumen_general = response.split("<Resumen general>")[1].split("</Resumen general>")[0].strip()

    print("# 3. Future recommendations")
    user_prompt = USER_PERFONAL_INFORMATION.format(edad=edad, ingreso_mensual=ingreso_mensual, enfoque=enfoque) + resumen_general + "\n<Documentos> \n" + retrieved_docs + "\n</Documentos>"
    categories_recomendaciones = model_client.invoke(RECOMENDADOR, user_prompt)
    categorias = categories_recomendaciones.split("<Categorias>")[1].split("</Categorias>")[0].strip()
    recomendaciones = categories_recomendaciones.split("<Recomendaciones>")[1].split("</Recomendaciones>")[0].strip()
    
    print("# 4. Score")
    system_prompt = PUNTAJERO
    user_prompt = USER_PERFONAL_INFORMATION.format(edad=edad, ingreso_mensual=ingreso_mensual, enfoque=enfoque) + resumen_general + "\n## Recomendaciones:\n" + recomendaciones
    puntaje_final = model_client.invoke(system_prompt, user_prompt)
    razon_puntaje = puntaje_final.split("<Razonamiento>")[1].split("</Razonamiento>")[0].strip()
    puntaje = puntaje_final.split("<Puntaje>")[1].split("</Puntaje>")[0].strip()
    
    # Generate JSON output
    json_output = {
        "resumen_general": resumen_general,
        "categorias": categorias,
        "recomendaciones": recomendaciones,
        "puntaje_final": 10-int(puntaje),
        "razon_puntaje": razon_puntaje
    }
    return json_output


if __name__ == "__main__":
    result = main()
    print(json.dumps(result, indent=2, ensure_ascii=False))