#!/usr/bin/env python3
"""
Generate Requirements Traceability Matrix (RTM) from documentation.
Scans PRD, TechSpec, and Architecture docs for requirement IDs and traces them to implementation.
"""
import re
import sys
from pathlib import Path
from datetime import datetime
import json

class RTMGenerator:
    def __init__(self):
        self.requirements = {}
        self.implementations = {}
        self.req_pattern = re.compile(r'(FR|NFR)-(\d+(?:\.\d+)?):?\s*(.+?)(?:\n|$)')
        self.impl_pattern = re.compile(r'(?:Implements?|Addresses?|Satisfies?)\s+((?:FR|NFR)-\d+(?:\.\d+)?)', re.IGNORECASE)
        self.file_ref_pattern = re.compile(r'`([^`]+\.(py|js|ts))`')
        
    def parse_requirements(self, prd_path):
        """Extract requirements from PRD."""
        content = Path(prd_path).read_text()
        
        for match in self.req_pattern.finditer(content):
            req_type, req_num, req_desc = match.groups()
            req_id = f"{req_type}-{req_num}"
            self.requirements[req_id] = {
                'type': req_type,
                'number': req_num,
                'description': req_desc.strip(),
                'source': 'PRD',
                'implementations': []
            }
    
    def parse_implementations(self, techspec_path, arch_path):
        """Extract implementation references from technical documents."""
        for doc_path, doc_type in [(techspec_path, 'TechSpec'), (arch_path, 'Architecture')]:
            if not Path(doc_path).exists():
                continue
                
            content = Path(doc_path).read_text()
            lines = content.split('\n')
            
            for i, line in enumerate(lines):
                # Check for requirement references
                impl_match = self.impl_pattern.search(line)
                if impl_match:
                    req_id = impl_match.group(1)
                    
                    # Look for file references in nearby lines
                    context_start = max(0, i - 5)
                    context_end = min(len(lines), i + 5)
                    context = '\n'.join(lines[context_start:context_end])
                    
                    files = self.file_ref_pattern.findall(context)
                    
                    if req_id in self.requirements:
                        self.requirements[req_id]['implementations'].append({
                            'document': doc_type,
                            'line': i + 1,
                            'files': [f[0] for f in files],
                            'context': line.strip()
                        })
    
    def scan_source_code(self, source_dirs):
        """Scan source code for requirement references."""
        for source_dir in source_dirs:
            if not Path(source_dir).exists():
                continue
                
            for file_path in Path(source_dir).rglob('*.py'):
                content = file_path.read_text()
                
                for match in self.impl_pattern.finditer(content):
                    req_id = match.group(1)
                    if req_id in self.requirements:
                        # Find the line number
                        lines = content[:match.start()].count('\n') + 1
                        
                        self.requirements[req_id]['implementations'].append({
                            'document': 'Source Code',
                            'file': str(file_path),
                            'line': lines,
                            'context': match.group(0)
                        })
    
    def calculate_coverage(self):
        """Calculate requirement coverage statistics."""
        total = len(self.requirements)
        implemented = sum(1 for r in self.requirements.values() if r['implementations'])
        
        return {
            'total': total,
            'implemented': implemented,
            'coverage': (implemented / total * 100) if total > 0 else 0
        }
    
    def generate_markdown(self):
        """Generate RTM in Markdown format."""
        coverage = self.calculate_coverage()
        
        output = [
            "# Requirements Traceability Matrix (RTM)",
            f"\n**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"**Coverage**: {coverage['implemented']}/{coverage['total']} ({coverage['coverage']:.1f}%)\n",
            "## Summary",
            f"- Total Requirements: {coverage['total']}",
            f"- Implemented: {coverage['implemented']}",
            f"- Not Implemented: {coverage['total'] - coverage['implemented']}",
            f"- Coverage: {coverage['coverage']:.1f}%\n",
            "## Requirements Mapping\n"
        ]
        
        # Group by requirement type
        fr_reqs = {k: v for k, v in self.requirements.items() if k.startswith('FR')}
        nfr_reqs = {k: v for k, v in self.requirements.items() if k.startswith('NFR')}
        
        if fr_reqs:
            output.append("### Functional Requirements (FR)\n")
            output.extend(self._format_requirements(fr_reqs))
        
        if nfr_reqs:
            output.append("\n### Non-Functional Requirements (NFR)\n")
            output.extend(self._format_requirements(nfr_reqs))
        
        # Add unimplemented requirements section
        unimplemented = [k for k, v in self.requirements.items() if not v['implementations']]
        if unimplemented:
            output.append("\n## Unimplemented Requirements\n")
            for req_id in sorted(unimplemented):
                req = self.requirements[req_id]
                output.append(f"- **{req_id}**: {req['description']}")
        
        return '\n'.join(output)
    
    def _format_requirements(self, reqs):
        """Format a group of requirements."""
        output = []
        
        for req_id in sorted(reqs.keys()):
            req = reqs[req_id]
            output.append(f"#### {req_id}: {req['description']}\n")
            
            if req['implementations']:
                output.append("**Implementations:**")
                for impl in req['implementations']:
                    if impl['document'] == 'Source Code':
                        output.append(f"- {impl['file']}:{impl['line']}")
                    else:
                        files = ', '.join(impl.get('files', [])) or 'No file refs'
                        output.append(f"- {impl['document']} (line {impl['line']}): {files}")
                output.append("")
            else:
                output.append("**Status**: ❌ Not Implemented\n")
        
        return output
    
    def generate_json(self):
        """Generate RTM in JSON format for tooling."""
        return json.dumps({
            'generated': datetime.now().isoformat(),
            'coverage': self.calculate_coverage(),
            'requirements': self.requirements
        }, indent=2)

def main():
    if len(sys.argv) < 4:
        print("Usage: gen_rtm.py <PRD> <TechSpec> <Architecture> [source_dirs...]")
        sys.exit(1)
    
    prd_path = sys.argv[1]
    techspec_path = sys.argv[2]
    arch_path = sys.argv[3]
    source_dirs = sys.argv[4:] if len(sys.argv) > 4 else ['backend/', 'frontend/']
    
    generator = RTMGenerator()
    
    # Parse documents
    generator.parse_requirements(prd_path)
    generator.parse_implementations(techspec_path, arch_path)
    generator.scan_source_code(source_dirs)
    
    # Generate output
    print(generator.generate_markdown())
    
    # Also save JSON version
    json_path = Path('docs/AVATAR_ENGINE_RTM.json')
    json_path.write_text(generator.generate_json())

if __name__ == '__main__':
    main()