import os
import re
import pandas as pd

output_dir = os.getenv("PROCESSED_OUTPUT")

# must be a directory in current folder and should not contain any os.path.sep symbols.
extracted_data = os.getenv("ZIP_EXTRACTION_FOLDER")
staging_data = os.getenv("CHUNK_CSV_OUTPUT")

chunk_count = 0
files_processed = 0

if not os.path.exists(output_dir):
    os.mkdir(output_dir)

if not os.path.exists(staging_data):
    os.mkdir(staging_data)


def getOutputPath(path):
    return path.replace(
        extracted_data + os.path.sep, 
        output_dir + os.path.sep
    )


def traverseFolders(curr_path, df, version, processFile, chunkMarkdown, indent = 0):
    global chunk_count
    global files_processed
    for category in os.listdir(curr_path):
        path = os.path.join(curr_path, category)
        # print("\t" * indent + path)
        
        output_path = getOutputPath(path)
        if os.path.isdir(path):
            # Check if same output directory exists?
            if not os.path.isdir(output_path):
                os.mkdir(output_path)
            df = traverseFolders(path, df, version, processFile, chunkMarkdown, indent + 1)
        else:
            files_processed += 1
            try:
                title, content, metadata = processFile(path)
                
                # # We saw that the content with single line is not much useful for us.
                # if content is not None and len(content.split("\n")) > 1:
                if content is not None:
                    # Will be helpful for next step when chunking
                    if not content.startswith("#"):
                        content = f"# {title}\n\n" + content

                    with open(output_path, 'w', encoding='utf-8') as fp:
                        fp.write(content)

                    chunks, chunk_info = chunkMarkdown(content)
                    num_chunks = len(chunks)
                    chunk_count += num_chunks

                    df_dict = {
                        'path': [path[len(extracted_data) + len(version) + 2:]] * num_chunks, 
                        'title': [title] * num_chunks,
                        'content': chunks
                    }
                    # Adding Metadata keys
                    for key in metadata.keys():
                        df_dict[key] = [metadata[key]] * num_chunks

                    # Add Content specific keys
                    for key in chunk_info.keys():
                        df_dict[key] = chunk_info[key]

                    chunks_df = pd.DataFrame(df_dict)

                    df = pd.concat([df, chunks_df], ignore_index=True)
            except Exception as e:
                print(f"Failed for file: {path}")
                print(f"Error: {e}")

    return df


def processAndChunk(processFile, chunkMarkdown):
    global chunk_count
    global files_processed
    print("-" * 50)
    for version in os.listdir(extracted_data):
        chunk_count = 0
        files_processed = 0
        if not os.path.exists(os.path.join(output_dir, version)):
            os.mkdir(os.path.join(output_dir, version))

        print("For version:", version)
        df = pd.DataFrame(columns=['path', 'title', 'description', 'content'])
        df = traverseFolders(
            os.path.join(extracted_data, version), df, version, processFile, chunkMarkdown
        )
        df['version'] = version
        df.to_csv(f"{staging_data}/{version[1:]}.csv", index=False)
        df = pd.read_csv(f"{staging_data}/{version[1:]}.csv")

        df['length'] = df['content'].apply(lambda x: len(x.split()))
        print(f"Min Content Length: {min(df['length'])}, Max Content Length: {max(df['length'])}")
        print(f"Exceeding Chunk Size: {df[df['length'] > 385].shape[0]}/{df.shape[0]}")
        print(f"Files processed: {files_processed}, Chunk Count: {chunk_count}")
        print("-" * 50)