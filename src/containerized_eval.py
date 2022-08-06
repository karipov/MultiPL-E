"""
This is the entrypoint for the containerized evaluator.

The program expects as input the path to a PROBLEM_NAME.yaml file and
produces PROBLEM_NAME.results.yaml alongside it.
"""

import argparse
from pathlib import Path
from problem_yaml import Problem, Result, ResultList, TestResults
import eval_ruby
import eval_lua
import eval_python
import eval_rust
import eval_julia
import eval_java
import eval_lua
import eval_racket
import eval_javascript
import eval_go
import eval_swift
import eval_cpp
import eval_php
import eval_dlang
import eval_julia
import eval_r
import tempfile
import json

EVALUATORS = {
    "rb": (eval_ruby.eval_script, ".rb"),
    "lua": (eval_lua.eval_script, ".lua"),
    "python": (eval_python.eval_script, ".py"),
    "py": (eval_python.eval_script, ".py"),
    "julia": (eval_julia.eval_script, ".jl"),
    "java" : (eval_java.eval_script, ".java"),
    "rust" : (eval_rust.eval_script, ".rs"),
    "rs" : (eval_rust.eval_script, ".rs"),
    "swift": (eval_swift.eval_script, ".swift"),
    "lua": (eval_lua.eval_script, ".lua"),
    "racket": (eval_racket.eval_script, ".rkt"),
    "rkt": (eval_racket.eval_script, ".rkt"),
    "javascript": (eval_javascript.eval_script, ".js"),
    "js": (eval_javascript.eval_script, ".js"),
    "cpp": (eval_cpp.eval_script, ".cpp"),
    "php": (eval_php.eval_script, ".php"),
    "humaneval_to_dlang.py": (eval_dlang.eval_script, ".d"),
    "d": (eval_dlang.eval_script, ".d"),
    "r": (eval_r.eval_script, ".r"),
    "humaneval_to_r.py": (eval_r.eval_script, ".r"),
    "jl": (eval_julia.eval_script, ".jl"),
    "go": (eval_go.eval_script, ".go")
}

def eval_script(problem, index):
    program = problem.prompt + problem.completions[index] + '\n' + problem.tests
    eval_string_script(problem.language, program)

def eval_string_script(language, program):
    if language in EVALUATORS:
        (eval_script, file_ext) = EVALUATORS[language]
    else:
        eval_module = __import__(f"eval_{language}")
        eval_script = eval_module.eval_script
        file_ext = f".{language}"
    with tempfile.NamedTemporaryFile(suffix=file_ext, delete=True) as f:
        f.write(program.encode("utf-8"))
        f.flush()
        result = eval_script(Path(f.name))
        # Only save the first 2K of output from the running program. Any futher
        # output is very likely an exceptionally long stack trace or a long
        # series of prints.
        #TODO(molly, arjun): make this eyesore not an eyesore
        if type(result["stdout"]) == bytes:
            result["stdout"] = result["stdout"].decode("utf-8", errors="ignore")
        if result["stdout"] is None:
            result["stdout"] = ""
        if result["stderr"] is None:
            result["stderr"] = ""
        if type(result["stderr"]) == bytes:
            result["stderr"] = result["stderr"].decode("utf-8", errors="ignore")
        assert type(result["stdout"]) == str
        assert type(result["stderr"]) == str
        return {
            "program": program,
            "stdout": result['stdout'].replace("!!int", "")[:2048],
            "stderr": result['stderr'][:2048],
            "exit_code": result['exit_code'],
            "status": result['status']
        }

def eval_in_thread(problem_yaml_path, index):
    with open(problem_yaml_path) as f:
        problem = Problem.load(f)
    return eval_script(problem, index)

def main():
    parser = argparse.ArgumentParser(description="Evaluate a problem")
    parser.add_argument("--problem_yaml_path", help="Path to the problem YAML file")
    parser.add_argument("--index", help="Index of the problem to evaluate", type=int)
    args = parser.parse_args()
    result_json = eval_in_thread(Path(args.problem_yaml_path), args.index)
    print(json.dumps(result_json))

if __name__ == "__main__":
    main()
