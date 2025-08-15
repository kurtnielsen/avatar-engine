#!/usr/bin/env python3
"""
Generate CHANGELOG.md from git commits using conventional commit format.
Groups changes by type and includes PR references.
"""
import re
import subprocess
import json
from datetime import datetime
from collections import defaultdict
import argparse

class ChangelogGenerator:
    def __init__(self):
        # Conventional commit types
        self.commit_types = {
            'feat': '✨ Features',
            'fix': '🐛 Bug Fixes',
            'perf': '⚡ Performance Improvements',
            'refactor': '♻️ Code Refactoring',
            'docs': '📚 Documentation',
            'test': '✅ Tests',
            'build': '🔧 Build System',
            'ci': '👷 CI/CD',
            'chore': '🔨 Chores',
            'security': '🔒 Security',
            'revert': '⏪ Reverts'
        }
        
        # Patterns
        self.commit_pattern = re.compile(
            r'^(?P<type>\w+)(?:\((?P<scope>[^)]+)\))?: (?P<subject>.+)$'
        )
        self.pr_pattern = re.compile(r'\(#(\d+)\)')
        self.breaking_pattern = re.compile(r'BREAKING CHANGE:', re.MULTILINE)
        
    def get_git_tags(self):
        """Get all git tags sorted by date."""
        try:
            result = subprocess.run(
                ['git', 'tag', '--sort=-version:refname'],
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout.strip().split('\n') if result.stdout else []
        except subprocess.CalledProcessError:
            return []
    
    def get_commits_between(self, from_ref, to_ref='HEAD'):
        """Get commits between two refs."""
        cmd = [
            'git', 'log',
            f'{from_ref}..{to_ref}',
            '--pretty=format:%H|%ai|%s|%b',
            '--reverse'
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            commits = []
            
            for line in result.stdout.strip().split('\n'):
                if line:
                    parts = line.split('|', 3)
                    if len(parts) >= 3:
                        commits.append({
                            'hash': parts[0][:7],
                            'date': parts[1],
                            'subject': parts[2],
                            'body': parts[3] if len(parts) > 3 else ''
                        })
            
            return commits
        except subprocess.CalledProcessError:
            return []
    
    def parse_commit(self, commit):
        """Parse commit message into structured format."""
        subject = commit['subject']
        match = self.commit_pattern.match(subject)
        
        if match:
            commit_type = match.group('type')
            scope = match.group('scope')
            description = match.group('subject')
            
            # Check for PR reference
            pr_match = self.pr_pattern.search(description)
            pr_number = pr_match.group(1) if pr_match else None
            
            # Check for breaking change
            is_breaking = bool(self.breaking_pattern.search(commit['body']))
            
            return {
                'type': commit_type,
                'scope': scope,
                'description': description,
                'hash': commit['hash'],
                'pr': pr_number,
                'breaking': is_breaking,
                'date': commit['date']
            }
        
        return None
    
    def group_commits(self, commits):
        """Group commits by type."""
        grouped = defaultdict(list)
        breaking_changes = []
        
        for commit in commits:
            parsed = self.parse_commit(commit)
            if parsed:
                if parsed['breaking']:
                    breaking_changes.append(parsed)
                
                commit_type = parsed['type']
                if commit_type in self.commit_types:
                    grouped[commit_type].append(parsed)
        
        return grouped, breaking_changes
    
    def format_commit_line(self, commit):
        """Format a single commit line."""
        line = f"- {commit['description']} ({commit['hash']})"
        if commit['scope']:
            line = f"- **{commit['scope']}**: {commit['description']} ({commit['hash']})"
        if commit['pr']:
            line += f" [#{commit['pr']}]"
        return line
    
    def generate_release_section(self, version, date, grouped, breaking):
        """Generate changelog section for a release."""
        lines = [f"## [{version}] - {date}\n"]
        
        # Breaking changes
        if breaking:
            lines.append("### ⚠️ BREAKING CHANGES\n")
            for commit in breaking:
                lines.append(self.format_commit_line(commit))
            lines.append("")
        
        # Other changes by type
        for commit_type, type_label in self.commit_types.items():
            if commit_type in grouped and grouped[commit_type]:
                lines.append(f"### {type_label}\n")
                for commit in grouped[commit_type]:
                    lines.append(self.format_commit_line(commit))
                lines.append("")
        
        return '\n'.join(lines)
    
    def generate_changelog(self, output_file='CHANGELOG.md', include_unreleased=True):
        """Generate the complete changelog."""
        tags = self.get_git_tags()
        changelog_parts = [
            "# Changelog\n",
            "All notable changes to the Avatar Engine will be documented in this file.\n",
            "The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),\n",
            "and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).\n"
        ]
        
        # Unreleased changes
        if include_unreleased:
            from_ref = tags[0] if tags else 'HEAD~20'
            commits = self.get_commits_between(from_ref, 'HEAD')
            if commits:
                grouped, breaking = self.group_commits(commits)
                if any(grouped.values()):
                    section = self.generate_release_section(
                        'Unreleased',
                        datetime.now().strftime('%Y-%m-%d'),
                        grouped,
                        breaking
                    )
                    changelog_parts.append(section)
        
        # Released versions
        for i, tag in enumerate(tags):
            from_ref = tags[i + 1] if i + 1 < len(tags) else ''
            if from_ref:
                commits = self.get_commits_between(from_ref, tag)
                grouped, breaking = self.group_commits(commits)
                
                # Get tag date
                tag_date = subprocess.run(
                    ['git', 'log', '-1', '--format=%ai', tag],
                    capture_output=True,
                    text=True
                ).stdout.strip()[:10]
                
                section = self.generate_release_section(
                    tag,
                    tag_date,
                    grouped,
                    breaking
                )
                changelog_parts.append(section)
        
        # Add links section
        changelog_parts.append("\n## Links\n")
        changelog_parts.append("[Unreleased]: https://github.com/neureval/avatar-engine/compare/{}...HEAD".format(
            tags[0] if tags else 'main'
        ))
        
        for i, tag in enumerate(tags[:-1]):
            next_tag = tags[i + 1]
            changelog_parts.append(
                f"[{tag}]: https://github.com/neureval/avatar-engine/compare/{next_tag}...{tag}"
            )
        
        return '\n'.join(changelog_parts)
    
    def generate_json_changelog(self):
        """Generate changelog in JSON format for tooling."""
        tags = self.get_git_tags()
        releases = []
        
        # Process each release
        for i, tag in enumerate(['HEAD'] + tags):
            from_ref = tags[i] if i < len(tags) else None
            to_ref = tag if tag != 'HEAD' else 'HEAD'
            
            if from_ref:
                commits = self.get_commits_between(from_ref, to_ref)
                grouped, breaking = self.group_commits(commits)
                
                release_data = {
                    'version': 'Unreleased' if tag == 'HEAD' else tag,
                    'date': datetime.now().isoformat() if tag == 'HEAD' else None,
                    'changes': {k: [c for c in v] for k, v in grouped.items()},
                    'breaking_changes': breaking
                }
                releases.append(release_data)
        
        return json.dumps({
            'generated': datetime.now().isoformat(),
            'releases': releases
        }, indent=2, default=str)

def main():
    parser = argparse.ArgumentParser(description='Generate changelog from git commits')
    parser.add_argument('--output', default='CHANGELOG.md', help='Output file')
    parser.add_argument('--format', choices=['markdown', 'json'], default='markdown')
    parser.add_argument('--include-unreleased', action='store_true', default=True)
    
    args = parser.parse_args()
    
    generator = ChangelogGenerator()
    
    if args.format == 'markdown':
        changelog = generator.generate_changelog(
            output_file=args.output,
            include_unreleased=args.include_unreleased
        )
        with open(args.output, 'w') as f:
            f.write(changelog)
        print(f"Changelog generated: {args.output}")
    else:
        changelog = generator.generate_json_changelog()
        output_file = args.output.replace('.md', '.json')
        with open(output_file, 'w') as f:
            f.write(changelog)
        print(f"JSON changelog generated: {output_file}")

if __name__ == '__main__':
    main()