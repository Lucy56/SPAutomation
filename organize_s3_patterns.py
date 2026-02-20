#!/usr/bin/env python3
"""
Script to organize S3 pattern files into appropriate folders based on pattern names
"""

import re
import subprocess
from collections import defaultdict

# AWS credentials from environment
import os
AWS_ACCESS_KEY_ID = os.getenv("AWS_PATTERNS_KEY")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_PATTERNS_SECRET")
S3_BUCKET = "s3://sinclairpatterns/MAIL/patterns/"

def run_aws_command(cmd):
    """Run AWS CLI command with credentials"""
    env_vars = f'AWS_ACCESS_KEY_ID={AWS_ACCESS_KEY_ID} AWS_SECRET_ACCESS_KEY="{AWS_SECRET_ACCESS_KEY}"'
    full_cmd = f'{env_vars} {cmd}'
    result = subprocess.run(full_cmd, shell=True, capture_output=True, text=True)
    return result.stdout, result.stderr, result.returncode

def extract_pattern_name(filename):
    """Extract pattern name from filename"""
    filename_lower = filename.lower()

    # Pattern mapping - order matters (more specific first)
    patterns = {
        # Specific product codes
        'S1095': 'Soho',
        'S1037': 'Yasmin',  # Classic colorblocked tee
        'S1038': 'Gaia',
        'S1061': 'Candy',
        'S1075': 'Jakarta',
        'S1085': 'Poesy',
        'S1088': 'Rio',
        'S1089': 'Juno',
        'S1096': 'Nyoka',
        'S9011': 'Monterey',
        'S1078': 'Metro',
        'S104': 'Carmel',
        'S1500': 'Kiki',
        'S7002': 'Cloudberry',

        # Named patterns (check for word boundaries)
        'oasis': 'Oasis',
        'soho': 'Soho',
        'gaia': 'Gaia',
        'candy': 'Candy',
        'jakarta': 'Jakarta',
        'poesy': 'Poesy',
        'rio_': 'Rio',
        'juno': 'Juno',
        'nyoka': 'Nyoka',
        'monterey': 'Monterey',
        'metro': 'Metro',
        'carmel': 'Carmel',
        'poppy': 'Poppy',
        'kiki': 'Kiki',
        'cloudberry': 'Cloudberry',
        'rockyberry': 'Rockyberry_Solberry',
        'solberry': 'Rockyberry_Solberry',
        'blueberry': 'Blueberry',

        # Special cases
        'cynthia': 'Cynthia',
        'dale': 'Dale',
        'michelle': 'Michelle',
        'rassika': 'Rassika',
    }

    # Check for pattern matches
    for key, folder in patterns.items():
        if key.lower() in filename_lower:
            return folder

    # Check for children's patterns (generic)
    if 'children' in filename_lower or 'joggers' in filename_lower or 'leggings_with_skirt' in filename_lower:
        if 'joggers' in filename_lower:
            return 'Runberry'
        elif 'leggings_with_skirt' in filename_lower:
            return 'Twinberry'

    return None

def main():
    print("Fetching file list from S3...")
    stdout, stderr, returncode = run_aws_command(f'aws s3 ls {S3_BUCKET}')

    if returncode != 0:
        print(f"Error fetching files: {stderr}")
        return

    # Parse files
    files_to_move = defaultdict(list)
    files_to_delete = []
    skip_files = []

    for line in stdout.strip().split('\n'):
        parts = line.split()
        if len(parts) < 4:
            continue

        # Check if it's a directory (PRE prefix)
        if parts[0] == 'PRE':
            continue

        # Get filename (last part)
        filename = parts[-1]

        # Skip empty files and special files
        if not filename or filename.endswith('/'):
            continue

        # Mark banner and special marketing files for deletion
        if any(x in filename for x in ['Banners_', 'BOGO_', 'Boxing-day', 'SinclairPatterns_Kids']):
            files_to_delete.append(filename)
            continue

        # Extract pattern name
        pattern_folder = extract_pattern_name(filename)

        if pattern_folder:
            files_to_move[pattern_folder].append(filename)
        else:
            skip_files.append(filename)

    # Print summary
    print("\n" + "="*80)
    print("ORGANIZATION PLAN")
    print("="*80)

    for folder in sorted(files_to_move.keys()):
        files = files_to_move[folder]
        print(f"\n{folder}/ ({len(files)} files)")
        for f in sorted(files):
            print(f"  - {f}")

    if files_to_delete:
        print(f"\n\nFILES TO DELETE ({len(files_to_delete)} files):")
        for f in sorted(files_to_delete):
            print(f"  - {f}")

    if skip_files:
        print(f"\n\nFILES TO SKIP (unrecognized pattern) ({len(skip_files)} files):")
        for f in sorted(skip_files):
            print(f"  - {f}")

    print("\n" + "="*80)
    total_files = sum(len(files) for files in files_to_move.values())
    print(f"Total files to organize: {total_files}")
    print(f"Files to delete: {len(files_to_delete)}")
    print(f"Files to skip: {len(skip_files)}")
    print("="*80)

    # Save plan to file for review
    with open('/Users/sanna/Dev/Experiments/SinclairHelper/organization_plan.txt', 'w') as f:
        f.write("="*80 + "\n")
        f.write("ORGANIZATION PLAN\n")
        f.write("="*80 + "\n\n")

        for folder in sorted(files_to_move.keys()):
            files = files_to_move[folder]
            f.write(f"\n{folder}/ ({len(files)} files)\n")
            for file in sorted(files):
                f.write(f"  - {file}\n")

        if files_to_delete:
            f.write(f"\n\nFILES TO DELETE ({len(files_to_delete)} files):\n")
            for file in sorted(files_to_delete):
                f.write(f"  - {file}\n")

        if skip_files:
            f.write(f"\n\nFILES TO SKIP (unrecognized pattern) ({len(skip_files)} files):\n")
            for file in sorted(skip_files):
                f.write(f"  - {file}\n")

        f.write("\n" + "="*80 + "\n")
        f.write(f"Total files to organize: {total_files}\n")
        f.write(f"Files to delete: {len(files_to_delete)}\n")
        f.write(f"Files to skip: {len(skip_files)}\n")
        f.write("="*80 + "\n")

    print("\nPlan saved to organization_plan.txt")
    print("Review the plan and run with --execute flag to proceed.")
    return files_to_move, files_to_delete

def execute_move(files_to_move, files_to_delete):
    """Execute the file moves and deletions"""
    print("\nMoving files...")
    move_success = 0
    move_errors = 0

    for folder, files in files_to_move.items():
        print(f"\nProcessing {folder}/ ...")
        for filename in files:
            source = f"{S3_BUCKET}{filename}"
            dest = f"{S3_BUCKET}{folder}/{filename}"

            # Copy file to new location
            _, stderr, returncode = run_aws_command(f'aws s3 cp {source} {dest}')

            if returncode != 0:
                print(f"  ✗ Error copying {filename}: {stderr}")
                move_errors += 1
                continue

            # Delete original file
            _, stderr, returncode = run_aws_command(f'aws s3 rm {source}')

            if returncode != 0:
                print(f"  ✗ Error deleting {filename}: {stderr}")
                move_errors += 1
            else:
                print(f"  ✓ {filename}")
                move_success += 1

    # Delete marketing/banner files
    print("\nDeleting marketing and banner files...")
    delete_success = 0
    delete_errors = 0

    for filename in files_to_delete:
        source = f"{S3_BUCKET}{filename}"
        _, stderr, returncode = run_aws_command(f'aws s3 rm {source}')

        if returncode != 0:
            print(f"  ✗ Error deleting {filename}: {stderr}")
            delete_errors += 1
        else:
            print(f"  ✓ Deleted {filename}")
            delete_success += 1

    print("\n" + "="*80)
    print(f"Operation complete!")
    print(f"Successfully moved: {move_success} files")
    print(f"Move errors: {move_errors}")
    print(f"Successfully deleted: {delete_success} files")
    print(f"Delete errors: {delete_errors}")
    print("="*80)

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == '--execute':
        # Re-run analysis and execute
        stdout, stderr, returncode = run_aws_command(f'aws s3 ls {S3_BUCKET}')
        if returncode != 0:
            print(f"Error fetching files: {stderr}")
            sys.exit(1)

        files_to_move = defaultdict(list)
        files_to_delete = []

        for line in stdout.strip().split('\n'):
            parts = line.split()
            if len(parts) < 4 or parts[0] == 'PRE':
                continue
            filename = parts[-1]
            if not filename or filename.endswith('/'):
                continue

            # Mark marketing/banner files for deletion
            if any(x in filename for x in ['Banners_', 'BOGO_', 'Boxing-day', 'SinclairPatterns_Kids']):
                files_to_delete.append(filename)
                continue

            pattern_folder = extract_pattern_name(filename)
            if pattern_folder:
                files_to_move[pattern_folder].append(filename)

        execute_move(files_to_move, files_to_delete)
    else:
        main()
