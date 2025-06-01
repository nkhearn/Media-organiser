# Media Symlinker Organizer

This is a Flask web application designed to help you organize your media files (movies and TV shows) by creating a structured directory of symbolic links based on user-defined tags.

## Features

- Scans a specified search directory for media files and directories.
- Allows users to set a working directory where organized symlinks will be created.
- Users can categorize items as 'Movie' or 'TV' and assign multiple tags.
- Symlinks are created in a `WorkingDir/Movie/Tag/` or `WorkingDir/TV/Tag/` structure.
- Simple web interface for selecting media and assigning types/tags.

## Setup

1.  **Prerequisites**:
    *   Python 3.x
    *   Flask (will be installed via pip)

2.  **Installation**:
    *   Clone this repository or download the source code.
    *   It's recommended to use a virtual environment:
        ```bash
        python -m venv venv
        source venv/bin/activate  # On Windows use `venv\Scripts\activate`
        ```
    *   Install dependencies (Flask, in this case, though not explicitly listed in a requirements.txt yet):
        ```bash
        pip install Flask
        ```

3.  **Running the Application**:
    *   Navigate to the project directory.
    *   Run the Flask application:
        ```bash
        python app.py [optional_search_directory] [optional_working_directory]
        ```
    *   If you don't provide the directories as command-line arguments, the application will prompt you to set them up in the web interface.
    *   Open your web browser and go to `http://127.0.0.1:5000` (or `http://0.0.0.0:5000` as configured in `app.py`).

## Usage

1.  **Setup Directories**:
    *   If you haven't provided them via command line, the first page will ask you to set your **Search Directory** (where your original media files are) and your **Working Directory** (where the `Movie` and `TV` symlink structures will be created).
    *   These directories must exist.

2.  **Organize Media**:
    *   The main page will display a list of files and directories found in your **Search Directory**.
    *   For each item, you can:
        *   Select its type: 'Movie', 'TV', or 'NA' (Not Applicable/Ignore).
        *   Select one or more tags. Tags are based on existing subdirectories within `WorkingDir/Movie` and `WorkingDir/TV`. You can create new tags by creating new subdirectories in these locations manually or by typing a new tag name during selection (this feature might depend on the version, primarily it uses existing tags).
    *   Click "Submit".

3.  **Results**:
    *   The application will process your selections and attempt to create symbolic links in the appropriate `WorkingDir/MediaType/Tag/` folder, pointing to your original media files/directories.
    *   A summary of actions (symlinked, skipped, errors) will be displayed.

## Notes

- This application creates symbolic links. The original files are not moved or copied.
- Ensure the application has the necessary permissions to read the search directory and write to the working directory.

## Testing

A test script `test_symlink_fix.py` is included to verify the core logic of symlink creation, especially for directory names with spaces. This test was created to ensure that the URL decoding fix in `app.py` correctly handles such cases.

To run the test:

1.  Navigate to the project's root directory in your terminal.
2.  Execute the script:
    ```bash
    python test_symlink_fix.py
    ```
3.  The script will print output indicating the steps it's taking and will report success or failure. It creates temporary directories for its operations and cleans them up afterward.
