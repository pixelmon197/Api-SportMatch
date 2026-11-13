"""
Ejecuta todos los scripts de prueba de test/ (test_*.py), uno por uno y en
procesos separados, y termina con código 1 si alguno falla.

Lo usa el workflow de GitHub Actions (.github/workflows/ci.yml), pero
también sirve en local:

    python test/run_all.py

Cada script crea su propia base SQLite temporal en test/, así que no
necesita la base de datos real (Neon) ni un archivo .env.
"""
import os
import subprocess
import sys
import time

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(BASE_DIR)


def main():
    scripts = sorted(
        f for f in os.listdir(BASE_DIR) if f.startswith("test_") and f.endswith(".py")
    )
    resultados = []
    inicio_total = time.time()

    for script in scripts:
        inicio = time.time()
        proc = subprocess.run(
            [sys.executable, os.path.join(BASE_DIR, script)],
            cwd=PROJECT_DIR,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        duracion = time.time() - inicio
        ok = proc.returncode == 0
        resultados.append((script, ok, duracion))
        print(f"[{'OK ' if ok else 'FALLO'}] {script} ({duracion:.1f} s)", flush=True)
        if not ok:
            # Solo se imprime el detalle de los que fallan, para no llenar el log.
            print(proc.stdout[-4000:])
            print(proc.stderr[-4000:])

    fallidos = [r for r in resultados if not r[1]]
    print("-" * 60)
    print(
        f"{len(resultados) - len(fallidos)} de {len(resultados)} scripts de prueba "
        f"pasaron en {time.time() - inicio_total:.1f} s"
    )
    if fallidos:
        print("Fallaron: " + ", ".join(r[0] for r in fallidos))
        sys.exit(1)


if __name__ == "__main__":
    main()
