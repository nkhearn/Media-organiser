import os
import sys
import urllib.parse
from flask import Flask, render_template, request, redirect, url_for
from pathlib import Path

app = Flask(__name__)

# Global variables to store the search and working directories
SEARCH_DIR = None
WORKING_DIR = None
MOVIE_DIR = None
TV_DIR = None

# Define common video file extensions (you can add more if needed)
VIDEO_EXTENSIONS = {'.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.webm', '.mpg', '.mpeg', '.m4v', '.3gp', '.3g2', '.ts', '.m2ts', '.vob'}

@app.before_request
def check_dirs():
    """Redirects to setup if directories are not set."""
    if request.endpoint != 'setup_dirs' and (SEARCH_DIR is None or WORKING_DIR is None):
        return redirect(url_for('setup_dirs'))

@app.route('/', methods=['GET', 'POST'])
def index():
    global SEARCH_DIR, WORKING_DIR, MOVIE_DIR, TV_DIR # Ensure global scope for template context

    if request.method == 'POST':
        results = []
        form_data = request.form

        # Process only the actual media_type selections
        for key in form_data:
            if key.startswith('media_type_'):
                item_path_str = key.replace('media_type_', '', 1)
                
                # --- DEBUGGING START ---
                print(f"\n--- Processing form item ---")
                print(f"1. Raw key from form: {key}")
                print(f"2. Extracted item_path_str (URL-decoded by Flask): {item_path_str}")
                # --- DEBUGGING END ---

                item_path = Path(item_path_str).resolve() 
                
                # --- DEBUGGING START ---
                print(f"3. Path(item_path_str).resolve(): {item_path}")
                print(f"4. Does it exist? {item_path.exists()}")
                print(f"5. Is it a file? {item_path.is_file()}")
                print(f"6. Is it a directory? {item_path.is_dir()}")
                # --- DEBUGGING END ---

                # Skip if the item doesn't exist or is not a file/directory
                if not item_path.exists():
                    results.append(f"Skipped (not found): {item_path.name}")
                    continue
                
                # Check if it's a video file or a directory that might contain videos
                if item_path.is_file() and item_path.suffix.lower() not in VIDEO_EXTENSIONS:
                    results.append(f"Skipped (not video file): {item_path.name}")
                    continue

                media_type = form_data.get(key) # This is the value for media_type_{item_path}
                selected_tags = form_data.getlist(f"tags_{item_path_str}") # Get list of selected tags

                if media_type == 'NA':
                    results.append(f"Ignored: {item_path.name}")
                    continue

                if media_type and selected_tags:
                    target_base_dir = None
                    if media_type == 'Movie':
                        target_base_dir = MOVIE_DIR
                    elif media_type == 'TV':
                        target_base_dir = TV_DIR

                    if target_base_dir:
                        for tag in selected_tags:
                            # Ensure the tag itself is a valid directory name
                            tag_clean = "".join(c for c in tag if c.isalnum() or c in (' ', '-', '_')).strip()
                            if not tag_clean: # Skip if tag is empty after cleaning
                                results.append(f"Skipped {item_path.name}: Invalid tag selected.")
                                continue

                            target_dir = Path(target_base_dir) / tag_clean
                            target_dir.mkdir(parents=True, exist_ok=True)
                            
                            link_name = target_dir / item_path.name
                            
                            try:
                                if link_name.exists():
                                    results.append(f"Skipped (exists): {item_path.name} -> {link_name.relative_to(WORKING_DIR)}")
                                else:
                                    os.symlink(item_path, link_name)
                                    results.append(f"Symlinked: {item_path.name} -> {link_name.relative_to(WORKING_DIR)}")
                            except OSError as e:
                                results.append(f"Error linking {item_path.name} to {link_name}: {e}")
                    else:
                        results.append(f"Error: Invalid media type for {item_path.name}")
                else:
                    results.append(f"Skipped: {item_path.name} - no media type or tags selected (or NA selected)")
        
        return render_template('results.html', results=results)

    file_tree = []
    if SEARCH_DIR and os.path.isdir(SEARCH_DIR):
        # Using a dictionary to build the tree structure
        tree_dict = {}

        for root, dirs, files in os.walk(SEARCH_DIR):
            current_node = tree_dict
            # Navigate to the correct level in the tree_dict
            # Use relative_to to get path parts without the search_dir root
            relative_path = Path(root).relative_to(SEARCH_DIR)
            path_parts = relative_path.parts
            
            # For the root of the search directory, relative_path might be Path('.')
            # We treat it as the current_node for the entire search directory content
            if relative_path == Path('.'):
                path_parts = ()

            for part in path_parts:
                if part not in current_node:
                    # Construct full_path for interim directories for consistency
                    full_interim_path = str(SEARCH_DIR / Path(*path_parts[:path_parts.index(part) + 1]))
                    current_node[part] = {'type': 'dir', 'full_path': full_interim_path, 'contents': {}}
                current_node = current_node[part]['contents']
            
            # Add subdirectories (empty or not)
            for d in sorted(dirs):
                full_dir_path = str(Path(root) / d)
                if d not in current_node: # Avoid overwriting if already created by recursive path_parts logic
                    current_node[d] = {'type': 'dir', 'full_path': full_dir_path, 'contents': {}}

            # Add video files
            for f in sorted(files):
                file_ext = Path(f).suffix.lower()
                if file_ext in VIDEO_EXTENSIONS:
                    full_file_path = str(Path(root) / f)
                    current_node[f] = {'type': 'file', 'full_path': full_file_path, 'name': f}

        # Convert the dictionary tree into a flat list for rendering with indentation
        def flatten_tree(node, level=0):
            flat_list = []
            indent_multiplier = 4 # Number of spaces per level
            for name in sorted(node.keys()):
                item = node[name]
                item_indent = '&nbsp;' * (indent_multiplier * level)
                
                if item['type'] == 'dir':
                    # Only add the directory to the flat list if it has a 'full_path' defined
                    # This excludes the implicit root of tree_dict if it has no explicit full_path
                    if 'full_path' in item:
                         flat_list.append({
                            'type': 'dir', 
                            'path': item['full_path'], # This is the full, absolute path string
                            'name': name, 
                            'indent': item_indent
                        })
                    flat_list.extend(flatten_tree(item['contents'], level + 1))
                elif item['type'] == 'file':
                    flat_list.append({
                        'type': 'file', 
                        'path': item['full_path'], # This is the full, absolute path string
                        'name': item['name'], 
                        'indent': item_indent
                    })
            return flat_list
        
        file_tree = flatten_tree(tree_dict)

    movie_tags = get_tags_from_directory(MOVIE_DIR) if MOVIE_DIR else []
    tv_tags = get_tags_from_directory(TV_DIR) if TV_DIR else []

    return render_template('index.html', 
                           file_tree=file_tree, 
                           movie_tags=movie_tags, 
                           tv_tags=tv_tags,
                           search_dir=SEARCH_DIR, # Pass these to template for display
                           working_dir=WORKING_DIR)

@app.route('/setup', methods=['GET', 'POST'])
def setup_dirs():
    global SEARCH_DIR, WORKING_DIR, MOVIE_DIR, TV_DIR
    error_message = None

    if request.method == 'POST':
        search_dir_input = request.form.get('search_directory')
        working_dir_input = request.form.get('working_directory')

        if not search_dir_input or not working_dir_input:
            error_message = "Both directories are required."
        else:
            search_path_obj = Path(search_dir_input).resolve()
            working_path_obj = Path(working_dir_input).resolve()

            if not search_path_obj.is_dir():
                error_message = f"Search directory '{search_dir_input}' does not exist or is not a directory."
            elif not working_path_obj.is_dir():
                error_message = f"Working directory '{working_dir_input}' does not exist or is not a directory."
            else:
                SEARCH_DIR = search_path_obj
                WORKING_DIR = working_path_obj
                MOVIE_DIR = WORKING_DIR / 'Movie'
                TV_DIR = WORKING_DIR / 'TV'

                # Create Movie and TV directories if they don't exist
                MOVIE_DIR.mkdir(exist_ok=True)
                TV_DIR.mkdir(exist_ok=True)
                
                return redirect(url_for('index'))

    return render_template('setup.html', error=error_message, 
                           current_search_dir=SEARCH_DIR, 
                           current_working_dir=WORKING_DIR)

def get_tags_from_directory(directory):
    """Gets subdirectories as tags from a given directory."""
    if directory and Path(directory).is_dir():
        return sorted([d.name for d in Path(directory).iterdir() if d.is_dir()])
    return []

if __name__ == '__main__':
    # Parse command line arguments for initial directories
    if len(sys.argv) > 1:
        search_path_obj = Path(sys.argv[1]).resolve()
        if search_path_obj.is_dir():
            SEARCH_DIR = search_path_obj
        else:
            print(f"Warning: Initial search directory '{sys.argv[1]}' not found or not a directory. Will prompt in browser.")

    if len(sys.argv) > 2:
        working_path_obj = Path(sys.argv[2]).resolve()
        if working_path_obj.is_dir():
            WORKING_DIR = working_path_obj
            MOVIE_DIR = WORKING_DIR / 'Movie'
            TV_DIR = WORKING_DIR / 'TV'
            MOVIE_DIR.mkdir(exist_ok=True)
            TV_DIR.mkdir(exist_ok=True)
        else:
            print(f"Warning: Initial working directory '{sys.argv[2]}' not found or not a directory. Will prompt in browser.")
    
    app.run(debug=True, host='0.0.0.0') # host='0.0.0.0' makes it accessible from other devices on the network
