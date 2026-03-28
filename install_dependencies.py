import platform
import subprocess
import sys

def install_os_dependencies():
    system = platform.system()
    print(f"Detected OS: {system}")
    
    requirements_file = None
    
    if system == "Windows":
        requirements_file = "requirements-windows.txt"
    elif system == "Linux":
        requirements_file = "requirements-linux.txt"
    elif system == "Darwin":
        requirements_file = "requirements-macos.txt"
    
    if requirements_file:
        try:
            print(f"Installing dependencies from {requirements_file}...")
            subprocess.check_call([
                sys.executable, "-m", "pip", "install", "-r", requirements_file
            ])
            print("OS-specific dependencies installed successfully")
        except subprocess.CalledProcessError as e:
            print(f"Failed to install dependencies: {e}")
        except FileNotFoundError:
            print(f"{requirements_file} not found, skipping OS-specific dependencies")
    else:
        print("Unknown OS, skipping OS-specific dependencies")

if __name__ == "__main__":
    install_os_dependencies()