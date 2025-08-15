#!/usr/bin/env python3
"""
Enhanced link checker that validates both file existence and markdown anchors.
Combines the best of both approaches.
"""
import sys
import re
import pathlib
from typing import Set, List, Tuple

def slugify(text: str) -> str:
    """Convert heading text to anchor slug."""
    text = text.strip().lower()
    text = re.sub(r'[\t\n\r]+', ' ', text)
    text = re.sub(r'[^\w\-\s]', '', text)
    text = re.sub(r'\s+', '-', text)
    return text

def extract_anchors(file_path: str) -> Set[str]:
    """Extract all heading anchors from a markdown file."""
    anchors = set()
    try:
        with open(file_path, encoding='utf-8', errors='ignore') as f:
            for line in f:
                if line.startswith('#'):
                    # Remove markdown heading syntax
                    heading_text = line.strip('#').strip()
                    # Convert to anchor format
                    anchor = slugify(heading_text)
                    anchors.add(anchor)
    except Exception as e:
        print(f"Warning: Could not read {file_path}: {e}")
    return anchors

def check_links(root_dir: str) -> List[Tuple[str, str, str]]:
    """Check all markdown links and anchors in the given directory."""
    root = pathlib.Path(root_dir)
    md_files = list(root.rglob("*.md"))
    
    # Build anchor index for all files
    anchor_index = {}
    for md_file in md_files:
        anchor_index[str(md_file)] = extract_anchors(str(md_file))
    
    # Check all links
    broken_links = []
    
    # Patterns to match different link types
    link_patterns = [
        # Standard markdown links: [text](file.md#anchor)
        re.compile(r'\[([^\]]+)\]\(([^)\s]+\.md)(?:#([^)]+))?\)'),
        # Reference-style links: [text][ref] ... [ref]: file.md#anchor
        re.compile(r'^\[([^\]]+)\]:\s*([^#\s]+\.md)(?:#(.+))?', re.MULTILINE),
        # Direct file references in backticks: `file.md`
        re.compile(r'`([^`]+\.md)(?:#([^`]+))?`')
    ]
    
    for md_file in md_files:
        try:
            content = md_file.read_text(encoding='utf-8', errors='ignore')
            
            for pattern in link_patterns:
                for match in pattern.finditer(content):
                    # Extract components based on pattern
                    if pattern.groups == 3:
                        _, file_ref, anchor = match.groups()
                    else:
                        file_ref, anchor = match.groups()
                    
                    # Resolve relative path
                    if file_ref.startswith('http'):
                        continue  # Skip external links
                    
                    target_path = (md_file.parent / file_ref).resolve()
                    
                    # Check file existence
                    if not target_path.exists():
                        broken_links.append((
                            str(md_file),
                            file_ref,
                            "file-not-found"
                        ))
                        continue
                    
                    # Check anchor if specified
                    if anchor:
                        anchor_slug = slugify(anchor)
                        available_anchors = anchor_index.get(str(target_path), set())
                        
                        if anchor_slug not in available_anchors:
                            broken_links.append((
                                str(md_file),
                                f"{file_ref}#{anchor}",
                                f"anchor-not-found (available: {', '.join(sorted(available_anchors)[:3])}...)"
                            ))
        
        except Exception as e:
            print(f"Warning: Error processing {md_file}: {e}")
    
    return broken_links

def validate_rtm_links(rtm_path: str) -> List[str]:
    """Special validation for RTM table links."""
    issues = []
    try:
        content = pathlib.Path(rtm_path).read_text()
        
        # Find all requirement links in tables
        req_pattern = re.compile(r'\[([A-Z]+-\d+(?:\.\d+)?)\]\(([^)#]+)(?:#([^)]+))?\)')
        
        for match in req_pattern.finditer(content):
            req_id, file_ref, anchor = match.groups()
            
            # Check if file exists
            target = pathlib.Path(rtm_path).parent / file_ref
            if not target.exists():
                issues.append(f"RTM: {req_id} links to missing file: {file_ref}")
            elif anchor:
                # Check anchor exists
                anchors = extract_anchors(str(target))
                if slugify(anchor) not in anchors:
                    issues.append(f"RTM: {req_id} links to missing anchor: {file_ref}#{anchor}")
    
    except Exception as e:
        issues.append(f"Could not validate RTM: {e}")
    
    return issues

def main(root_dir: str = "docs", check_rtm: bool = True) -> int:
    """Main link checking function."""
    print(f"Checking links in: {root_dir}")
    
    # Check general links
    broken_links = check_links(root_dir)
    
    # Check RTM specifically if it exists
    rtm_issues = []
    if check_rtm:
        rtm_path = pathlib.Path(root_dir) / "AVATAR_ENGINE_RTM.md"
        if rtm_path.exists():
            rtm_issues = validate_rtm_links(str(rtm_path))
    
    # Report results
    if broken_links or rtm_issues:
        print("\n❌ BROKEN LINKS AND ANCHORS:")
        
        for source, target, issue in broken_links:
            print(f"  - {source} → {target} :: {issue}")
        
        for issue in rtm_issues:
            print(f"  - {issue}")
        
        print(f"\nTotal issues: {len(broken_links) + len(rtm_issues)}")
        return 1
    else:
        print("✅ All links and anchors are valid!")
        return 0

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Check markdown links and anchors")
    parser.add_argument("root", nargs="?", default="docs", help="Root directory to check")
    parser.add_argument("--no-rtm", action="store_true", help="Skip RTM validation")
    
    args = parser.parse_args()
    sys.exit(main(args.root, not args.no_rtm))