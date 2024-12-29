import os
import re
import shutil
import zipfile


def extractDocsFromMainFolder(zip_path, output_dir, zip_filename):
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        all_files = zip_ref.namelist()
        main_folder = all_files[0]
        docs_folder = main_folder + os.getenv("CONTENT_FOLDER")

        docs_files = [file for file in all_files if file.startswith(docs_folder)]
        
        if docs_files:
            os.makedirs(output_dir, exist_ok=True)

            for file in docs_files:
                zip_ref.extract(file, output_dir)
                rename = os.path.join(output_dir, file[len(docs_folder):])
                if not os.path.exists(rename):
                    os.rename(os.path.join(output_dir, file), rename)
                
            print(f"Extracted 'docs' folder from {zip_path} to {output_dir}")
        else:
            print(f"No 'docs' folder found in {zip_path}.")

        shutil.rmtree(os.path.join(output_dir, main_folder))


def extract(postProcessing=None):
    docs_folder = os.getenv("ZIP_DOWNLOAD_FOLDER")
    output_root = os.getenv("ZIP_EXTRACTION_FOLDER")
    os.makedirs(output_root, exist_ok=True)

    zip_files = [f for f in os.listdir(docs_folder) if f.endswith('.zip')]

    for zip_file in zip_files:
        zip_path = os.path.join(docs_folder, zip_file)
        output_dir_name = os.path.splitext(zip_file)[0]
        output_dir_path = os.path.join(output_root, output_dir_name)
        extractDocsFromMainFolder(zip_path, output_dir_path, zip_file)

    if postProcessing is not None:
        postProcessing()


def filePostProcessing():
    base_dir = os.getenv("ZIP_EXTRACTION_FOLDER")
    # Matches one or more digits followed by a hyphen
    pattern = r'^\d+-'

    for root, dirs, files in os.walk(base_dir, topdown=False):
        for filename in files:
            if re.match(pattern, filename):
                new_filename = re.sub(pattern, '', filename)
                old_filepath = os.path.join(root, filename)
                new_filepath = os.path.join(root, new_filename)
                
                os.rename(old_filepath, new_filepath)
                print(f"Renamed file: {old_filepath} -> {new_filepath}")

        for dirname in dirs:
            if re.match(pattern, dirname):
                new_dirname = re.sub(pattern, '', dirname)
                old_dirpath = os.path.join(root, dirname)
                new_dirpath = os.path.join(root, new_dirname)

                if os.path.exists(new_dirpath):
                    for item in os.listdir(old_dirpath):
                        old_item_path = os.path.join(old_dirpath, item)
                        new_item_path = os.path.join(new_dirpath, item)

                        if os.path.isfile(old_item_path):
                            shutil.move(old_item_path, new_item_path)
                        elif os.path.isdir(old_item_path):
                            shutil.move(old_item_path, new_item_path)
                    os.rmdir(old_dirpath)
                    print(f"Merged contents from {old_dirpath} into {new_dirpath}.")
                else:
                    os.rename(old_dirpath, new_dirpath)
                    print(f"Renamed directory: {old_dirpath} -> {new_dirpath}")