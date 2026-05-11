import sys
import os

print("--- Iniciando verificação de sintaxe ---")

files_to_check = [
    "config.py",
    "memory/manager.py",
    "tools/github_tool.py",
    "tools/search_tool.py",
    "agents/writer.py",
    "agents/designer.py",
    "agents/developer.py",
    "orchestrator.py",
    "scheduler.py",
    "main.py"
]

all_ok = True

for file in files_to_check:
    if not os.path.exists(file):
        print(f"[AVISO] Arquivo opcional/ausente: {file}")
        continue
        
    try:
        with open(file, "r", encoding="utf-8") as f:
            compile(f.read(), file, "exec")
        print(f"[OK] Sintaxe: {file}")
    except Exception as e:
        print(f"[ERRO] Sintaxe em {file}: {e}")
        all_ok = False

if all_ok:
    print("\n--- Verificação concluída com SUCESSO ---")
    sys.exit(0)
else:
    print("\n--- Verificação falhou ---")
    sys.exit(1)
