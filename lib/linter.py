from pylint import lint
import rope
import esprima
import subprocess
import json
import os
import tempfile
import shutil

class Linter:
    def __init__(self):
        self.python_lint = lint.PyLinter()
        self.python_extractor = self.extract_python_errors

    def lint(self, code, language):

        self.language = language

        if self.language == "python":
            ast = rope.base.ast.parse(code)
            self.python_lint.load_default_plugins()
            self.python_lint.check(ast)
            return self.python_lint.reporter.messages

        elif self.language == "javascript":
            return self.run_eslint(code)

        elif self.language == "csharp":
            return self.analyze_csharp_code(code)

        else:
            raise ValueError("Unsupported language")

    def run_eslint(self, code):
        # Run ESLint using subprocess
        process = subprocess.Popen(
            ["npx eslint", "--format=json", "--stdin"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        stdout, stderr = process.communicate(input=code)

        if process.returncode == 0:
            # Parse ESLint output
            lint_results = json.loads(stdout)
            return lint_results

        else:
            # Handle error if ESLint command fails
            print("Error running ESLint:", stderr)
            return []

    def analyze_csharp_code(self, code):
        with tempfile.TemporaryDirectory() as temp_dir:
            cs_file_path = os.path.join(temp_dir, "yourfile.cs")
            with open(cs_file_path, "w") as file:
                file.write(code)

            try:
                process = subprocess.Popen(
                    ["dotnet", "new", "console", "--name", "temp_project"],
                    cwd=temp_dir,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )
                process.communicate()

                process = subprocess.Popen(
                    ["dotnet", "add", "file", cs_file_path],
                    cwd=temp_dir,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )
                stdout, stderr = process.communicate()

                process = subprocess.Popen(
                    ["dotnet", "build"],
                    cwd=temp_dir,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )
                stdout, stderr = process.communicate()

                warnings, errors = self.parse_output(stdout.decode("utf-8"), stderr.decode("utf-8"))

                return warnings, errors
            finally:
                shutil.rmtree(temp_dir)

    def parse_output(output, error):
        warnings = []
        errors = []

        output_lines = output.split("\n")

        for line in output_lines:
            if re.match(r"^[Ww]arning: SEVERITY: (.*)", line):
                warning_message = re.search(r"^[Ww]arning: SEVERITY: (.*)", line).group(1)
                warnings.append(warning_message)

            elif re.match(r"^Error: (.*)", line):
                error_message = re.search(r"^Error: (.*)", line).group(1)
                errors.append(error_message)

        return warnings, errors

    def extract_errors(self, code):
        lint_results = self.lint(code)
        return self.extract_errors_from_lint_results(lint_results)

    def extract_errors_from_lint_results(self, lint_results):
        if self.language == "python":
            return self.python_extractor(lint_results)
        elif self.language == "javascript":
            return self.extract_javascript_errors(lint_results)
        elif self.language == "csharp":
            return self.extract_csharp_errors(lint_results)
        else:
            return []

    def extract_python_errors(self, messages):
        return [(msg.line, msg.column, msg.msg) for msg in messages]

    def extract_javascript_errors(self, lint_results):
        # Extract error information from ESLint output
        errors = []
        for result in lint_results:
            if result["severity"] > 1:
                errors.append((result["line"], result["column"], result["message"]))
        return errors

    def extract_csharp_errors(self, diagnostics):
        # Extract error information from Roslyn diagnostics
        errors = []
        for diag in diagnostics:
            if diag.Severity > 1:
                line_span = diag.Location.GetLineSpan()
                errors.append((line_span.StartLinePosition.Line, line_span.StartLinePosition.Character, diag.GetMessage()))
        return errors

linter = Linter()
