### Step 1: Install Ollama
```bash
curl -L https://ollama.com/download/Ollama-darwin.zip -o Ollama.zip
unzip Ollama.zip
mv Ollama.app /Applications/
rm Ollama.zip

echo 'export PATH="/Applications/Ollama.app/Contents/Resources:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

### Step 2: Start Ollama & Pull Model

```bash
# Start Ollama (keeps running in background)
ollama serve &

# Pull the AI model (4.7GB download, one-time)
ollama pull llama3.1:8b

# Test it works
ollama run llama3.1:8b "Hello!"
```

### Step 3: Install Python Dependencies

```bash
pip install -r requirements.txt
```

### Step 4: Run Everything!

```bash
python3 run.py
```

