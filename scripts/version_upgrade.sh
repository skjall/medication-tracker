#!/bin/bash
# Script to update version number in version.txt

# Usage:
# ./scripts/update_version.sh [major|minor|patch]

set -e

# Check if version.txt exists
if [ ! -f "version.txt" ]; then
    echo "Error: version.txt not found in the current directory."
    exit 1
fi

# Read current version
CURRENT_VERSION=$(cat version.txt)

# Check if it matches semantic versioning pattern
if ! [[ $CURRENT_VERSION =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    echo "Error: Current version ($CURRENT_VERSION) does not follow semantic versioning (X.Y.Z)."
    exit 1
fi

# Split version into components
IFS='.' read -ra VERSION_PARTS <<< "$CURRENT_VERSION"
MAJOR=${VERSION_PARTS[0]}
MINOR=${VERSION_PARTS[1]}
PATCH=${VERSION_PARTS[2]}

# Check which part to increment
if [ "$1" == "major" ]; then
    NEW_VERSION="$((MAJOR + 1)).0.0"
elif [ "$1" == "minor" ]; then
    NEW_VERSION="$MAJOR.$((MINOR + 1)).0"
elif [ "$1" == "patch" ]; then
    NEW_VERSION="$MAJOR.$MINOR.$((PATCH + 1))"
else
    echo "Usage: ./scripts/update_version.sh [major|minor|patch]"
    echo "Current version: $CURRENT_VERSION"
    exit 1
fi

# Update version.txt
echo "$NEW_VERSION" > version.txt

echo "Version updated from $CURRENT_VERSION to $NEW_VERSION"

# Make the script create a commit with this change
if [ "$2" == "--commit" ]; then
    git add version.txt
    git commit -m "Bump version to $NEW_VERSION"
    echo "Committed version change to git"

    # Optionally create a tag
    if [ "$3" == "--tag" ]; then
        git tag -a "v$NEW_VERSION" -m "Version $NEW_VERSION"
        echo "Created tag v$NEW_VERSION"
    fi
fi

exit 0