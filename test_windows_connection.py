#!/usr/bin/env python3
"""
Windows Connection Diagnostic Tool for Ollama
This script helps diagnose connection issues between Python and Ollama on Windows.
"""

import http.client
import json
import sys
import socket
from urllib.parse import urlparse


def test_dns_resolution():
    """Test if localhost resolves correctly."""
    print("\n[1/5] Testing DNS resolution...")
    try:
        localhost_ip = socket.gethostbyname("localhost")
        print(f"  ✓ 'localhost' resolves to: {localhost_ip}")
        return True
    except socket.gaierror as e:
        print(f"  ✗ Failed to resolve 'localhost': {e}")
        print("  → Try using 127.0.0.1 directly instead")
        return False


def test_port_open():
    """Test if port 11434 is accepting connections."""
    print("\n[2/5] Testing if port 11434 is open...")
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        result = sock.connect_ex(("127.0.0.1", 11434))
        sock.close()
        
        if result == 0:
            print("  ✓ Port 11434 is open and accepting connections")
            return True
        else:
            print("  ✗ Port 11434 is not accessible")
            print("  → Ollama may not be running")
            print("  → Run 'ollama serve' in a separate terminal")
            return False
    except Exception as e:
        print(f"  ✗ Socket error: {e}")
        return False


def test_http_connection():
    """Test HTTP connection to Ollama."""
    print("\n[3/5] Testing HTTP connection to Ollama...")
    try:
        conn = http.client.HTTPConnection("127.0.0.1", 11434, timeout=10)
        conn.request("GET", "/api/version")
        resp = conn.getresponse()
        data = resp.read().decode("utf-8")
        conn.close()
        
        if resp.status == 200:
            print(f"  ✓ Successfully connected to Ollama")
            try:
                version_info = json.loads(data)
                print(f"  → Ollama version: {version_info.get('version', 'unknown')}")
            except:
                print(f"  → Response: {data[:100]}")
            return True
        else:
            print(f"  ✗ HTTP request failed with status {resp.status}")
            return False
            
    except ConnectionRefusedError:
        print("  ✗ Connection refused")
        print("  → Ollama is not running on port 11434")
        print("  → Start Ollama: 'ollama serve'")
        return False
    except TimeoutError:
        print("  ✗ Connection timeout")
        print("  → Windows Firewall may be blocking the connection")
        print("  → See HOWTO.md for firewall configuration")
        return False
    except Exception as e:
        print(f"  ✗ Connection failed: {e}")
        return False


def test_ollama_models():
    """Check if models are available."""
    print("\n[4/5] Checking available models...")
    try:
        conn = http.client.HTTPConnection("127.0.0.1", 11434, timeout=10)
        conn.request("GET", "/api/tags")
        resp = conn.getresponse()
        data = resp.read().decode("utf-8")
        conn.close()
        
        if resp.status == 200:
            models_info = json.loads(data)
            models = models_info.get("models", [])
            
            if models:
                print(f"  ✓ Found {len(models)} model(s):")
                for model in models:
                    name = model.get("name", "unknown")
                    size = model.get("size", 0)
                    size_gb = size / (1024**3) if size else 0
                    print(f"    - {name} ({size_gb:.1f} GB)")
                
                # Check for llama3.1
                llama_models = [m for m in models if "llama" in m.get("name", "").lower()]
                if llama_models:
                    print("  ✓ llama3.1 or compatible model found")
                    return True
                else:
                    print("  ⚠ No llama models found")
                    print("  → Install llama3.1: 'ollama pull llama3.1'")
                    return True
            else:
                print("  ⚠ No models installed")
                print("  → Install a model: 'ollama pull llama3.1'")
                return False
        else:
            print(f"  ✗ Failed to fetch models (status {resp.status})")
            return False
            
    except Exception as e:
        print(f"  ✗ Failed to check models: {e}")
        return False


def test_ollama_generate():
    """Test actual generation with Ollama."""
    print("\n[5/5] Testing LLM generation...")
    try:
        conn = http.client.HTTPConnection("127.0.0.1", 11434, timeout=30)
        
        body = {
            "model": "llama3.1",
            "prompt": "Say 'Hello from Windows!' and nothing else.",
            "stream": False
        }
        payload = json.dumps(body).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        
        conn.request("POST", "/api/generate", body=payload, headers=headers)
        resp = conn.getresponse()
        data = resp.read().decode("utf-8")
        conn.close()
        
        if resp.status == 200:
            result = json.loads(data)
            response_text = result.get("response", "").strip()
            print(f"  ✓ Generation successful!")
            print(f"  → Response: {response_text}")
            return True
        elif resp.status == 404:
            print("  ✗ Model 'llama3.1' not found")
            print("  → Install the model: 'ollama pull llama3.1'")
            return False
        else:
            print(f"  ✗ Generation failed (status {resp.status})")
            print(f"  → Error: {data[:200]}")
            return False
            
    except Exception as e:
        print(f"  ✗ Generation test failed: {e}")
        return False


def print_summary(results):
    """Print summary and recommendations."""
    print("\n" + "="*60)
    print("DIAGNOSTIC SUMMARY")
    print("="*60)
    
    passed = sum(results.values())
    total = len(results)
    
    print(f"\nTests passed: {passed}/{total}")
    
    if passed == total:
        print("\n✓ All tests passed! Your system is ready to use.")
        print("\nYou can now run: python src/thomas/vdb.py")
    else:
        print("\n✗ Some tests failed. Recommendations:\n")
        
        if not results["dns"]:
            print("→ DNS Issue: Use 127.0.0.1 instead of localhost in your code")
        
        if not results["port"]:
            print("→ Ollama Not Running: Start Ollama with 'ollama serve'")
        
        if not results["http"]:
            print("→ Connection Blocked: Configure Windows Firewall (see HOWTO.md)")
            print("  Run as Administrator:")
            print("  netsh advfirewall firewall add rule name=\"Python Local Access\"")
            print("    dir=in action=allow program=\"C:\\Path\\To\\python.exe\" enable=yes")
        
        if not results["models"]:
            print("→ No Models: Install a model with 'ollama pull llama3.1'")
        
        if not results["generate"]:
            print("→ Generation Failed: Check model installation and Ollama logs")
    
    print("\nFor detailed troubleshooting, see HOWTO.md")
    print("="*60)


def main():
    """Run all diagnostic tests."""
    print("="*60)
    print("Windows-Ollama Connection Diagnostic Tool")
    print("="*60)
    print("\nThis tool will test your Ollama connection on Windows.")
    print("Testing connection to: http://127.0.0.1:11434")
    
    results = {
        "dns": test_dns_resolution(),
        "port": test_port_open(),
        "http": test_http_connection(),
        "models": test_ollama_models(),
        "generate": test_ollama_generate(),
    }
    
    print_summary(results)
    
    return 0 if all(results.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
