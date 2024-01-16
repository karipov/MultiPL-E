from pathlib import Path
from safe_subprocess import run

def eval_script(path: Path):
    r = run(["pyret", path])

    if r.timeout:
        status = "Timeout"
    elif "Looks shipshape" in r.stdout:
        status = "OK"
    elif "Pyret didn't understand" in r.stderr:
        status = "SyntaxError"
    else:
        status = "Exception"

    # shutdown language server
    run(["pyret", "--shutdown"])

    return {
        "status": status,
        "exit_code": r.exit_code,
        "stdout": r.stdout,
        "stderr": r.stderr
    }
