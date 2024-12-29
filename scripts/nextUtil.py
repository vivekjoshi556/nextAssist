"""
This file contains the utility functions that are specific to Next.js.

If you want to use this for other project you just need to create 2 functions (processFile, chunkMarkdown) with same signature in another file and you should directly be able to update import in index.py file to see the updated index.
"""
import os
import re
import yaml

extracted_data = os.getenv("ZIP_EXTRACTION_FOLDER")


def processFile(path):
    """
    Processes a file to extract metadata and content.

    Args:
        path (str): The path to the file to be processed.

    Returns:
        tuple: A tuple containing the title, content, and metadata dictionary.
    """

    content = ""
    with open(path, 'r', encoding='utf-8') as fp:
        content = fp.read()

    # See if there is a source mentioned for this document.
    lines = content.strip().split("\n")
    metadata_lines = lines[1:lines.index("---", 1)]
    source_index = next((i for i, s in enumerate(metadata_lines) if s.startswith("source:")), None)

    # If there is a source mentioned.
    if source_index is not None:
        source_path = metadata_lines[source_index].split(":")[-1].strip().replace("/", os.path.sep)
        try:
            source_path = getPathFromSource(path, source_path)
            with open(source_path, 'r', encoding='utf-8') as fp:
                content = fp.read()
            
            lines = content.strip().split("\n")
            metadata_lines = lines[1:lines.index("---", 1)]

        except Exception as e:
            print(e)

    metadata_dict = yaml.safe_load("\n".join(metadata_lines))

    # Remove metadata tag we have everything we need.
    content = "\n".join(content.split("\n")[len(metadata_lines) + 2:])

    # Get rid of comments
    content = re.sub(r'{\/\*.*?\*\/}', '', content, flags=re.DOTALL)
    # Get rid of 3 or more consecutive newline characters.
    content = re.sub(r'\n{3,}', '\n', content, flags=re.DOTALL)
    content = content.strip()

    # If no source is mentioned and file doesn't contain any content exclude it from indexing.
    if len(metadata_lines) + 2 == len(lines):
        return None, None, None
        
    router = getRouter(path)
    if router is not None:
        content = filterRouterContent(content, getRouter(path))

    return metadata_dict.get("title", ""), content.strip(), {"description": metadata_dict.get("description", "")}


def chunkMarkdown(content):
    """
    This method performs the chunking of the given markdown content.

    Args:
        content (str): This is the content of the markdown file that needs to be chunked.

    Returns: 
        List[str]: This is a list of all the chunks that were created.
        dict: This is a dictionary of the metadata related to each chunk. The value of each key is a list of length equals to the number of chunks.
    """
    heading_pattern = r"^(#{1,6})\s+(.+)$"
    
    def getChunks(text, max_size, headings_stack):
        """Recursive function to chunk the markdown based on heading levels."""
        chunks = []
        lines = text.splitlines()
        buffer = []
        current_heading = ""
        in_code_block = False

        for line in lines:
            if line.strip().startswith("```"):
                in_code_block = not in_code_block

            if not in_code_block:
                heading_match = re.match(heading_pattern, line)
                if heading_match:
                    if buffer:
                        # Process the current buffer as a chunk
                        chunks += splitBuffer(buffer, max_size, headings_stack)
                        buffer = []

                    current_heading = heading_match.group(0)  # Full heading with level
                    current_heading_level = len(heading_match.group(1))

                    # Only adjust the headings stack up to the current heading level
                    while (
                        len(headings_stack) > 0 and 
                        current_heading_level <= len(re.match(heading_pattern, headings_stack[-1]).group(1))
                    ):
                        headings_stack = headings_stack[:-1]

                    headings_stack.append(current_heading)
                    continue

            buffer.append(line)

        if buffer:
            # Process remaining buffer
            chunks += splitBuffer(buffer, max_size, headings_stack)

        return chunks

    def splitBuffer(buffer, max_size, headings_stack):
        """Split buffer content into chunks if it exceeds the size."""
        chunks = []
        content = "\n".join(buffer)
        words = content.split()

        if len(words) <= max_size:
            chunk_content = "\n".join(headings_stack).strip() + "\n" + content
            # Skip chunks that are just headings
            if not all(re.match(heading_pattern, line) for line in content.splitlines()):
                chunks.append(chunk_content)
        else:
            current_chunk = []
            word_count = 0

            for word in words:
                current_chunk.append(word)
                word_count += 1
                if word_count >= max_size:
                    # Ensure we don't split in the middle of a code block or list
                    joined_chunk = " ".join(current_chunk)
                    if re.search(r"```", joined_chunk) and joined_chunk.count("```") % 2 != 0:
                        continue
                    if re.search(r"\n\s*[-*]\s", joined_chunk):
                        continue

                    chunk_content = "\n".join(headings_stack).strip() + "\n" + " ".join(current_chunk)
                    chunks.append(chunk_content)
                    current_chunk = []
                    word_count = 0

            if current_chunk:
                chunk_content = "\n".join(headings_stack).strip() + "\n" + " ".join(current_chunk)
                chunks.append(chunk_content)

        return chunks

    if not content.strip():
        return []

    return getChunks(content, 385, []), {}


def getRouter(path):
    """
    This is a next.js specific method which determines the router for which this document is.

    Args:
        path (str): This is the path of the document.
    
    Returns:
        str | None: This is the name of the router (pages or app) or none (if doesn't belong to a specific router).
    """
    path_dirs = path.split(os.path.sep)
    if extracted_data in path_dirs:
        root_idx = path_dirs.index(extracted_data)
        # +1 is version and +2 is the first folder inside the root.
        return None if path_dirs[root_idx + 2] not in ["app", "pages"] else path_dirs[root_idx + 2]
    
    return path_dirs[0]


def getPathFromSource(curr_path, source_path):
    """
    This is also a next.js specific method. This method resolves the path which is referenced as source in the documentation.

    Args:
        curr_path (str): This is the path of the document current being processed.
        source_path (str): This is the path mentioned in the source.
    
    Returns:
        str: This is the path of the file which is reference in the source.
    """
    if source_path.startswith("'") and source_path.endswith("'"):
        source_path = source_path[1:-1]

    curr_path_folders = curr_path.split(os.path.sep)
    base_path = os.path.sep.join(curr_path_folders[:curr_path_folders.index(getRouter(curr_path))])
    abs_source_path = os.path.sep.join([base_path, source_path])

    if os.path.isdir(abs_source_path):
        abs_source_file = os.path.join(abs_source_path, "index.mdx")
        if not os.path.isdir(abs_source_file) and os.path.exists(abs_source_file):
            return abs_source_file
    elif not abs_source_path.endswith(".mdx"):
        return abs_source_path + ".mdx"

    return abs_source_path


def filterRouterContent(content, router):
    """
    This is also a next.js specific method. Filter out the content based on the given router name.

    Args:
        content (str): The content of the source document.
        router (str): The name of the router (pages or app).
    """
    # Get the tag for current router.
    tag = "<AppOnly>" if router == "app" else "<PagesOnly>"
    remove_tag = "<AppOnly>" if tag == "<PagesOnly>" else "<PagesOnly>"

    remove_pattern = fr'{remove_tag}(.*?)<\/{remove_tag[1:]}'

    # Remove the content of other router.
    content = re.sub(remove_pattern, '', content, flags=re.DOTALL)

    # Remove opening and closing tags of the current router.
    content = re.sub(fr'{tag}', '', content, flags=re.DOTALL)
    content = re.sub(fr'<\/{tag[1:]}', '', content, flags=re.DOTALL)

    content = re.sub(r'\n{3,}', '\n', content, flags=re.DOTALL)

    return content
