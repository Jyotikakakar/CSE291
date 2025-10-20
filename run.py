#!/usr/bin/env python3
import os
import sys
import subprocess


def check_env():
    if not os.path.exists(".env"):
        print("Creating .env file with Ollama defaults")
        with open(".env", 'w') as f:
            f.write("# Ollama Configuration\n")
            f.write("OLLAMA_HOST=http://localhost:11434\n")
            f.write("OLLAMA_MODEL=llama3.1:8b\n")
        print("Created .env file")
    
    import requests
    from dotenv import load_dotenv
    load_dotenv()
    
    host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    model = os.getenv("OLLAMA_MODEL", "llama3.1:8b")
    
    try:
        response = requests.get(f"{host}/api/tags", timeout=2)
        if response.status_code == 200:
            models = response.json().get('models', [])
            model_names = [m['name'] for m in models]
            
            print("✓ Ollama is running")
            
            if not any(model in name for name in model_names):
                print(f"\nModel '{model}' not found!")
                print(f"   Available models: {', '.join(model_names) if model_names else 'None'}")
                print(f"\n   To install the model:")
                print(f"   $ ollama pull {model}")
                return False
            
            print(f"Model '{model}' is available")
            return True
    except requests.exceptions.ConnectionError:
        print("\nOllama is not running!")
        return False
    except Exception as e:
        print(f"\nError checking Ollama: {str(e)}")
        return False
    
    return True


def check_dependencies():
    try:
        import requests
        import datasets
        import matplotlib
        import numpy
        from dotenv import load_dotenv
        return True
    except ImportError as e:
        print("Missing dependencies!")
        print()
        print("Installing required packages")
        subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        return True


def main():
    print("MEETING SUMMARIZER AGENT - PHASE 1")
    print()
    
    print("1: Checking dependencies")
    if not check_dependencies():
        return
    print("Dependencies OK")
    print()
    
    print("2: Checking Ollama configuration")
    if not check_env():
        return
    print()
    
    print("3: Loading meeting transcripts")
    if not os.path.exists("data/metadata.json"):
        print()
        print("No data found. Choose an option:")
        print("  1. Load AMI dataset from HuggingFace (real meetings)")
        print("  2. Create synthetic sample transcripts (quick test)")
        print()
        choice = input("Your choice [1/2]: ").strip()
        
        if choice == "1":
            print()
            print("Loading AMI dataset")
            from load_data import load_ami_transcripts
            load_ami_transcripts(num_samples=20)
        else:
            print()
            print("Creating synthetic samples")
            from load_data import create_sample_transcripts
            create_sample_transcripts()
    else:
        print("Data already loaded")
    print()
    
    print("Step 4: Running evaluation...")
    print()
    
    from evaluate import run_evaluation, print_sample_summary
    run_evaluation()
    print_sample_summary()
    
    print()
    print("✓ COMPLETE!")
    print()
    print("Results saved to:")
    print("  - results/evaluation.json (detailed results)")
    print("  - results/latency_cdf.png (latency distribution)")
    print("  - results/extraction_counts.png (items extracted)")
    print("  - results/success_rate.png (success vs failure)")
 


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nError: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)