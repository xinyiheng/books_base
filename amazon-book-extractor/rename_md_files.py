#!/usr/bin/env python3
"""
Script to rename existing Markdown files in the amazon-book-extractor project
to use clean book titles without prefixes or timestamps.
"""

import os
import re
import json
import argparse

def clean_filename(filename):
    """
    Clean a filename by removing amazon_book_ prefix and timestamp suffix.
    
    Args:
        filename (str): Original filename
    
    Returns:
        str: Cleaned filename
    """
    # Remove amazon_book_ISBN_ prefix
    clean_name = re.sub(r'^amazon_book_[A-Z0-9]+_', '', filename)
    
    # Remove timestamp suffix _YYYY-MM-DDThh-mm-ss-mmmZ
    clean_name = re.sub(r'_\d{4}-\d{2}-\d{2}T\d{2}-\d{2}-\d{2}-\d{3}Z', '', clean_name)
    
    # Replace underscores with spaces for better readability
    clean_name = clean_name.replace('_', ' ')
    
    return clean_name

def get_title_from_json(json_file_path):
    """
    Extract book title from corresponding JSON file
    
    Args:
        json_file_path (str): Path to JSON file
    
    Returns:
        str: Book title or None if not found or error
    """
    try:
        with open(json_file_path, 'r', encoding='utf-8') as f:
            book_data = json.load(f)
            title = book_data.get('标题') or book_data.get('书名') or book_data.get('title', '')
            if title:
                return title
    except Exception as e:
        print(f"Error reading JSON file {json_file_path}: {str(e)}")
    
    return None

def rename_markdown_files(markdown_dir, json_dir, dry_run=False):
    """
    Rename Markdown files to use clean book titles
    
    Args:
        markdown_dir (str): Directory containing Markdown files
        json_dir (str): Directory containing JSON files
        dry_run (bool): If True, only show what would be done without making changes
    
    Returns:
        int: Number of files renamed
    """
    count = 0
    
    # Get list of all Markdown files with amazon_book_ prefix
    for filename in os.listdir(markdown_dir):
        if not filename.endswith('.md') or not filename.startswith('amazon_book_'):
            continue
        
        old_path = os.path.join(markdown_dir, filename)
        
        # Get corresponding JSON file path
        json_filename = filename.replace('.md', '.json')
        json_path = os.path.join(json_dir, json_filename)
        
        # Try to get title from JSON file first
        title = None
        if os.path.exists(json_path):
            title = get_title_from_json(json_path)
        
        # If no title found in JSON, clean the filename
        if not title:
            title = clean_filename(os.path.splitext(filename)[0])
        
        # Clean title for use as filename
        clean_title = title.replace('/', '_').replace('\\', '_').replace(':', '_')
        clean_title = clean_title.replace('*', '_').replace('?', '_').replace('"', '_')
        clean_title = clean_title.replace('<', '_').replace('>', '_').replace('|', '_')
        
        # Limit filename length
        if len(clean_title) > 100:
            clean_title = clean_title[:100]
        
        new_filename = f"{clean_title}.md"
        new_path = os.path.join(markdown_dir, new_filename)
        
        # Skip if new filename already exists
        if os.path.exists(new_path) and old_path != new_path:
            print(f"Skipping {filename} - destination file {new_filename} already exists")
            continue
        
        if dry_run:
            print(f"Would rename: {filename} -> {new_filename}")
        else:
            try:
                os.rename(old_path, new_path)
                print(f"Renamed: {filename} -> {new_filename}")
                count += 1
            except Exception as e:
                print(f"Error renaming {filename}: {str(e)}")
    
    return count

def main():
    parser = argparse.ArgumentParser(description='Rename Markdown files to use clean book titles')
    parser.add_argument('--markdown-dir', default='./amazonbooks/markdown', help='Directory containing Markdown files')
    parser.add_argument('--json-dir', default='./amazonbooks/json', help='Directory containing JSON files')
    parser.add_argument('--dry-run', action='store_true', help='Only show what would be done without making changes')
    
    args = parser.parse_args()
    
    if not os.path.exists(args.markdown_dir):
        print(f"Markdown directory not found: {args.markdown_dir}")
        return 1
    
    if not os.path.exists(args.json_dir):
        print(f"JSON directory not found: {args.json_dir}")
        return 1
    
    renamed = rename_markdown_files(args.markdown_dir, args.json_dir, args.dry_run)
    
    if args.dry_run:
        print(f"Would rename {renamed} files")
    else:
        print(f"Successfully renamed {renamed} files")
    
    return 0

if __name__ == "__main__":
    exit(main())