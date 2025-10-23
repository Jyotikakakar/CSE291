#!/usr/bin/env python3
import os
import sys
import subprocess


def check_env():
    if not os.path.exists(".env"):
        print("Creating .env file with Gemini defaults")
        with open(".env", 'w') as f:
            f.write("# Gemini Configuration\n")
            f.write("GEMINI_API_KEY=your_api_key_here\n")
            f.write("GEMINI_MODEL=your_model_here\n")
        print("Created .env file")
        print("Please add your Gemini API key to the .env file")
        return False
    
    from dotenv import load_dotenv
    load_dotenv()
    
    api_key = os.getenv("GEMINI_API_KEY")
    model = os.getenv("GEMINI_MODEL")
    
    if not api_key or api_key == "your_api_key_here":
        print("GEMINI_API_KEY not found in .env file!")
        print("Please add your Gemini API key to the .env file")
        return False
    
    if not model:
        print("GEMINI_MODEL not found in .env file!")
        print("Please add your Gemini model to the .env file")
        return False
    
    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        model_instance = genai.GenerativeModel(model)
        
        # Test the API
        response = model_instance.generate_content("Hello")
        if response.text:
            print("✓ Gemini API is working")
            print(f"Model: {model}")
            return True
        else:
            print("No response from Gemini API")
            return False
    except Exception as e:
        print(f"Error testing Gemini API: {str(e)}")
        return False
    
    return True


def check_dependencies():
    try:
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
    
    print("2: Checking Gemini configuration")
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