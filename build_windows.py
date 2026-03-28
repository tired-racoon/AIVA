import PyInstaller.__main__
import os
import shutil

def build_exe():
    if os.path.exists('dist'):
        shutil.rmtree('dist')
    if os.path.exists('build'):
        shutil.rmtree('build')
    
    PyInstaller.__main__.run([
        'main_gui.py',
        '--name=AIVA',
        '--onefile',
        '--windowed',
        '--icon=icon.ico',
        '--add-data=.env;.',
        '--add-data=config;config',
        '--add-data=core;core',
        '--add-data=providers;providers',
        '--add-data=tools;tools',
        '--add-data=utils;utils',
        '--add-data=gui;gui',
        '--hidden-import=gigaam',
        '--hidden-import=vosk_tts',
        '--hidden-import=PyQt5',
        '--hidden-import=pycaw',
        '--hidden-import=wmi',
        '--hidden-import=win32com',
        '--hidden-import=tqdm',
        '--hidden-import=regex',
        '--hidden-import=requests',
        '--hidden-import=packaging',
        '--hidden-import=filelock',
        '--hidden-import=numpy',
        '--hidden-import=tokenizers',
        '--hidden-import=safetensors',
        '--hidden-import=hydra',
        '--hidden-import=hydra.core',
        '--collect-all=transformers',
        '--collect-all=torch',
        '--collect-all=gigaam',
        '--collect-all=vosk_tts',
        '--collect-all=onnxruntime',
        '--collect-all=tqdm',
        '--collect-all=tokenizers',
        '--collect-all=huggingface_hub',
        '--copy-metadata=transformers',
        '--copy-metadata=torch',
        '--copy-metadata=tqdm',
        '--copy-metadata=regex',
        '--copy-metadata=requests',
        '--copy-metadata=packaging',
        '--copy-metadata=filelock',
        '--copy-metadata=tokenizers',
        '--copy-metadata=huggingface-hub',
        '--copy-metadata=safetensors',
        '--copy-metadata=pyyaml',
        '--copy-metadata=numpy',
    ])
    
    print("\nBuild complete! Executable is in dist/ folder")

if __name__ == "__main__":
    build_exe()