import os
import requests


def downloadRepo():
    """
    Download all the Repositories.
    """
    repo_name = os.getenv("REPO_NAME")
    major_version = int(os.getenv("MAJOR_VERSION"))
    minor_version = int(os.getenv("MINOR_VERSION"))
    zip_download_folder = os.getenv("ZIP_DOWNLOAD_FOLDER")

    if not os.path.exists(zip_download_folder):
        os.mkdir(zip_download_folder)

    consider = []
    # Only these many are allowed (maybe look into authentication setup).
    for page_num in range(1, 11):
        response = requests.get(
            f"https://api.github.com/repos/{repo_name}/releases?per_page=100&page={page_num}"
        )

        releases = response.json()
        print(f"Page: {page_num}")

        for release in releases:
            if release['tag_name'].startswith("v") and "-" not in release['tag_name']:
                consider.append(release['tag_name'][1:])
                print("-->", release['tag_name'][1:], release['created_at'])

    # This will sort them
    consider.reverse()

    releases = {}
    for version in consider:
        [major, minor, _] = version.split(".")
        if major not in releases:
            releases[major] = []
        if minor not in releases[major]:
            releases[major].append(minor)


    # Filter only the folders we have.
    for major in releases.keys():
        for minor in releases[major]:
            if int(major) < major_version or int(major) == major_version and int(minor) < minor_version:
                continue

            print(f"Download v{major}.{minor}.0")
            url = f"https://api.github.com/repos/{repo_name}/zipball/v{major}.{minor}.0"
            save_path = f"{zip_download_folder}/v{major}.{minor}.0.zip"

            # Only download file if it is not present already.
            if not os.path.exists(save_path):
                response = requests.get(url)
                if response.status_code == 200:
                    with open(save_path, 'wb') as f:
                        f.write(response.content)
                    print(f"File downloaded and saved to {save_path}")
                else:
                    print(f"Failed to download file. HTTP status code: {response.status_code}")