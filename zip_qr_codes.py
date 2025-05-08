import os
import zipfile

def zip_qr_codes(output_zip_path='qr_codes.zip'):
    qr_folder = 'qr_codes'
    
    if not os.path.exists(qr_folder):
        print(f"❌ Folder '{qr_folder}' does not exist!")
        return
    
    with zipfile.ZipFile(output_zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(qr_folder):
            for file in files:
                if file.endswith('.png'):
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, qr_folder)  # relative name inside zip
                    zipf.write(file_path, arcname)
    
    print(f"✅ All QR codes zipped successfully into '{output_zip_path}'!")

# Only run if this script is executed directly
if __name__ == "__main__":
    zip_qr_codes()
