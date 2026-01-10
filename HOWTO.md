# Thomas RAG Application - Windows Setup Guide

## Overview
This application provides RAG (Retrieval-Augmented Generation) functionality using ChromaDB for vector storage and Ollama for LLM inference. There are several Windows-specific issues that need to be addressed for proper operation.

---

## Critical Windows Issues and Solutions

### 1. **Missing Python Dependencies**

**Problem:** The `pyproject.toml` only lists `beautifulsoup4` and `bs4`, but the application requires `chromadb` which is not declared as a dependency.

**Solution:** Install missing dependencies manually:

```powershell
# Activate your virtual environment first
.venv\Scripts\activate

# Install required packages
pip install chromadb
```

**Permanent Fix:** Add chromadb to dependencies in `pyproject.toml`:
```toml
[project]
dependencies = [
    "beautifulsoup4>=4.12,<5",
    "bs4>=0.0.2",
    "chromadb>=0.4.0",
]
```

---

### 2. **Ollama Connection Issues on Windows**

**Problem:** The application cannot connect to Ollama server on Windows due to:
- Windows networking treats `localhost` differently than Unix systems
- Windows Firewall may block local connections on port 11434
- The connection error messages are not helpful for diagnosing the issue

**Root Causes:**
1. `urlparse("http://localhost:11434").hostname` may return `None` on some Windows configurations
2. Windows DNS resolution for `localhost` can be problematic
3. Windows Firewall blocks Python from making local HTTP connections by default

**Solutions Implemented in Code:**
- Force resolution of `localhost` to `127.0.0.1` (direct IP address)
- Add explicit error handling with Windows-specific troubleshooting guidance
- Provide clear connection diagnostics

**Windows Firewall Configuration:**

If Python cannot connect to Ollama, you need to allow Python through Windows Firewall:

```powershell
# Run PowerShell as Administrator, then execute:

# Allow inbound connections for Python
netsh advfirewall firewall add rule name="Python Local Server Access" dir=in action=allow program="C:\Users\YourUsername\AppData\Local\Programs\Python\Python313\python.exe" enable=yes

# Allow outbound connections for Python (if needed)
netsh advfirewall firewall add rule name="Python Local Client Access" dir=out action=allow program="C:\Users\YourUsername\AppData\Local\Programs\Python\Python313\python.exe" enable=yes

# If using a virtual environment, also add:
netsh advfirewall firewall add rule name="Python Venv Local Access" dir=in action=allow program="C:\path\to\your\project\.venv\Scripts\python.exe" enable=yes
```

**Important:** Replace the paths with your actual Python installation paths. To find your Python path:
```powershell
# In your activated virtual environment:
python -c "import sys; print(sys.executable)"
```

**Alternative Quick Test (Temporary):**
```powershell
# Disable Windows Firewall temporarily (NOT RECOMMENDED for production)
netsh advfirewall set allprofiles state off

# After testing, re-enable it:
netsh advfirewall set allprofiles state on
```

---

### 3. **Ollama Server Not Running**

**Problem:** The Ollama service may not be running on Windows.

**Solution:** 

```powershell
# Check if Ollama is running:
netstat -ano | findstr :11434

# If nothing appears, start Ollama:
ollama serve

# In a separate terminal, verify the model is available:
ollama list

# If llama3.1 is not installed:
ollama pull llama3.1
```

---

### 4. **SSL Certificate Verification Errors**

**Problem:** When fetching RSS feeds (in `finma.py`), Windows Python installations may not have proper SSL certificates, causing:
```
[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: unable to get local issuer certificate
```

**Solution Already Implemented:** The code now bypasses SSL verification for the RSS feed fetch. This is acceptable for development but should be fixed properly in production.

**Production Fix (Optional):**
```powershell
pip install certifi
```

Then update the code to use certifi's certificate bundle:
```python
import certifi
ssl_context = ssl.create_default_context(cafile=certifi.where())
```

---

### 5. **Path Handling Differences**

**Problem:** Windows uses backslashes (`\`) for paths, which can cause issues with string literals and path operations.

**Solution Already Implemented:** The code uses `pathlib.Path` throughout, which handles cross-platform path operations correctly:
```python
from pathlib import Path
project_root = Path(__file__).resolve().parent.parent.parent
finma_path = project_root / "data" / "finma.txt"
```

**Note:** Always use `Path` objects instead of string concatenation for file paths.

---

## Complete Setup Instructions for Windows

### Step 1: Prerequisites

1. **Install Python 3.13+**
   - Download from https://python.org
   - During installation, check "Add Python to PATH"

2. **Install Ollama**
   - Download from https://ollama.ai
   - Install and start the Ollama application
   - It should appear in your system tray

3. **Verify Ollama Installation**
   ```powershell
   ollama --version
   ollama list
   ollama pull llama3.1
   ```

### Step 2: Project Setup

1. **Clone/Download the project**
   ```powershell
   cd C:\your\projects\folder
   # (project should be here)
   ```

2. **Create and activate virtual environment**
   ```powershell
   python -m venv .venv
   .venv\Scripts\activate
   ```

3. **Install dependencies**
   ```powershell
   # Install declared dependencies
   pip install -e .
   
   # Install missing dependencies
   pip install chromadb
   ```

### Step 3: Configure Windows Firewall

Run PowerShell **as Administrator**:

```powershell
# Get your Python executable path
$pythonPath = python -c "import sys; print(sys.executable)"
Write-Host "Python path: $pythonPath"

# Add firewall rules
netsh advfirewall firewall add rule name="Python Local Server Access" dir=in action=allow program="$pythonPath" enable=yes
netsh advfirewall firewall add rule name="Python Local Client Access" dir=out action=allow program="$pythonPath" enable=yes
```

### Step 4: Verify Ollama is Accessible

```powershell
# Test Ollama API directly
curl http://127.0.0.1:11434/api/version

# Should return JSON with version info
```

If this fails:
- Ensure Ollama is running (check system tray)
- Try restarting Ollama
- Check if another application is using port 11434: `netstat -ano | findstr :11434`

### Step 5: Run the Application

```powershell
# Make sure you're in the project root and venv is activated
cd C:\path\to\thomas
.venv\Scripts\activate

# Run the vector database RAG demo
python src\thomas\vdb.py
```

---

## Testing Connection Issues

If you still have connection problems, create a test script:

**test_ollama.py:**
```python
import http.client
import json

def test_ollama_connection():
    try:
        conn = http.client.HTTPConnection("127.0.0.1", 11434, timeout=10)
        conn.request("GET", "/api/version")
        resp = conn.getresponse()
        data = resp.read().decode("utf-8")
        print(f"✓ Connected successfully!")
        print(f"Response: {data}")
        conn.close()
        return True
    except ConnectionRefusedError:
        print("✗ Connection refused - Ollama is not running")
        return False
    except TimeoutError:
        print("✗ Connection timeout - check firewall settings")
        return False
    except Exception as e:
        print(f"✗ Connection failed: {e}")
        return False

if __name__ == "__main__":
    print("Testing Ollama connection on Windows...")
    print("Attempting connection to 127.0.0.1:11434...")
    test_ollama_connection()
```

Run it:
```powershell
python test_ollama.py
```

---

## Environment Variables (Optional)

You can customize the application behavior with environment variables:

```powershell
# Set custom Ollama URL (if running on different port)
$env:OLLAMA_BASE_URL = "http://127.0.0.1:11434"

# Set custom model
$env:OLLAMA_MODEL = "llama3.1:8b"

# For persistent settings, add to your PowerShell profile:
# notepad $PROFILE
# Add the lines above to the file
```

---

## Common Error Messages and Solutions

### Error: "Failed to create connection to 127.0.0.1:11434"
**Cause:** Ollama is not running or firewall is blocking
**Solution:** 
1. Start Ollama: `ollama serve`
2. Configure firewall (see Step 3 above)

### Error: "No module named 'chromadb'"
**Cause:** Missing dependency
**Solution:** `pip install chromadb`

### Error: "[SSL: CERTIFICATE_VERIFY_FAILED]"
**Cause:** SSL certificate issues when fetching RSS feeds
**Solution:** Already fixed in code - SSL verification is disabled for the RSS fetch

### Error: "FileNotFoundError: data/finma.txt not found"
**Cause:** Running script from wrong directory
**Solution:** Always run from project root or ensure `data/finma.txt` exists

### Error: "Ollama generate failed (404)"
**Cause:** Model not installed
**Solution:** `ollama pull llama3.1`

---

## Architecture Notes

### File Structure
```
thomas/
├── data/
│   ├── finma.txt          # RSS feed data
│   └── chroma/            # ChromaDB persistent storage
├── src/thomas/
│   ├── vdb.py            # Main RAG demo (ChromaDB + Ollama)
│   ├── finma.py          # RSS feed fetcher
│   ├── full_rag.py       # Full RAG implementation
│   └── load.py           # Data loader
└── pyproject.toml        # Project dependencies (INCOMPLETE)
```

### Data Flow
1. `finma.py` - Fetches RSS feeds from finma.ch → saves to `data/finma.txt`
2. `vdb.py` - Loads data → Creates embeddings → Stores in ChromaDB → Queries with user input → Sends to Ollama
3. Ollama receives context + query → Generates response

### Network Flow (Windows-specific)
```
Python Script (vdb.py)
    ↓
Windows Firewall Check
    ↓
127.0.0.1:11434 (loopback interface)
    ↓
Ollama Server (running locally)
    ↓
llama3.1 model inference
    ↓
Response back to Python
```

---

## Troubleshooting Checklist

- [ ] Python 3.13+ installed
- [ ] Virtual environment activated
- [ ] All dependencies installed (`pip list` shows chromadb)
- [ ] Ollama installed and running (`ollama list` works)
- [ ] Model downloaded (`ollama list` shows llama3.1)
- [ ] Firewall configured (Python allowed on port 11434)
- [ ] Can connect to Ollama (`curl http://127.0.0.1:11434/api/version`)
- [ ] data/finma.txt file exists
- [ ] Running from correct directory (project root)

---

## Production Recommendations

1. **Add proper dependency management:**
   - Update `pyproject.toml` to include ALL required packages
   - Run `pip freeze > requirements.txt` for documentation

2. **SSL Certificate handling:**
   - Use `certifi` package for proper certificate verification
   - Don't disable SSL verification in production

3. **Error handling:**
   - Add retry logic for network requests
   - Implement proper logging instead of print statements
   - Add graceful degradation if Ollama is unavailable

4. **Security:**
   - Don't disable Windows Firewall - use specific rules
   - Consider authentication if exposing Ollama endpoint
   - Validate and sanitize all user inputs

5. **Configuration:**
   - Use configuration files instead of environment variables
   - Document all configurable parameters
   - Provide sensible defaults

---

## Additional Resources

- **Ollama Documentation:** https://github.com/ollama/ollama/blob/main/docs/windows.md
- **ChromaDB Documentation:** https://docs.trychroma.com/
- **Windows Firewall cmdlets:** https://learn.microsoft.com/en-us/powershell/module/netsecurity/

---

## Support

If you continue to experience issues after following this guide:

1. Check that all prerequisites are met
2. Run the test script to isolate the problem
3. Check Windows Event Viewer for firewall blocks
4. Verify Ollama logs (usually in `%LOCALAPPDATA%\Ollama\logs`)
5. Try running both Python and Ollama as Administrator (temporary test only)

**Last Updated:** January 2026
