## Goal
On **Windows**, remove _all_ existing Python installs you don’t want, then install **one clean Python 3.13**, plus **uv**, and use **uv** for all virtual environments going forward.
Below are **safe, automatable PowerShell scripts** with a couple of “choose your level of aggression” options.
Important notes This is written for Windows 10/11 with PowerShell and ideally winget available.

## 0) Open an elevated PowerShell
1. Start Menu → type **PowerShell**
2. Right-click → **Run as administrator**

All scripts below assume admin rights.
## 1) Audit what Python you currently have (safe)
Run this first to see what you’re dealing with:``` powershell
# Show what the Python launcher knows
py -0p 2>$null

# Show which python.exe is found in PATH
where.exe python 2>$null

# Show Windows "App Execution Aliases" python shims (often from Microsoft Store)
Get-ItemProperty "HKCU:\Software\Microsoft\Windows\CurrentVersion\App Paths\python.exe" -ErrorAction SilentlyContinue
```

If where python shows something like:
...WindowsApps\python.exe → you’re hitting the Microsoft Store alias, not a real install.
 
2) Remove Python installs (automated via winget, preferred)
This is the cleanest uninstall path for CPython installed via the official installer/winget.
2.1 List python-related winget packages``` powershell
winget list --name Python
winget list --name "Python Launcher"
winget list --name uv
```

2.2 Uninstall all Python versions via winget (interactive confirmation disabled)
This script tries to remove all CPython packages it finds:``` powershell
$pkgs = winget list --name Python | Select-String -Pattern "Python\.Python\." | ForEach-Object {
  ($_ -split "\s{2,}")[0]
} | Sort-Object -Unique

if (-not $pkgs) {
  Write-Host "No winget CPython packages found."
} else {
  foreach ($id in $pkgs) {
    Write-Host "Uninstalling $id ..."
    winget uninstall --id $id --silent --accept-source-agreements --accept-package-agreements
  }
}
```

Also uninstall the Python Launcher if you want a full reset (optional; it’s usually fine to keep):``` powershell
winget uninstall --id Python.PythonLauncher --silent --accept-source-agreements --accept-package-agreements
```

 
3) Remove Microsoft Store “python.exe” alias (recommended)
If you ever saw WindowsApps\python.exe, disable those aliases:
Settings → Apps → Advanced app settings → App execution aliases
Turn OFF:
python.exe
python3.exe
You can also uninstall “Python” from Microsoft Store apps if present:
Settings → Apps → Installed apps → search “Python” → Uninstall
 
4) Clean up PATH and Python env vars (semi-automated)
4.1 Remove common Python env vars (safe)``` powershell
# Remove common environment variables that can interfere
[Environment]::SetEnvironmentVariable("PYTHONHOME", $null, "User")
[Environment]::SetEnvironmentVariable("PYTHONPATH", $null, "User")
[Environment]::SetEnvironmentVariable("PYTHONHOME", $null, "Machine")
[Environment]::SetEnvironmentVariable("PYTHONPATH", $null, "Machine")
```

4.2 Optional: remove typical Python folders from PATH (automated-ish)
PATH editing is tricky to do perfectly automatically. Here’s a pragmatic approach that removes entries containing Python3, Python39, Python310, etc.``` powershell
function Remove-PathEntriesMatching {
  param(
    [ValidateSet("User","Machine")] [string] $Scope,
    [string[]] $Patterns
  )

  $path = [Environment]::GetEnvironmentVariable("Path", $Scope)
  if (-not $path) { return }

  $parts = $path -split ';' | Where-Object { $_ -and $_.Trim() -ne "" }
  $filtered = foreach ($p in $parts) {
    $keep = $true
    foreach ($pat in $Patterns) {
      if ($p -match $pat) { $keep = $false; break }
    }
    if ($keep) { $p }
  }

  [Environment]::SetEnvironmentVariable("Path", ($filtered -join ';'), $Scope)
}

$patterns = @(
  '\\Python\d+\\',      # e.g. \Python312\
  '\\Python\d+$',       # e.g. C:\...\Python312
  '\\Python\\',         # some installs
  '\\Scripts\\',        # python Scripts folder
  'WindowsApps\\python',# store alias paths (rarely in PATH but just in case)
  '\\AppData\\Local\\Programs\\Python\\Python\d+\\'
)

Remove-PathEntriesMatching -Scope User -Patterns $patterns
Remove-PathEntriesMatching -Scope Machine -Patterns $patterns

Write-Host "PATH cleaned (best-effort). You should sign out/in or reboot for full effect."
```

After this, reboot (or at least sign out/in) so PATH changes propagate everywhere.
 
5) Install Python 3.13 (clean, reproducible)
Option A (recommended): winget``` powershell
winget install --id Python.Python.3.13 --silent --accept-source-agreements --accept-package-agreements
```

Verify:``` powershell
py -0p
py -3.13 -V
python -V
```

If python -V doesn’t show 3.13, your PATH still points somewhere else—re-check where python.
 
6) Install uv
Option A: official uv installer script (fastest)
Run:``` powershell
powershell -NoProfile -ExecutionPolicy Bypass -Command "irm https://astral.sh/uv/install.ps1 | iex"
```

Then open a new PowerShell and verify:``` powershell
uv --version
```

Option B: winget (if available on your system)``` powershell
winget install --id Astral.uv --silent --accept-source-agreements --accept-package-agreements
```

If winget can’t find it, use Option A.
 
7) Make uv create venvs with Python 3.13 (the way you want)
uv can manage Python versions and venv creation. Two common workflows:
Workflow 1: Use the system-installed Python 3.13
In your project folder:``` powershell
cd <YOUR_PROJECT_FOLDER>
uv venv .venv --python 3.13
```

Activate:``` powershell
.\.venv\Scripts\activate
python -V
```

Install deps:``` powershell
uv pip install -r requirements.txt
```

Workflow 2: Let uv manage Python (more reproducible across machines)
This keeps Python tooling consistent even if system Python changes.``` powershell
cd <YOUR_PROJECT_FOLDER>
uv python install 3.13
uv venv .venv --python 3.13
```

 
8) Optional: enforce “don’t accidentally use random Pythons”
If you want to strongly prefer uv-managed Python, set a user env var:``` powershell
[Environment]::SetEnvironmentVariable("UV_PYTHON_PREFERENCE", "only-managed", "User")
```

Open a new terminal afterward.
 
9) One-shot “reset + install” script (use with care)
This script:
uninstalls winget CPython packages
disables Python-related env vars
installs Python 3.13
installs uv (official installer)``` powershell
# 1) Uninstall CPython via winget
$pkgs = winget list --name Python | Select-String -Pattern "Python\.Python\." | ForEach-Object {
  ($_ -split "\s{2,}")[0]
} | Sort-Object -Unique

foreach ($id in $pkgs) {
  Write-Host "Uninstalling $id ..."
  winget uninstall --id $id --silent --accept-source-agreements --accept-package-agreements
}

# 2) Clear env vars that commonly interfere
[Environment]::SetEnvironmentVariable("PYTHONHOME", $null, "User")
[Environment]::SetEnvironmentVariable("PYTHONPATH", $null, "User")
[Environment]::SetEnvironmentVariable("PYTHONHOME", $null, "Machine")
[Environment]::SetEnvironmentVariable("PYTHONPATH", $null, "Machine")

# 3) Install Python 3.13
winget install --id Python.Python.3.13 --silent --accept-source-agreements --accept-package-agreements

# 4) Install uv
powershell -NoProfile -ExecutionPolicy Bypass -Command "irm https://astral.sh/uv/install.ps1 | iex"

Write-Host "Done. Open a NEW terminal and run: py -3.13 -V ; uv --version"
```

I didn’t include PATH surgery in the one-shot because it can remove things you didn’t intend (better to do PATH cleanup consciously).
 
Quick troubleshooting
python still points to Store alias
Disable App execution aliases for python/python3 (Section 3)
Reopen terminal
where python should no longer show WindowsApps
py not found
Install Python Launcher:``` powershell
winget install --id Python.PythonLauncher --silent --accept-source-agreements --accept-package-agreements
```

Multiple python.exe still show up
Run:``` powershell
where.exe python
```

Then remove the offending install from “Installed apps” or via winget, and clean PATH entries referencing that folder.
 
Two questions so I can tailor the “delete everything” part safely
Do you have Anaconda/Miniconda installed (or do you want to remove it too)?
Are any of your Pythons installed per-user under AppData\Local\Programs\Python\..., or system-wide under Program Files\...?
If you paste the output of py -0p and where python (it won’t contain secrets), I can tell you exactly what’s safe to remove and what’s just an alias.