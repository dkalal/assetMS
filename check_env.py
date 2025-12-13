import sys
import subprocess

def check_environment():
    print("Python Environment Check")
    print("======================")
    print(f"Python Version: {sys.version}")
    print(f"Executable: {sys.executable}")
    print(f"\nEnvironment Variables:")
    print(f"PATH: {sys.prefix}")
    print(f"Base Prefix: {sys.base_prefix}")
    print(f"Real Prefix: {getattr(sys, 'real_prefix', 'Not in a virtual environment')}")
    
    try:
        import pip
        print("\nPIP Version:", pip.__version__)
    except ImportError:
        print("\nPIP is not installed or not accessible")

if __name__ == "__main__":
    check_environment()
