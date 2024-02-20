from lib.linter import Linter

def test_linter():
    python_code = """
    def hello()
        print("Hello, world!")
    """

    javascript_code = """
    function greet() {
        console.log("Greetings!"
    }
    """

    csharp_code = """
    using System;

    class Program
    {
        static void Main(string[] args)
        {
            string message = "Hello, world!";
            Console.WriteLine(message)
        }
    }
    """

    python_linter = Linter(python_code, "python")
    python_linted_code = python_linter.lint()
    print("Python Linted Code:")
    print(python_linted_code)

    javascript_linter = Linter(javascript_code, "javascript")
    javascript_linted_code = javascript_linter.lint()
    print("\nJavaScript Linted Code:")
    print(javascript_linted_code)

    csharp_linter = Linter(csharp_code, "csharp")
    csharp_linted_code = csharp_linter.lint()
    print("\nC# Linted Code:")
    print(csharp_linted_code)

if __name__ == "__main__":
    test_linter()