# Quick Start Guide for Windows Users

## ⚠️ Before You Start

This application requires **Ollama** and **Python 3.13+** to be installed on your Windows machine. It will NOT work without these prerequisites.

---

## Fast Setup (5 Minutes)

### 1. Install Prerequisites

**Python 3.13+:**
- Download and install from [python.org](https://python.org)
- ✅ Check "Add Python to PATH" during installation

**Ollama:**
- Download and install from [ollama.ai](https://ollama.ai)
- After installation, open PowerShell and run:
  ```powershell
  ollama pull llama3.1
  ```

### 2. Setup Project

Open PowerShell in the project directory:

```powershell
# Create virtual environment
python -m venv .venv

# Activate it
.venv\Scripts\activate

# Install dependencies
pip install -e .
pip install chromadb
```

### 3. Configure Windows Firewall

**Run PowerShell as Administrator:**

```powershell
# Find your Python path
$pythonPath = & ".venv\Scripts\python.exe" -c "import sys; print(sys.executable)"

# Add firewall rule
netsh advfirewall firewall add rule name="Python Local Access" dir=in action=allow program="$pythonPath" enable=yes
```

### 4. Start Ollama

In a **separate** PowerShell window:

```powershell
ollama serve
```

Keep this window open while using the application.

### 5. Test Your Setup

```powershell
# In your project directory with venv activated
python test_windows_connection.py
```

If all tests pass ✓, you're ready to go!

### 6. Run the Application

```powershell
python src\thomas\vdb.py
```

---

## Common Issues

### "Connection refused" Error

**Problem:** Ollama is not running  
**Fix:** Run `ollama serve` in a separate terminal

### "Connection timeout" Error

**Problem:** Windows Firewall is blocking Python  
**Fix:** Configure firewall (see step 3 above)

### "No module named 'chromadb'"

**Problem:** Missing dependency  
**Fix:** Run `pip install chromadb`

### "Model 'llama3.1' not found"

**Problem:** Model not installed  
**Fix:** Run `ollama pull llama3.1`

---

## Need More Help?

See the detailed **[HOWTO.md](HOWTO.md)** file for:
- Complete troubleshooting guide
- Architecture explanation
- Advanced configuration options
- Security recommendations

---

## Verification Checklist

Before running the app, verify:

- [ ] Python 3.13+ installed (`python --version`)
- [ ] Ollama installed (`ollama --version`)
- [ ] Model downloaded (`ollama list` shows llama3.1)
- [ ] Virtual environment activated (prompt shows `(.venv)`)
- [ ] ChromaDB installed (`pip show chromadb`)
- [ ] Firewall configured (Python allowed)
- [ ] Ollama running (`ollama serve` in separate window)
- [ ] Test script passes (`python test_windows_connection.py`)

If all checkboxes are ✅, you're good to go!

---

**Last Updated:** January 2026
