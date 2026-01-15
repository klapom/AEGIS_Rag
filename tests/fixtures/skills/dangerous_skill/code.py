"""Dangerous skill code with security violations."""

def execute_code(code: str):
    """Execute arbitrary code - DANGEROUS!"""
    exec(code)  # Security violation

def evaluate_expression(expr: str):
    """Evaluate arbitrary expression - DANGEROUS!"""
    return eval(expr)  # Security violation

def run_command(cmd: str):
    """Run shell command - DANGEROUS!"""
    import subprocess
    subprocess.run(cmd, shell=True)  # Security violation
