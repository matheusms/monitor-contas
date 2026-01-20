import os
import time
import json
import google.generativeai as genai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    print("Error: GEMINI_API_KEY not found in environment variables. Please set it in a .env file or export it.")
    exit(1)

genai.configure(api_key=api_key)

def upload_to_gemini(path, mime_type=None):
    """Uploads the given file to Gemini.

    See https://ai.google.dev/gemini-api/docs/prompting_with_media
    """
    file = genai.upload_file(path, mime_type=mime_type)
    print(f"Uploaded file '{file.display_name}' as: {file.uri}")
    return file

def wait_for_files_active(files):
    """Waits for the given files to be active.

    Some files uploaded to the Gemini API need to be processed before they can
    be used as prompt inputs. The status will be in the "processing" state.
    This function waits for a file to become "active".
    """
    print("Waiting for file processing...")
    for name in (file.name for file in files):
        file = genai.get_file(name)
        while file.state.name == "PROCESSING":
            print(".", end="", flush=True)
            time.sleep(10)
            file = genai.get_file(name)
        if file.state.name != "ACTIVE":
            raise Exception(f"File {file.name} failed to process")
    print("...all files ready")

def extract_data(pdf_path):
    # Upload the PDF
    files = [upload_to_gemini(pdf_path, mime_type="application/pdf")]
    
    # Wait for processing
    wait_for_files_active(files)

    # Create the model
    # Using gemini-1.5-flash for speed and efficiency for this task
    model = genai.GenerativeModel(
        model_name="gemini-flash-latest",
        generation_config={
            "response_mime_type": "application/json",
        }
    )

    prompt = """
    Analise esta conta de luz da Light RJ (PDF) e extraia os dados abaixo em formato JSON.
    Se algum campo não for encontrado, use null.
    
    Campos requeridos:
    - valor_total (number): Valor total a pagar da conta.
    - mes_referencia (string): Mês de referência da conta (ex: "JANEIRO/2024").
    - vencimento (string): Data de vencimento (ex: "20/01/2024").
    - consumo_kwh (number): Total de consumo faturado em kWh.
    - codigo_instalacao (string): Código da instalação/cliente.
    - leitura_atual (string): Data da leitura atual.
    - leitura_proxima (string): Previsão da próxima leitura.
    - bandeira_tarifaria (string): Cor da bandeira tarifária vigente (ex: "Verde", "Amarela", "Vermelha").
    - adicional_bandeira (number): Valor adicional cobrado devido à bandeira (se houver), ou null.
    - detalhes_tarifas (list of objects): Lista com itens da composição do faturamento (descrição e valor).
    """

    print("Sending prompt to Gemini...")
    response = model.generate_content([files[0], prompt])
    
    print("Response received.")
    return response.text

def process_all_faturas():
    import glob

    faturas_dir = "Faturas"
    history_file = "bills_history.json"

    # Ensure Faturas directory exists
    if not os.path.isdir(faturas_dir):
        print(f"Directory '{faturas_dir}' not found.")
        return 0

    # Load existing history
    history = []
    if os.path.exists(history_file):
        try:
            with open(history_file, "r", encoding="utf-8") as f:
                history = json.load(f)
        except json.JSONDecodeError:
            print("Error reading history file. Starting fresh.")
    
    # Create a set of processed filenames for quick lookup
    # Normalize paths/names to avoid duplicates on slightly different paths
    processed_files = {item.get("arquivo_origem") for item in history if item.get("arquivo_origem")}

    pdf_files = glob.glob(os.path.join(faturas_dir, "*.pdf"))
    
    if not pdf_files:
        print(f"No PDF files found in '{faturas_dir}'.")
        return 0

    print(f"Found {len(pdf_files)} PDF files.")
    
    new_data_count = 0

    for pdf_path in pdf_files:
        filename = os.path.basename(pdf_path)
        
        if filename in processed_files:
            continue

        print(f"\nProcessing '{filename}'...")
        try:
            json_result = extract_data(pdf_path)
            
            # Basic validation and parsing
            data = json.loads(json_result)
            
            # Add metadata
            data["arquivo_origem"] = filename
            data["data_processamento"] = time.strftime("%Y-%m-%d %H:%M:%S")

            history.append(data)
            processed_files.add(filename)
            new_data_count += 1
            
            # Save incrementally (optional, but safer)
            with open(history_file, "w", encoding="utf-8") as f:
                json.dump(history, f, indent=4, ensure_ascii=False)
                
            print(f"Successfully processed '{filename}'")
            # Avoid hitting rate limits too hard
            time.sleep(2) 

        except Exception as e:
            print(f"Failed to process '{filename}': {e}")

    print(f"\nProcessing complete. {new_data_count} new bills added.")
    print(f"Total entries in history: {len(history)}")
    return new_data_count

if __name__ == "__main__":
    process_all_faturas()

