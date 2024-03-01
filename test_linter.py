from lib.linter import Linter
from lib.custom_logger import *
from lib.config_manager import *

logger = CustomLogger(get_config("log_folder",""))

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
            test = 15;
            string message = "Hello, world!";
            Console.WriteLine(message);
        }
    }
    """

    python_linter = Linter(python_code, "python")
    python_linted_code = python_linter.lint()
    logger.log("Python Linted Code:")
    logger.log(python_linted_code)

    javascript_linter = Linter(javascript_code, "javascript")
    javascript_linted_code = javascript_linter.lint()
    logger.log("\nJavaScript Linted Code:")
    logger.log(javascript_linted_code)

    csharp_linter = Linter(csharp_code, "csharp")
    csharp_linted_code = csharp_linter.lint()
    logger.log("\nC# Linted Code:")
    logger.log(csharp_linted_code)

if __name__ == "__main__":
    test_linter()