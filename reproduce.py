"""Reprocess archived recordings; does not communicate with hardware."""
from pathlib import Path
import subprocess, sys
ROOT=Path(__file__).resolve().parent
for script in ('verify.py','final.py','cv.py','plot_results.py'):
    subprocess.run([sys.executable,str(ROOT/'analysis'/script)],cwd=ROOT,check=True)
print('Complete: results/ contains numerical results; figures/ contains regenerated plots.')
