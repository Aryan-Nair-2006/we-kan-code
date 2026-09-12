import os
import shutil

def prepare_build():
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    build_dir = os.path.join(root_dir, '.sam_build_context')
    
    print(f"Preparing SAM build context at: {build_dir}")
    os.makedirs(build_dir, exist_ok=True)
    
    # Copy necessary source directories
    for module in ['backend', 'shared', 'lambdas']:
        src = os.path.join(root_dir, module)
        dst = os.path.join(build_dir, module)
        if os.path.exists(src):
            print(f"Copying {module}...")
            shutil.copytree(src, dst, dirs_exist_ok=True)
            
    # Copy Lambda-specific requirements
    req_src = os.path.join(root_dir, 'lambdas', 'requirements.txt')
    req_dst = os.path.join(build_dir, 'requirements.txt')
    if os.path.exists(req_src):
        print("Copying Lambda requirements...")
        shutil.copyfile(req_src, req_dst)
        
    print("Build context prepared successfully.")

if __name__ == '__main__':
    prepare_build()
